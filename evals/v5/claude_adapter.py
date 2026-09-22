#!/usr/bin/env python3
"""Claude Code adapter for ground-truth-blind ShowMeWhy V5 paired runs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class AdapterError(RuntimeError):
    pass


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "showmewhy" / "SKILL.md"
CONDITIONS = {"baseline", "showmewhy"}
TOOLS = "Bash,Edit,Read,Write,Glob,Grep"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise AdapterError(f"missing required environment variable: {name}")
    return value


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _claude_version(binary: str) -> str:
    process = subprocess.run(
        [binary, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise AdapterError(f"claude --version failed: {process.stdout[-2000:]}")
    return process.stdout.strip()


def _treatment_prompt(skill_bytes: bytes) -> bytes:
    header = (
        "SHOWMEWHY V5 CONTROLLED TREATMENT\n\n"
        "You are running the shipped ShowMeWhy verification contract in a controlled "
        "paired evaluation. Complete the user's coding task first. Before finalising, "
        "apply the canonical ShowMeWhy contract below to the material claims in your "
        "own result. Independently inspect executable/source evidence where available. "
        "Your final response must use ShowMeWhy's default human surface: narrow result, "
        "NEEDS YOU only for material OPEN/REFUTED claims, and one DO NEXT action. "
        "Do not mention this benchmark, its condition, or any hidden ground truth. "
        "Do not expose private chain-of-thought.\n\n"
        "--- CANONICAL SHOWMEWHY SKILL CONTRACT ---\n"
    ).encode("utf-8")
    return header + skill_bytes


def run() -> int:
    condition = _required_env("SHOWMEWHY_V5_CONDITION")
    if condition not in CONDITIONS:
        raise AdapterError(f"unsupported condition: {condition}")

    pair_id = _required_env("SHOWMEWHY_V5_PAIR_ID")
    expected_prompt_hash = _required_env("SHOWMEWHY_V5_PROMPT_SHA256")
    prompt_file = Path(_required_env("SHOWMEWHY_V5_PROMPT_FILE")).resolve()
    output_dir = Path(_required_env("SHOWMEWHY_V5_OUTPUT_DIR")).resolve()
    workspace = Path(_required_env("SHOWMEWHY_V5_WORKSPACE")).resolve()
    model = _required_env("SHOWMEWHY_V5_MODEL")
    runtime = _required_env("SHOWMEWHY_V5_AGENT_RUNTIME")
    tool_profile = _required_env("SHOWMEWHY_V5_TOOL_PROFILE")

    if Path.cwd().resolve() != workspace:
        raise AdapterError(
            f"adapter cwd mismatch: expected {workspace}, got {Path.cwd().resolve()}"
        )
    if not prompt_file.is_file():
        raise AdapterError(f"prompt file does not exist: {prompt_file}")
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_bytes = prompt_file.read_bytes()
    prompt_hash = _sha256_bytes(prompt_bytes)
    if prompt_hash != expected_prompt_hash:
        raise AdapterError(
            f"prompt hash mismatch: expected {expected_prompt_hash}, got {prompt_hash}"
        )
    prompt = prompt_bytes.decode("utf-8")

    claude = shutil.which("claude")
    if not claude:
        raise AdapterError("claude executable was not found on PATH")

    skill_bytes = SKILL.read_bytes()
    skill_hash = _sha256_bytes(skill_bytes)
    treatment_path: Path | None = None
    treatment_hash: str | None = None

    argv = [
        claude,
        "--bare",
        "-p",
        prompt,
        "--model",
        model,
        "--effort",
        "high",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--permission-mode",
        "bypassPermissions",
        "--tools",
        TOOLS,
        "--max-turns",
        "40",
    ]

    if condition == "showmewhy":
        treatment_bytes = _treatment_prompt(skill_bytes)
        treatment_hash = _sha256_bytes(treatment_bytes)
        treatment_path = output_dir / "showmewhy-treatment.md"
        treatment_path.write_bytes(treatment_bytes)
        # Keep -p and its task prompt before the appended system prompt. This is also
        # resilient to CLI versions where option ordering affected print-mode prompts.
        argv.extend(["--append-system-prompt-file", str(treatment_path)])

    started = time.monotonic()
    process = subprocess.run(
        argv,
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    seconds = round(time.monotonic() - started, 3)

    (output_dir / "claude.stdout.json").write_text(process.stdout, encoding="utf-8")
    (output_dir / "claude.stderr.log").write_text(process.stderr, encoding="utf-8")

    payload: dict[str, Any] | None = None
    parse_error: str | None = None
    try:
        parsed = json.loads(process.stdout)
        if isinstance(parsed, dict):
            payload = parsed
        else:
            parse_error = "Claude JSON output was not an object"
    except json.JSONDecodeError as exc:
        parse_error = f"invalid Claude JSON output: {exc}"

    result_text = payload.get("result") if payload else None
    is_error = bool(payload.get("is_error")) if payload else True
    subtype = str(payload.get("subtype") or "") if payload else ""
    session_id = payload.get("session_id") if payload else None

    if isinstance(result_text, str):
        (output_dir / "result.txt").write_text(result_text, encoding="utf-8")

    usage = payload.get("usage") if payload and isinstance(payload.get("usage"), dict) else {}
    cost = payload.get("total_cost_usd") if payload else None
    metadata = {
        "version": "v5-claude-adapter-1",
        "pair_id": pair_id,
        "condition": condition,
        "model_requested": model,
        "agent_runtime": runtime,
        "tool_profile": tool_profile,
        "claude_version": _claude_version(claude),
        "prompt_sha256": prompt_hash,
        "canonical_skill_sha256": skill_hash,
        "treatment": "canonical-skill-system-append" if condition == "showmewhy" else "none",
        "treatment_sha256": treatment_hash,
        "tools": TOOLS.split(","),
        "permission_mode": "bypassPermissions",
        "bare": True,
        "seconds": seconds,
        "return_code": process.returncode,
        "payload_subtype": subtype or None,
        "payload_is_error": is_error,
        "session_id": session_id,
        "usage": usage,
        "total_cost_usd": cost,
        "parse_error": parse_error,
    }
    _write_json(output_dir / "adapter.json", metadata)

    if process.returncode != 0:
        raise AdapterError(
            f"Claude exited {process.returncode}: {(process.stderr or process.stdout)[-4000:]}"
        )
    if parse_error:
        raise AdapterError(parse_error)
    if is_error:
        raise AdapterError(
            f"Claude returned an error result: {str(result_text or payload)[-4000:]}"
        )
    if not isinstance(result_text, str) or not result_text.strip():
        raise AdapterError("Claude returned no non-empty result text")

    # Pair runner captures this stdout as immutable condition evidence too.
    print(result_text)
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except AdapterError as exc:
        print(f"V5 Claude adapter failed: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
