#!/usr/bin/env python3
"""Claude Code adapter for ground-truth-blind ShowMeWhy V5 post-hoc runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
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
BASELINE_TOOLS = "Bash,Edit,Read,Write,Glob,Grep"
VERIFY_TOOLS = "Bash,Read,Glob,Grep"

CLAUDE_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SystemRoot",
    "COMSPEC",
    "PATHEXT",
    "LANG",
    "LC_ALL",
    "TERM",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "ANTHROPIC_API_KEY",
    "DISABLE_AUTOUPDATER",
    "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
)


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


def _expected_cli_version(runtime: str) -> str | None:
    match = re.fullmatch(r"claude-code-cli@(\d+\.\d+\.\d+)", runtime)
    return match.group(1) if match else None


def _treatment_prompt(skill_bytes: bytes) -> bytes:
    header = (
        "You are verifying a completed coding-agent result. The implementation already "
        "exists in the current workspace. Do not implement, edit, rewrite, or otherwise "
        "change repository files. Use observable source/execution evidence to assess the "
        "material claims in the completed result. Apply the canonical ShowMeWhy contract "
        "below. Return only ShowMeWhy's default human surface: the narrowest defensible "
        "result, NEEDS YOU only for material OPEN claims, any material REFUTED result, "
        "and one DO NEXT action. Never expose or reconstruct private chain-of-thought.\n\n"
        "--- CANONICAL SHOWMEWHY SKILL CONTRACT ---\n"
    ).encode("utf-8")
    return header + skill_bytes


def _claude_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for name in CLAUDE_ENV_ALLOWLIST:
        if name in os.environ:
            env[name] = os.environ[name]
    env["DISABLE_AUTOUPDATER"] = "1"
    env["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] = "1"
    return env


def _verification_user_prompt(task_prompt: str, baseline_result: str) -> str:
    return (
        "Verify the completed result below against the current workspace. The workspace "
        "is an exact clone of the state produced by the coding agent. Do not modify it.\n\n"
        "<original_task>\n"
        + task_prompt
        + "\n</original_task>\n\n"
        "<completed_agent_result>\n"
        + baseline_result
        + "\n</completed_agent_result>\n"
    )


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
    _required_env("ANTHROPIC_API_KEY")

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
    task_prompt = prompt_bytes.decode("utf-8")

    claude = shutil.which("claude")
    if not claude:
        raise AdapterError("claude executable was not found on PATH")

    actual_version = _claude_version(claude)
    expected_cli = _expected_cli_version(runtime)
    if expected_cli is not None and actual_version != f"{expected_cli} (Claude Code)":
        raise AdapterError(
            f"Claude Code runtime mismatch: pair requires {expected_cli}, got {actual_version}"
        )

    skill_bytes = SKILL.read_bytes()
    skill_hash = _sha256_bytes(skill_bytes)
    treatment_hash: str | None = None
    baseline_result_hash: str | None = None

    if condition == "baseline":
        user_prompt = task_prompt
        tools = BASELINE_TOOLS
        max_turns = "40"
        treatment = "none"
    else:
        baseline_result_file = Path(
            _required_env("SHOWMEWHY_V5_BASE_RESULT_FILE")
        ).resolve()
        if not baseline_result_file.is_file():
            raise AdapterError(
                f"baseline result file does not exist: {baseline_result_file}"
            )
        baseline_result_bytes = baseline_result_file.read_bytes()
        baseline_result_hash = _sha256_bytes(baseline_result_bytes)
        baseline_result = baseline_result_bytes.decode("utf-8")
        if not baseline_result.strip():
            raise AdapterError("baseline result is empty")

        treatment_bytes = _treatment_prompt(skill_bytes)
        treatment_hash = _sha256_bytes(treatment_bytes)
        treatment_path = output_dir / "showmewhy-treatment.md"
        treatment_path.write_bytes(treatment_bytes)

        user_prompt = _verification_user_prompt(task_prompt, baseline_result)
        tools = VERIFY_TOOLS
        max_turns = "24"
        treatment = "canonical-skill-posthoc"

    argv = [
        claude,
        "--bare",
        "--restricted",
        "-p",
        user_prompt,
        "--model",
        model,
        "--effort",
        "high",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--allowedTools",
        *tools.split(","),
        "--tools",
        tools,
        "--max-turns",
        max_turns,
    ]
    if condition == "showmewhy":
        argv.extend(
            [
                "--append-system-prompt-file",
                str(output_dir / "showmewhy-treatment.md"),
            ]
        )

    started = time.monotonic()
    process = subprocess.run(
        argv,
        cwd=workspace,
        env=_claude_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    seconds = round(time.monotonic() - started, 3)

    (output_dir / "claude.stdout.json").write_text(
        process.stdout, encoding="utf-8"
    )
    (output_dir / "claude.stderr.log").write_text(
        process.stderr, encoding="utf-8"
    )

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
        (output_dir / "result.txt").write_text(
            result_text, encoding="utf-8"
        )

    usage = (
        payload.get("usage")
        if payload and isinstance(payload.get("usage"), dict)
        else {}
    )
    cost = payload.get("total_cost_usd") if payload else None
    metadata = {
        "version": "v5-claude-adapter-2",
        "pair_id": pair_id,
        "condition": condition,
        "role": (
            "task-agent-result"
            if condition == "baseline"
            else "posthoc-verification"
        ),
        "model_requested": model,
        "agent_runtime": runtime,
        "tool_profile": tool_profile,
        "claude_version": actual_version,
        "prompt_sha256": prompt_hash,
        "baseline_result_sha256": baseline_result_hash,
        "canonical_skill_sha256": skill_hash,
        "treatment": treatment,
        "treatment_sha256": treatment_hash,
        "tools": tools.split(","),
        "permission_mode": "dontAsk",
        "permission_prompts": "none",
        "restricted": True,
        "subprocess_env_scrub": True,
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
            f"Claude exited {process.returncode}: "
            f"{(process.stderr or process.stdout)[-4000:]}"
        )
    if parse_error:
        raise AdapterError(parse_error)
    if is_error:
        raise AdapterError(
            f"Claude returned an error result: "
            f"{str(result_text or payload)[-4000:]}"
        )
    if not isinstance(result_text, str) or not result_text.strip():
        raise AdapterError("Claude returned no non-empty result text")

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
