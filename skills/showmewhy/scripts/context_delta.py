#!/usr/bin/env python3
"""Deterministic temporal verification for ShowMeWhy Context Delta surfaces."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "showmewhy_verification_surface", HERE / "verification_surface.py"
)
_verification = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_verification)

ASSUMPTION_OUTCOMES = {"supports", "refutes", "inconclusive"}
STATE_TRANSITIONS = {
    ("verified", "refuted"): "invalidated",
    ("verified", "open"): "degraded",
    ("open", "refuted"): "contradicted",
    ("open", "verified"): "resolved",
    ("refuted", "verified"): "resolved",
    ("refuted", "open"): "softened",
}
WORSENING = {"invalidated", "degraded", "contradicted"}
IMPROVING = {"resolved", "softened"}


class ContextDeltaError(ValueError):
    pass


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextDeltaError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ContextDeltaError(f"{field} must be an array of non-empty strings")
    return [v.strip() for v in value]


def validate_delta_manifest(manifest: Dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ContextDeltaError("delta manifest must be an object")
    for key in ("previous", "current"):
        if not isinstance(manifest.get(key), dict):
            raise ContextDeltaError(f"{key} must be a verification manifest")
        try:
            _verification.validate_manifest(manifest[key])
        except ValueError as exc:
            raise ContextDeltaError(f"{key}: {exc}") from exc

    assumptions = manifest.get("assumptions", [])
    if not isinstance(assumptions, list):
        raise ContextDeltaError("assumptions must be an array")
    seen = set()
    for index, assumption in enumerate(assumptions):
        prefix = f"assumptions[{index}]"
        if not isinstance(assumption, dict):
            raise ContextDeltaError(f"{prefix} must be an object")
        aid = _nonempty(assumption.get("id"), f"{prefix}.id")
        if aid in seen:
            raise ContextDeltaError(f"duplicate assumption id: {aid}")
        seen.add(aid)
        _nonempty(assumption.get("text"), f"{prefix}.text")
        _string_list(assumption.get("claim_ids", []), f"{prefix}.claim_ids")
        witnesses = assumption.get("witnesses", [])
        if not isinstance(witnesses, list):
            raise ContextDeltaError(f"{prefix}.witnesses must be an array")
        for w_index, witness in enumerate(witnesses):
            wp = f"{prefix}.witnesses[{w_index}]"
            if not isinstance(witness, dict):
                raise ContextDeltaError(f"{wp} must be an object")
            _nonempty(witness.get("source"), f"{wp}.source")
            if witness.get("outcome") not in ASSUMPTION_OUTCOMES:
                raise ContextDeltaError(f"{wp}.outcome must be supports|refutes|inconclusive")
            if "finding" in witness:
                _nonempty(witness.get("finding"), f"{wp}.finding")

    coverage = manifest.get("coverage", {})
    if coverage is not None:
        if not isinstance(coverage, dict):
            raise ContextDeltaError("coverage must be an object")
        for key in ("previous", "current", "missing_that_mattered"):
            _string_list(coverage.get(key, []), f"coverage.{key}")

    _string_list(manifest.get("impact", []), "impact")
    if "blocker" in manifest and manifest["blocker"] is not None:
        _nonempty(manifest["blocker"], "blocker")


def _assess_assumption(assumption: Dict[str, Any]) -> Dict[str, Any]:
    witnesses = assumption.get("witnesses", [])
    refuting = [w for w in witnesses if w["outcome"] == "refutes"]
    supporting = [w for w in witnesses if w["outcome"] == "supports"]
    if refuting:
        state = "invalidated"
    elif supporting:
        state = "supported"
    else:
        state = "open"
    result = dict(assumption)
    result["state"] = state
    result["refuting_witnesses"] = refuting
    result["supporting_witnesses"] = supporting
    return result


def _claim_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {claim["id"]: claim for claim in report["claims"]}


def _transition(previous: str, current: str) -> str:
    if previous == current:
        return "unchanged"
    return STATE_TRANSITIONS.get((previous, current), "changed")


def _witness_signature(witness: Dict[str, Any]) -> Tuple[str, str, str]:
    return (witness.get("kind", ""), witness.get("source", ""), witness.get("outcome", ""))


def analyse_delta(manifest: Dict[str, Any]) -> Dict[str, Any]:
    validate_delta_manifest(manifest)
    previous = _verification.analyse(manifest["previous"])
    current = _verification.analyse(manifest["current"])
    before = _claim_map(previous)
    after = _claim_map(current)

    transitions: List[Dict[str, Any]] = []
    new_evidence: List[Dict[str, str]] = []
    seen_evidence = set()

    for cid in sorted(set(before) | set(after)):
        old = before.get(cid)
        new = after.get(cid)
        if old is None:
            transitions.append({
                "claim_id": cid,
                "claim": new["text"],
                "from": "absent",
                "to": new["state"],
                "change": "added",
            })
            old_signatures = set()
        elif new is None:
            transitions.append({
                "claim_id": cid,
                "claim": old["text"],
                "from": old["state"],
                "to": "absent",
                "change": "removed",
            })
            continue
        else:
            change = _transition(old["state"], new["state"])
            if change != "unchanged":
                transitions.append({
                    "claim_id": cid,
                    "claim": new["text"],
                    "from": old["state"],
                    "to": new["state"],
                    "change": change,
                })
            old_signatures = {_witness_signature(w) for w in old.get("witnesses", [])}

        if new is not None:
            for witness in new.get("witnesses", []):
                signature = _witness_signature(witness)
                if signature not in old_signatures and signature not in seen_evidence:
                    seen_evidence.add(signature)
                    new_evidence.append({
                        "source": witness["source"],
                        "finding": f"{witness['kind']} witness {witness['outcome']} the current claim",
                    })

    assumptions = [_assess_assumption(a) for a in manifest.get("assumptions", [])]
    broken = [a for a in assumptions if a["state"] == "invalidated"]
    for assumption in broken:
        for witness in assumption["refuting_witnesses"]:
            key = ("assumption", witness["source"], witness["outcome"])
            if key not in seen_evidence:
                seen_evidence.add(key)
                new_evidence.append({
                    "source": witness["source"],
                    "finding": witness.get("finding", "This evidence invalidates a relied-upon assumption."),
                })

    transition_changes = {t["change"] for t in transitions}
    if broken or transition_changes & WORSENING:
        status = "changed"
    elif transitions and transition_changes <= (IMPROVING | {"added", "removed", "changed"}):
        status = "resolved"
    else:
        status = "unchanged"

    coverage = manifest.get("coverage") or {}
    previous_coverage = set(_string_list(coverage.get("previous", []), "coverage.previous"))
    current_coverage = set(_string_list(coverage.get("current", []), "coverage.current"))
    missing_that_mattered = _string_list(
        coverage.get("missing_that_mattered", []), "coverage.missing_that_mattered"
    )

    return {
        "version": "1.0",
        "status": status,
        "previous": previous,
        "current": current,
        "transitions": transitions,
        "assumptions": assumptions,
        "broken_assumptions": broken,
        "new_evidence": new_evidence,
        "coverage": {
            "previous": sorted(previous_coverage),
            "current": sorted(current_coverage),
            "newly_inspected": sorted(current_coverage - previous_coverage),
            "missing_that_mattered": missing_that_mattered,
        },
        "impact": _string_list(manifest.get("impact", []), "impact"),
        "blocker": manifest.get("blocker"),
        "do_next": current["do_next"],
    }


def _evidence_line(evidence: Dict[str, str]) -> str:
    finding = evidence.get("finding", "").strip()
    return f"{evidence['source']} · {finding}" if finding else evidence["source"]


def render_delta(report: Dict[str, Any], max_evidence: int = 2) -> str:
    heading = {"changed": "CHANGED", "resolved": "RESOLVED", "unchanged": "UNCHANGED"}[report["status"]]
    lines: List[str] = ["SHOWMEWHY · DELTA", "", heading, report["current"]["result"], ""]

    broken = report["broken_assumptions"]
    if broken:
        lines.append("BROKEN ASSUMPTION")
        lines.append(broken[0]["text"])
        if len(broken) > 1:
            lines.append(f"+{len(broken) - 1} more invalidated assumption{'s' if len(broken) != 2 else ''}")
        lines.append("")

    evidence = report["new_evidence"][:max_evidence]
    if evidence:
        lines.append("NEW EVIDENCE")
        for item in evidence:
            lines.append(_evidence_line(item))
        hidden = len(report["new_evidence"]) - len(evidence)
        if hidden > 0:
            lines.append(f"+{hidden} more evidence item{'s' if hidden != 1 else ''}")
        lines.append("")

    impact = report["impact"]
    if impact:
        lines.append("IMPACT")
        for item in impact[:3]:
            lines.append(item)
        if len(impact) > 3:
            lines.append(f"+{len(impact) - 3} more")
        lines.append("")

    missed = report["coverage"]["missing_that_mattered"]
    if missed:
        lines.extend(["MISSED", "; ".join(missed[:3])])
        if len(missed) > 3:
            lines.append(f"+{len(missed) - 3} more missing context areas")
        lines.append("")

    if report.get("blocker"):
        lines.extend(["BLOCKER", report["blocker"], ""])

    lines.extend([
        "DO NEXT",
        report["do_next"].get("action") or "Re-verify the highest-value changed claim.",
    ])
    return "\n".join(lines)


def load_manifest(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "manifest" in payload:
        return payload["manifest"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a deterministic ShowMeWhy Context Delta")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--mode", choices=["default", "json"], default="default")
    args = parser.parse_args()

    report = analyse_delta(load_manifest(args.manifest))
    if args.mode == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_delta(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
