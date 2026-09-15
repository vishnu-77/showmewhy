from __future__ import annotations

import argparse
import json
import sys

from .evidence import EvidenceStore
from .hook import process_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="showmewhy-runtime")
    sub = parser.add_subparsers(dest="cmd", required=True)

    hook_p = sub.add_parser("hook")
    hook_p.add_argument("--mode", choices=["replace", "shadow"], default=None)
    hook_p.add_argument("--target-tokens", type=int, default=None)

    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("ref")
    inspect_p.add_argument("--cwd", default=".")

    prune_p = sub.add_parser("prune")
    prune_p.add_argument("--days", type=int, default=30)
    prune_p.add_argument("--cwd", default=".")

    args = parser.parse_args(argv)
    if args.cmd == "hook":
        event = json.load(sys.stdin)
        output, _ = process_event(event, mode=args.mode, target_tokens=args.target_tokens)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    if args.cmd == "inspect":
        print(json.dumps(EvidenceStore(args.cwd).get(args.ref), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "prune":
        print(json.dumps({"removed": EvidenceStore(args.cwd).prune(max_age_days=args.days)}))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
