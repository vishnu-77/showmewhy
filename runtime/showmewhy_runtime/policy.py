from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .common import runtime_root
from .compare import load_run

BASELINE_TARGET = 700
AGGRESSIVE_TARGET = 500
CONSERVATIVE_TARGET = 1100
SAFETY_TARGET = 1200
WINDOW = 50


def _state_path(cwd: str | Path | None = None) -> Path:
    return runtime_root(cwd) / "policy.json"


def _feedback_path(cwd: str | Path | None = None) -> Path:
    return runtime_root(cwd) / "feedback.jsonl"


def load_state(cwd: str | Path | None = None) -> dict[str, Any]:
    path = _state_path(cwd)
    if not path.exists():
        return {"version": "4.0", "safety_lock": False, "updated_unix": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "version": "4.0",
        "safety_lock": bool(data.get("safety_lock")),
        "updated_unix": data.get("updated_unix"),
    }


def _write_state(state: dict[str, Any], cwd: str | Path | None = None) -> None:
    path = _state_path(cwd)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def record_feedback(run_id: str, *, reopened: bool, material_loss: bool, cwd: str | Path | None = None) -> dict[str, Any]:
    run = load_run(run_id, cwd)
    parser = run.get("parser") or {}
    event = {
        "version": "4.0",
        "created_unix": int(time.time()),
        "run_id": run_id,
        "reopened": bool(reopened),
        "material_loss": bool(material_loss),
        "parser_complete": bool(parser.get("complete")),
        "parser_confidence": str(parser.get("confidence") or "unknown"),
        "compression_pct": float(run.get("compression_pct") or 0.0),
        "tokens_avoided": int(run.get("tokens_avoided") or 0),
    }
    path = _feedback_path(cwd)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    if material_loss:
        state = load_state(cwd)
        state["safety_lock"] = True
        state["updated_unix"] = int(time.time())
        _write_state(state, cwd)
    return event


def load_feedback(cwd: str | Path | None = None, *, limit: int = WINDOW) -> list[dict[str, Any]]:
    path = _feedback_path(cwd)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows[-limit:]


def clear_safety_lock(cwd: str | Path | None = None) -> dict[str, Any]:
    state = load_state(cwd)
    state["safety_lock"] = False
    state["updated_unix"] = int(time.time())
    _write_state(state, cwd)
    return state


def recommend_policy(cwd: str | Path | None = None) -> dict[str, Any]:
    state = load_state(cwd)
    events = load_feedback(cwd)
    if state["safety_lock"]:
        return {
            "version": "4.0",
            "mode": "shadow",
            "target_tokens": SAFETY_TARGET,
            "safety_lock": True,
            "samples": len(events),
            "reason": "Material information loss was reported; replacement is disabled until the safety lock is manually cleared.",
        }
    if len(events) < 3:
        return {
            "version": "4.0",
            "mode": "shadow",
            "target_tokens": BASELINE_TARGET,
            "safety_lock": False,
            "samples": len(events),
            "reason": "Insufficient verified feedback; observe compression candidates without replacing active context.",
        }

    reopen_rate = sum(bool(e.get("reopened")) for e in events) / len(events)
    complete_rate = sum(bool(e.get("parser_complete")) for e in events) / len(events)
    avg_compression = sum(float(e.get("compression_pct") or 0.0) for e in events) / len(events)

    if reopen_rate >= 0.35 or complete_rate < 0.75:
        target = CONSERVATIVE_TARGET
        reason = "Evidence is reopened frequently or parser completeness is low; preserve more context."
    elif len(events) >= 5 and reopen_rate <= 0.10 and complete_rate >= 0.90 and avg_compression >= 50.0:
        target = AGGRESSIVE_TARGET
        reason = "Verified feedback shows low reopen demand, high parser completeness and useful compression."
    else:
        target = BASELINE_TARGET
        reason = "Observed outcomes do not justify changing the baseline context budget."

    return {
        "version": "4.0",
        "mode": "replace",
        "target_tokens": target,
        "safety_lock": False,
        "samples": len(events),
        "reopen_rate": round(reopen_rate, 3),
        "parser_complete_rate": round(complete_rate, 3),
        "avg_compression_pct": round(avg_compression, 1),
        "reason": reason,
    }
