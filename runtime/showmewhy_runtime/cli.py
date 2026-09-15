from __future__ import annotations

import argparse
import json
import sys

from .compare import compare_runs, load_run
from .evidence import EvidenceStore
from .hook import process_event
from .policy import clear_safety_lock, recommend_policy, record_feedback
from .provenance import load_graph
from .viewer import write_html


def _yes_no(value: str) -> bool:
    normal = value.strip().lower()
    if normal in {"yes", "true", "1"}:
        return True
    if normal in {"no", "false", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected yes/no")


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

    feedback_p = sub.add_parser("feedback")
    feedback_p.add_argument("run_id")
    feedback_p.add_argument("--reopened", required=True, type=_yes_no)
    feedback_p.add_argument("--material-loss", required=True, type=_yes_no)
    feedback_p.add_argument("--cwd", default=".")

    policy_p = sub.add_parser("policy")
    policy_p.add_argument("--cwd", default=".")

    unlock_p = sub.add_parser("policy-unlock")
    unlock_p.add_argument("--cwd", default=".")

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
    if args.cmd == "provenance":
        print(json.dumps(load_graph(args.run_id, args.cwd), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "compare":
        print(json.dumps(compare_runs(load_run(args.before, args.cwd), load_run(args.after, args.cwd)), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "view":
        print(str(write_html(load_graph(args.run_id, args.cwd), args.out)))
        return 0
    if args.cmd == "feedback":
        print(json.dumps(record_feedback(args.run_id, reopened=args.reopened, material_loss=args.material_loss, cwd=args.cwd), indent=2))
        return 0
    if args.cmd == "policy":
        print(json.dumps(recommend_policy(args.cwd), indent=2))
        return 0
    if args.cmd == "policy-unlock":
        print(json.dumps(clear_safety_lock(args.cwd), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
