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


def _replacement_eligible(result) -> tuple[bool, str]:
    if not result.complete:
        return False, "digest is incomplete"
    if result.confidence != "high":
        return False, f"parser confidence is {result.confidence}"
    if result.parser in {"bounded-log", "passthrough"}:
        return False, f"parser {result.parser} is not replacement-safe"
    return True, "complete high-confidence structured parser"


def process_event(event: dict[str, Any], *, cwd: str | Path | None = None, mode: str | None = None, target_tokens: int | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    tool_name = str(event.get("tool_name") or "")
    response = event.get("tool_response")
    text = response_text(tool_name, response)
    if tool_name != "Bash" or text is None:
        return {}, None

    base_cwd = cwd or event.get("cwd") or "."
    policy = recommend_policy(base_cwd)
    env_mode = os.getenv("SHOWMEWHY_MODE")
    env_target = os.getenv("SHOWMEWHY_CONTEXT_BUDGET_TOKENS")
    effective_mode = (mode or env_mode or policy["mode"]).lower()
    effective_target = target_tokens or (int(env_target) if env_target else int(policy["target_tokens"]))

    if estimate_tokens(text) <= effective_target:
        return {}, None

    store = EvidenceStore(base_cwd)
    try:
        raw_ref = store.put(tool_name=tool_name, tool_input=event.get("tool_input"), tool_response=response, session_id=event.get("session_id"))
    except Exception:
        return {}, None

    result = compress_text(text, target_tokens=effective_target)
    if result.text == text:
        return {}, None
    digest = build_digest(tool_name=tool_name, evidence_ref=raw_ref, raw_text=text, result=result, session_id=event.get("session_id"), tool_use_id=event.get("tool_use_id"))
    replacement_eligible, replacement_reason = _replacement_eligible(result)
    digest["policy"] = {
        "mode": effective_mode,
        "target_tokens": effective_target,
        "safety_lock": bool(policy.get("safety_lock")),
        "samples": int(policy.get("samples", 0)),
        "reason": policy.get("reason"),
        "replacement_eligible": replacement_eligible,
        "replacement_reason": replacement_reason,
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
        digest["caveats"].append("Provenance graph generation failed; inspect raw evidence directly.")
    persist_digest(digest, base_cwd)

    if effective_mode == "shadow":
        return {}, digest
    if not result.complete:
        return {}, digest
    if effective_mode != "replace":
        return {}, digest
    if not replacement_eligible:
        return {}, digest

    replacement = replace_response_text(tool_name, response, result.text + f"\nRaw evidence: {raw_ref}")
    if replacement is None:
        return {}, digest
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": replacement}}, digest
