from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .common import estimate_tokens
from .compressors import compress_text, replace_response_text, response_text
from .digest import build_digest, persist_digest
from .evidence import EvidenceStore
from .policy import recommend_policy
from .provenance import build_graph, persist_graph


VALID_MODES = {"replace", "shadow"}
DEFAULT_FAIL_OPEN_TARGET = 1200


def _positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _effective_mode(requested: str | None, policy: dict[str, Any]) -> str:
    # A sticky safety lock is intentionally stronger than configuration.
    if bool(policy.get("safety_lock")):
        return "shadow"
    candidate = (requested or "").strip().lower()
    if candidate in VALID_MODES:
        return candidate
    fallback = str(policy.get("mode") or "shadow").lower()
    return fallback if fallback in VALID_MODES else "shadow"


def process_event(
    event: dict[str, Any],
    *,
    cwd: str | Path | None = None,
    mode: str | None = None,
    target_tokens: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    tool_name = str(event.get("tool_name") or "")
    response = event.get("tool_response")
    text = response_text(tool_name, response)
    if tool_name != "Bash" or text is None:
        return {}, None

    base_cwd = cwd or event.get("cwd") or "."

    try:
        policy = recommend_policy(base_cwd)
    except Exception:
        # Policy state must never make the hook fail closed on the host tool.
        policy = {
            "mode": "shadow",
            "target_tokens": DEFAULT_FAIL_OPEN_TARGET,
            "safety_lock": True,
            "samples": 0,
            "reason": "Policy state could not be read; replacement was disabled.",
        }

    env_mode = os.getenv("SHOWMEWHY_MODE")
    env_target = os.getenv("SHOWMEWHY_CONTEXT_BUDGET_TOKENS")
    effective_mode = _effective_mode(mode or env_mode, policy)

    policy_target = _positive_int(policy.get("target_tokens"), DEFAULT_FAIL_OPEN_TARGET)
    if target_tokens is not None:
        effective_target = _positive_int(target_tokens, policy_target)
    elif env_target is not None:
        effective_target = _positive_int(env_target, policy_target)
    else:
        effective_target = policy_target

    if estimate_tokens(text) <= effective_target:
        return {}, None

    store = EvidenceStore(base_cwd)
    try:
        raw_ref = store.put(
            tool_name=tool_name,
            tool_input=event.get("tool_input"),
            tool_response=response,
            session_id=event.get("session_id"),
        )
    except Exception:
        return {}, None

    try:
        result = compress_text(text, target_tokens=effective_target)
        if result.text == text:
            return {}, None
        digest = build_digest(
            tool_name=tool_name,
            evidence_ref=raw_ref,
            raw_text=text,
            result=result,
            session_id=event.get("session_id"),
            tool_use_id=event.get("tool_use_id"),
        )
    except Exception:
        # Raw evidence is already retained; preserve the original visible output.
        return {}, None

    digest["policy"] = {
        "mode": effective_mode,
        "target_tokens": effective_target,
        "safety_lock": bool(policy.get("safety_lock")),
        "samples": int(policy.get("samples", 0)),
        "reason": policy.get("reason"),
    }
    if not result.complete:
        digest["caveats"].append(
            "Compression is incomplete; original tool output was preserved in the active context."
        )

    try:
        graph = build_graph(digest)
        persist_graph(graph, base_cwd)
        digest["provenance_ref"] = f"provenance://{graph['graph_id']}"
        digest["provenance_confidence"] = graph["confidence"]
    except Exception:
        digest["caveats"].append(
            "Provenance graph generation failed; inspect raw evidence directly."
        )

    try:
        persist_digest(digest, base_cwd)
    except Exception:
        # Never replace context unless the digest itself was durably recorded.
        digest["caveats"].append(
            "Digest persistence failed; original tool output was preserved in the active context."
        )
        return {}, digest

    if effective_mode == "shadow":
        return {}, digest
    if not result.complete:
        return {}, digest
    if effective_mode != "replace":
        return {}, digest

    replacement = replace_response_text(
        tool_name,
        response,
        result.text + f"\nRaw evidence: {raw_ref}",
    )
    if replacement is None:
        return {}, digest
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": replacement,
        }
    }, digest
