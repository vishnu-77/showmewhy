from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import runtime_root


def load_run(run_id: str, cwd: str | Path | None = None) -> dict[str, Any]:
    return json.loads((runtime_root(cwd) / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))


def compare_runs(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "before": before["run_id"],
        "after": after["run_id"],
        "status_changed": before.get("status") != after.get("status"),
        "status": [before.get("status"), after.get("status")],
        "tokens_avoided_delta": int(after.get("tokens_avoided", 0)) - int(before.get("tokens_avoided", 0)),
        "compression_pct_delta": round(float(after.get("compression_pct", 0)) - float(before.get("compression_pct", 0)), 1),
        "new_findings": [x for x in (after.get("findings") or []) if x not in (before.get("findings") or [])],
        "resolved_findings": [x for x in (before.get("findings") or []) if x not in (after.get("findings") or [])],
    }
