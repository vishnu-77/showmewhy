#!/usr/bin/env python3
"""Deterministic reference implementation for ShowMeWhy verification surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

WITNESS_KINDS = {
    "execution",
    "source",
    "measurement",
    "invariant",
    "counterexample",
    "boundary",
    "regression",
    "comparison",
}
OUTCOMES = {"supports", "refutes", "inconclusive"}
RISKS = {"low", "medium", "high"}
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
STATE_ORDER = {"refuted": 0, "open": 1, "verified": 2}


class VerificationError(ValueError):
    pass


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationError(f"{field} must be a non-empty string")
    return value.strip()


def validate_manifest(manifest: Dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise VerificationError("manifest must be an object")
    _nonempty(manifest.get("result"), "result")
    claims = manifest.get("claims")
    if not isinstance(claims, list) or not claims:
        raise VerificationError("claims must be a non-empty array")

    seen_ids = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            raise VerificationError(f"{prefix} must be an object")
        cid = _nonempty(claim.get("id"), f"{prefix}.id")
        if cid in seen_ids:
            raise VerificationError(f"duplicate claim id: {cid}")
        seen_ids.add(cid)
        _nonempty(claim.get("text"), f"{prefix}.text")
        _nonempty(claim.get("obligation"), f"{prefix}.obligation")
        risk = claim.get("risk", "medium")
        if risk not in RISKS:
            raise VerificationError(f"{prefix}.risk must be low|medium|high")
        priority = claim.get("priority", 3)
        if not isinstance(priority, int) or not 1 <= priority <= 5:
            raise VerificationError(f"{prefix}.priority must be an integer 1..5")

        required = claim.get("required_witnesses", [])
        if not isinstance(required, list):
            raise VerificationError(f"{prefix}.required_witnesses must be an array")
        for kind in required:
            if kind not in WITNESS_KINDS:
                raise VerificationError(f"{prefix}.required_witnesses has unknown kind: {kind}")

        witnesses = claim.get("witnesses", [])
        if not isinstance(witnesses, list):
            raise VerificationError(f"{prefix}.witnesses must be an array")
        for w_index, witness in enumerate(witnesses):
            wp = f"{prefix}.witnesses[{w_index}]"
            if not isinstance(witness, dict):
                raise VerificationError(f"{wp} must be an object")
            kind = witness.get("kind")
            if kind not in WITNESS_KINDS:
                raise VerificationError(f"{wp}.kind must be a supported witness kind")
            outcome = witness.get("outcome")
            if outcome not in OUTCOMES:
                raise VerificationError(f"{wp}.outcome must be supports|refutes|inconclusive")
            _nonempty(witness.get("source"), f"{wp}.source")


def assess_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    required = set(claim.get("required_witnesses", []))
    witnesses = claim.get("witnesses", [])
    supporting = [w for w in witnesses if w["outcome"] == "supports"]
    refuting = [w for w in witnesses if w["outcome"] == "refutes"]
    supported_kinds = {w["kind"] for w in supporting}
    missing = sorted(required - supported_kinds)

    if refuting:
        state = "refuted"
    elif claim.get("requires_human_judgement", False):
        state = "open"
    elif required:
        state = "verified" if not missing else "open"
    else:
        state = "verified" if supporting else "open"

    result = dict(claim)
    result["state"] = state
    result["missing_witnesses"] = missing
    result["supporting_witnesses"] = supporting
    result["refuting_witnesses"] = refuting
    return result


def _rank_unresolved(claim: Dict[str, Any]) -> tuple:
    return (
        0 if claim.get("blocking", False) else 1,
        RISK_ORDER[claim.get("risk", "medium")],
        STATE_ORDER[claim["state"]],
        claim.get("priority", 3),
        claim["id"],
    )


def analyse(manifest: Dict[str, Any]) -> Dict[str, Any]:
    validate_manifest(manifest)
    assessed = [assess_claim(c) for c in manifest["claims"] if c.get("material", True)]
    verified = [c for c in assessed if c["state"] == "verified"]
    refuted = [c for c in assessed if c["state"] == "refuted"]
    open_claims = [c for c in assessed if c["state"] == "open"]
    unresolved = sorted(refuted + open_claims, key=_rank_unresolved)

    if refuted:
        overall = "refuted"
    elif open_claims:
        overall = "needs_review"
    else:
        overall = "verified"

    next_claim = unresolved[0] if unresolved else None
    return {
        "version": "2.0",
        "result": manifest["result"].strip(),
        "status": overall,
        "counts": {
            "material": len(assessed),
            "verified": len(verified),
            "open": len(open_claims),
            "refuted": len(refuted),
            "needs_human": len(unresolved),
        },
        "claims": assessed,
        "unresolved": unresolved,
        "do_next": {
            "claim_id": next_claim["id"] if next_claim else None,
            "action": next_claim.get("next_action") if next_claim else "No material verification gap found.",
        },
    }


def _gap_reason(claim: Dict[str, Any]) -> str:
    explicit = claim.get("unresolved_reason")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    if claim["state"] == "refuted":
        witness = claim["refuting_witnesses"][0]
        return f"Refuted by {witness['source']}."
    if claim["missing_witnesses"]:
        return "Missing witness: " + ", ".join(claim["missing_witnesses"]) + "."
    if claim.get("requires_human_judgement", False):
        return "Requires human judgement."
    return "No sufficient independent witness was found."


def render_default(report: Dict[str, Any], max_items: int = 3) -> str:
    lines: List[str] = ["SHOWMEWHY", "", report["result"], ""]
    counts = report["counts"]
    unresolved = report["unresolved"]

    if not unresolved:
        lines.extend([
            "VERIFIED",
            f"{counts['verified']} material claim{'s' if counts['verified'] != 1 else ''} independently settled.",
            "",
            "DO NEXT",
            "No material verification gap found.",
        ])
        return "\n".join(lines)

    if counts["material"] >= 4:
        lines.extend([f"{counts['verified']} verified · {counts['needs_human']} need you", ""])

    lines.append("NEEDS YOU")
    for idx, claim in enumerate(unresolved[:max_items], 1):
        suffixes = []
        if claim["state"] == "refuted":
            suffixes.append("REFUTED")
        if claim.get("risk") == "high":
            suffixes.append("HIGH")
        suffix = f" · {' · '.join(suffixes)}" if suffixes else ""
        lines.append(f"{idx}  {claim['text']}{suffix}")
        lines.append(f"   {_gap_reason(claim)}")

    hidden = len(unresolved) - max_items
    if hidden > 0:
        lines.extend(["", f"+{hidden} more · use why mode"])

    lines.extend(["", "DO NEXT", report["do_next"]["action"] or "Resolve the highest-priority open claim."])
    return "\n".join(lines)


def render_why(report: Dict[str, Any]) -> str:
    lines = ["SHOWMEWHY · WHY", "", report["result"], "", "CLAIMS"]
    for claim in report["claims"]:
        state = claim["state"].upper()
        if state == "VERIFIED":
            source = claim["supporting_witnesses"][0]["source"] if claim["supporting_witnesses"] else "witness satisfied"
            detail = source
        else:
            detail = _gap_reason(claim)
        lines.append(f"{claim['id']:<6} {state:<9} {claim['text']}")
        lines.append(f"       {detail}")
    lines.extend(["", "DO NEXT", report["do_next"]["action"] or "No material verification gap found."])
    return "\n".join(lines)


def load_manifest(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "manifest" in payload:
        return payload["manifest"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a deterministic ShowMeWhy verification surface")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--mode", choices=["default", "why", "json"], default="default")
    parser.add_argument("--max-items", type=int, default=3)
    args = parser.parse_args()

    report = analyse(load_manifest(args.manifest))
    if args.mode == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.mode == "why":
        print(render_why(report))
    else:
        print(render_default(report, max_items=max(1, args.max_items)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
