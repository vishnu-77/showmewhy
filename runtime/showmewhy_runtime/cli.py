from __future__ import annotations

import argparse
import json

from .compare import compare_runs, load_run
from .evidence import EvidenceStore
from .hook import process_event
from .provenance import load_graph
from .viewer import write_html


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

    prov_p = sub.add_parser("provenance")
    prov_p.add_argument("run_id")
    prov_p.add_argument("--cwd", default=".")

    compare_p = sub.add_parser("compare")
    compare_p.add_argument("before")
    compare_p.add_argument("after")
    compare_p.add_argument("--cwd", default=".")

    view_p = sub.add_parser("view")
    view_p.add_argument("run_id")
    view_p.add_argument("--out", required=True)
    view_p.add_argument("--cwd", default=".")

    args = parser.parse_args(argv)
    if args.cmd == "hook":
        event = json.load(__import__("sys").stdin)
        output, _ = process_event(event, mode=args.mode, target_tokens=args.target_tokens)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    if args.cmd == "inspect":
        print(json.dumps(EvidenceStore(args.cwd).get(args.ref), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "prune":
        print(json.dumps({"removed": EvidenceStore(args.cwd).prune(max_age_days=args.days)}))
        return 0
    if args.cmd == "provenance":
        print(json.dumps(load_graph(args.run_id, args.cwd), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "compare":
        print(json.dumps(compare_runs(load_run(args.before, args.cwd), load_run(args.after, args.cwd)), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "view":
        print(str(write_html(load_graph(args.run_id, args.cwd), args.out)))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
