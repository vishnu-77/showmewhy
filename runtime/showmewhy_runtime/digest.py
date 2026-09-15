from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .common import estimate_tokens, runtime_root
from .compressors import CompressionResult


def build_digest(*, tool_name: str, evidence_ref: str, raw_text: str, result: CompressionResult, session_id: str | None = None, tool_use_id: str | None = None) -> dict[str, Any]:
    raw_tokens = estimate_tokens(raw_text)
    digest_tokens = estimate_tokens(result.text)
    avoided = max(raw_tokens - digest_tokens, 0)
    return {
        "version": "2.0",
        "run_id": f"run-{uuid.uuid4().hex[:12]}",
        "created_unix": int(time.time()),
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "tool_name": tool_name,
        "kind": result.kind,
        "status": result.status,
        "summary": result.text,
        "metrics": result.metrics,
        "findings": result.findings,
        "caveats": [] if result.complete else ["Digest is incomplete; inspect raw evidence before relying on omitted detail."],
        "raw_ref": evidence_ref,
        "raw_tokens": raw_tokens,
        "digest_tokens": digest_tokens,
        "tokens_avoided": avoided,
        "compression_pct": round((avoided / raw_tokens * 100), 1) if raw_tokens else 0.0,
        "parser": {
            "name": result.parser,
            "confidence": result.confidence,
            "complete": result.complete,
        },
    }


def persist_digest(digest: dict[str, Any], cwd: str | Path | None = None) -> Path:
    root = runtime_root(cwd) / "runs"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{digest['run_id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(digest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path
