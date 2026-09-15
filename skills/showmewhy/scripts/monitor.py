#!/usr/bin/env python3
"""Deterministic ShowMeWhy V0 risk/reward budget monitor."""

from __future__ import annotations

import argparse
import json

BUDGETS = {
    "rewarded": {"min": 1200, "max": 2000, "low": 2000, "medium": 1600, "high": 1200},
    "constrained": {"min": 800, "max": 1800, "low": 1800, "medium": 1300, "high": 800},
}


def assess(evidence_verified: bool, guard_present: bool, risk: str) -> dict:
    state = "rewarded" if evidence_verified and guard_present else "constrained"
    band = BUDGETS[state]
    return {
        "state": state.upper(),
        "risk": risk.upper(),
        "budget_min": band["min"],
        "budget_max": band["max"],
        "recommended_next_tokens": band[risk],
        "evidence_verified": evidence_verified,
        "guard_present": guard_present,
    }


def parse_bool(value: str) -> bool:
    normalised = value.strip().lower()
    if normalised in {"yes", "true", "1"}:
        return True
    if normalised in {"no", "false", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected yes/no, true/false, or 1/0")


def main() -> None:
    parser = argparse.ArgumentParser(description="ShowMeWhy risk/reward monitor")
    parser.add_argument("--evidence-verified", required=True, type=parse_bool)
    parser.add_argument("--guard-present", required=True, type=parse_bool)
    parser.add_argument("--risk", required=True, choices=["low", "medium", "high"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = assess(args.evidence_verified, args.guard_present, args.risk)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"State     {result['state']}")
    print(f"Risk      {result['risk']}")
    print(f"Band      {result['budget_min']}–{result['budget_max']} tokens")
    print(f"Next      {result['recommended_next_tokens']} tokens")


if __name__ == "__main__":
    main()
