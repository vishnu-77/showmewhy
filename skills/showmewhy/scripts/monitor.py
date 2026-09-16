#!/usr/bin/env python3
"""Deterministic session-level ShowMeWhy verification monitor."""

from __future__ import annotations

import argparse
import json


def assess(verified: int, open_count: int, refuted: int, high_risk_open: int, next_action: str) -> dict:
    for name, value in {
        "verified": verified,
        "open": open_count,
        "refuted": refuted,
        "high_risk_open": high_risk_open,
    }.items():
        if value < 0:
            raise ValueError(f"{name} must be >= 0")
    if high_risk_open > open_count + refuted:
        raise ValueError("high_risk_open cannot exceed unresolved claims")

    if high_risk_open > 0:
        risk = "HIGH"
    elif open_count > 0 or refuted > 0:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    action = next_action.strip() if isinstance(next_action, str) else ""
    if not action:
        action = "No material verification gap found." if risk == "LOW" else "Resolve the highest-value open verification gap."

    return {
        "verified": verified,
        "open": open_count,
        "refuted": refuted,
        "risk": risk,
        "next": action,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ShowMeWhy session verification monitor")
    parser.add_argument("--verified", type=int, default=0)
    parser.add_argument("--open", dest="open_count", type=int, default=0)
    parser.add_argument("--refuted", type=int, default=0)
    parser.add_argument("--high-risk-open", type=int, default=0)
    parser.add_argument("--next", dest="next_action", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = assess(args.verified, args.open_count, args.refuted, args.high_risk_open, args.next_action)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("MONITOR")
    print(f"Verified  {result['verified']}")
    print(f"Open      {result['open']}")
    print(f"Refuted   {result['refuted']}")
    print(f"Risk      {result['risk']}")
    print(f"Next      {result['next']}")


if __name__ == "__main__":
    main()
