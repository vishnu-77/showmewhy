#!/usr/bin/env python3
"""Zero-dependency structural validator for ShowMeWhy Receipt V1."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

VISUALS={"text","table","bars","tree","timeline","graph","none"}
NODE_TYPES={"observation","evidence","inference","conclusion","caveat"}
RELATIONS={"supports","contradicts","derived_from","verified_by","correlated_with","caused_by"}
RISKS={"low","medium","high"}
STATES={"rewarded","constrained"}
CONFIDENCE={"high","medium","low","omitted"}
QUALITY={"high","medium","low","unavailable"}

def validate(r: dict) -> list[str]:
    errors=[]
    required={"version","conclusion","signal","visual","why","caveats","confidence","monitor","impact"}
    missing=required-set(r)
    if missing: errors.append("missing: "+", ".join(sorted(missing)))
    if r.get("version")!="1.0": errors.append("version must be 1.0")
    if not isinstance(r.get("conclusion",{}).get("text"),str) or not r.get("conclusion",{}).get("text","").strip(): errors.append("conclusion.text required")
    if r.get("visual",{}).get("type") not in VISUALS: errors.append("invalid visual.type")
    why=r.get("why",{})
    nodes=why.get("nodes",[]) if isinstance(why,dict) else []
    edges=why.get("edges",[]) if isinstance(why,dict) else []
    ids=set()
    for n in nodes:
        if n.get("type") not in NODE_TYPES: errors.append("invalid node type")
        if not n.get("id"): errors.append("node id required")
        elif n["id"] in ids: errors.append("duplicate node id: "+n["id"])
        else: ids.add(n["id"])
    for e in edges:
        if e.get("relation") not in RELATIONS: errors.append("invalid edge relation")
        if e.get("from") not in ids or e.get("to") not in ids: errors.append("edge references unknown node")
    if r.get("confidence",{}).get("level") not in CONFIDENCE: errors.append("invalid confidence.level")
    mon=r.get("monitor",{})
    if mon.get("risk") not in RISKS: errors.append("invalid monitor.risk")
    if mon.get("state") not in STATES: errors.append("invalid monitor.state")
    budget=mon.get("next_budget_tokens")
    if not isinstance(budget,int) or not 800 <= budget <= 2000: errors.append("monitor.next_budget_tokens must be 800..2000")
    imp=r.get("impact",{})
    if imp.get("estimate_quality") not in QUALITY: errors.append("invalid impact.estimate_quality")
    out=imp.get("output_tokens"); cap=imp.get("budget_tokens")
    if not isinstance(out,int) or out<0: errors.append("impact.output_tokens must be >=0 integer")
    if not isinstance(cap,int) or cap<1: errors.append("impact.budget_tokens must be positive integer")
    return errors

def main():
    p=argparse.ArgumentParser()
    p.add_argument("receipt",type=Path)
    args=p.parse_args()
    data=json.loads(args.receipt.read_text())
    errors=validate(data)
    if errors:
        for e in errors: print(f"ERROR: {e}",file=sys.stderr)
        return 1
    print("valid ShowMeWhy Receipt v1.0")
    return 0

if __name__=="__main__": raise SystemExit(main())
