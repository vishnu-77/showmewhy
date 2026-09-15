from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def estimate_tokens(value: Any) -> int:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if not text:
        return 0
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_id(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def runtime_root(cwd: str | Path | None = None) -> Path:
    base = Path(cwd or ".").resolve()
    root = base / ".showmewhy"
    root.mkdir(parents=True, exist_ok=True)
    return root
