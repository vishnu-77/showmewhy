from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .common import sha256_id, runtime_root


class EvidenceStore:
    def __init__(self, cwd: str | Path | None = None):
        self.root = runtime_root(cwd) / "evidence"
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, *, tool_name: str, tool_input: Any, tool_response: Any, session_id: str | None = None) -> str:
        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": tool_response,
        }
        digest = sha256_id(payload)
        path = self.root / f"{digest}.json"
        if not path.exists():
            record = {
                "version": "2.0",
                "sha256": digest,
                "created_unix": int(time.time()),
                "session_id": session_id,
                **payload,
            }
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            tmp.replace(path)
        return f"evidence://sha256/{digest}"

    def get(self, ref: str) -> dict[str, Any]:
        prefix = "evidence://sha256/"
        if not ref.startswith(prefix):
            raise ValueError("unsupported evidence reference")
        digest = ref[len(prefix):]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("invalid evidence digest")
        return json.loads((self.root / f"{digest}.json").read_text(encoding="utf-8"))

    def prune(self, *, max_age_days: int = 30) -> int:
        cutoff = time.time() - max_age_days * 86400
        removed = 0
        for path in self.root.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        return removed
