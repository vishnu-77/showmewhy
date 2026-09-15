from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .common import estimate_tokens
from .compressors import compress_text, replace_response_text, response_text
from .digest import build_digest, persist_digest
from .evidence import EvidenceStore


def process_event(event: dict[str, Any], *, cwd: str | Path | None = None, mode: str | None = None, target_tokens: int | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    mode = (mode or os.getenv("SHOWMEWHY_MODE", "replace")).lower()
    target_tokens = target_tokens or int(os.getenv("SHOWMEWHY_CONTEXT_BUDGET_TOKENS", "700"))
    tool_name = str(event.get("tool_name") or "")
    response = event.get("tool_response")
    text = response_text(tool_name, response)
    if tool_name != "Bash" or text is None or estimate_tokens(text) <= target_tokens:
        return {}, None

    base_cwd = cwd or event.get("cwd") or "."
    store = EvidenceStore(base_cwd)
    try:
        raw_ref = store.put(tool_name=tool_name, tool_input=event.get("tool_input"), tool_response=response, session_id=event.get("session_id"))
    except Exception:
        return {}, None

    result = compress_text(text, target_tokens=target_tokens)
    if result.text == text:
        return {}, None
    digest = build_digest(tool_name=tool_name, evidence_ref=raw_ref, raw_text=text, result=result, session_id=event.get("session_id"), tool_use_id=event.get("tool_use_id"))
    persist_digest(digest, base_cwd)

    if mode == "shadow":
        return {}, digest
    if mode != "replace":
        return {}, digest

    replacement = replace_response_text(tool_name, response, result.text + f"\nRaw evidence: {raw_ref}")
    if replacement is None:
        return {}, digest
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": replacement}}, digest
