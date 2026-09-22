#!/usr/bin/env python3
"""Build blinded V5 label packets and scoreable records from raw paired evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


class RecordBuildError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecordBuildError(f"{path} must contain a JSON object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ids(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise RecordBuildError(f"{field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise RecordBuildError(f"{field} contains duplicate ids")
    return value


def _pairing_anchor(pair: dict[str, Any]) -> dict[str, Any]:
    pairing = pair.get("pairing")
    if not isinstance(pairing, dict):
        raise RecordBuildError("pair.pairing must be an object")
    required = (
        "pair_id",
        "repository",
        "revision",
        "task_prompt_sha256",
        "model",
        "agent_runtime",
        "tool_profile",
        "repeat_index",
    )
    for field in required:
        if field not in pairing:
            raise RecordBuildError(f"pair.pairing.{field} is required")
    return {field: pairing[field] for field in required}


def _validate_pair(pair: dict[str, Any]) -> None:
    if pair.get("version") != "v5-pair-run-1":
        raise RecordBuildError("pair must use v5-pair-run-1")
    if pair.get("pair_status") != "valid":
        raise RecordBuildError("only a valid pair can become scoreable")
    if pair.get("ground_truth_present") is not False:
        raise RecordBuildError("raw pair must remain ground-truth blind")
    conditions = pair.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != {"baseline", "showmewhy"}:
        raise RecordBuildError("pair must contain exactly baseline and showmewhy conditions")
    for name in ("baseline", "showmewhy"):
        if conditions[name].get("status") != "valid":
            raise RecordBuildError(f"{name} condition is not valid")


def build_ground_truth_template(
    *,
    manifest_path: Path,
    pair_path: Path,
    task_id: str,
) -> dict[str, Any]:
    """Create a label packet without reading either condition's output files."""

    manifest = _load(manifest_path)
    pair = _load(pair_path)
    _validate_pair(pair)
    if pair.get("task_id") != task_id:
        raise RecordBuildError("pair task_id does not match requested task")

    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        raise RecordBuildError("pilot manifest.tasks must be a list")
    matches = [task for task in tasks if task.get("task_id") == task_id]
    if len(matches) != 1:
        raise RecordBuildError(f"expected exactly one pilot task {task_id!r}")
    task = matches[0]

    anchor = _pairing_anchor(pair)
    checks = {
        "repository": task.get("repository"),
        "revision": task.get("pre_fix_revision"),
        "task_prompt_sha256": task.get("task_prompt_sha256"),
    }
    for field, expected in checks.items():
        if anchor[field] != expected:
            raise RecordBuildError(
                f"pairing {field} does not match frozen pilot manifest"
            )

    # Intentionally no baseline/showmewhy result, diff, stdout or condition metadata.
    return {
        "version": "v5-ground-truth-1",
        "task_id": task_id,
        "domain": pair.get("domain"),
        "pairing": anchor,
        "task_prompt": task.get("task_prompt"),
        "oracle_refs": list(task.get("oracle_refs") or []),
        "boundary_notes": task.get("boundary_notes"),
        "labeler_count": None,
        "adjudicated": False,
        "blinded_to_showmewhy": False,
        "claims": [],
    }


def _validate_ground_truth(
    ground_truth: dict[str, Any],
    pair: dict[str, Any],
) -> tuple[list[dict[str, Any]], set[str]]:
    if ground_truth.get("version") != "v5-ground-truth-1":
        raise RecordBuildError("ground truth must use v5-ground-truth-1")
    if ground_truth.get("task_id") != pair.get("task_id"):
        raise RecordBuildError("ground truth task_id does not match pair")
    if ground_truth.get("pairing") != _pairing_anchor(pair):
        raise RecordBuildError("ground truth pairing anchor does not match pair")
    if ground_truth.get("blinded_to_showmewhy") is not True:
        raise RecordBuildError(
            "ground truth must explicitly attest blinded_to_showmewhy=true"
        )
    labeler_count = ground_truth.get("labeler_count")
    if (
        not isinstance(labeler_count, int)
        or isinstance(labeler_count, bool)
        or labeler_count < 1
    ):
        raise RecordBuildError("ground truth labeler_count must be >= 1")
    if not isinstance(ground_truth.get("adjudicated"), bool):
        raise RecordBuildError("ground truth adjudicated must be boolean")

    refs = _ids(ground_truth.get("oracle_refs"), "ground_truth.oracle_refs")
    if not refs:
        raise RecordBuildError("ground truth oracle_refs must not be empty")

    claims = ground_truth.get("claims")
    if not isinstance(claims, list) or not claims:
        raise RecordBuildError("ground truth claims must be a non-empty list")
    seen: set[str] = set()
    material: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise RecordBuildError(f"ground_truth.claims[{index}] must be an object")
        cid = claim.get("id")
        text = claim.get("text")
        if not isinstance(cid, str) or not cid:
            raise RecordBuildError(f"ground_truth.claims[{index}].id is required")
        if cid in seen:
            raise RecordBuildError(f"duplicate ground truth claim id: {cid}")
        seen.add(cid)
        if not isinstance(text, str) or not text.strip():
            raise RecordBuildError(f"ground_truth.claims[{index}].text is required")
        for flag in ("material", "failing", "human_review", "counterexample"):
            if not isinstance(claim.get(flag), bool):
                raise RecordBuildError(
                    f"ground_truth.claims[{index}].{flag} must be boolean"
                )
        if claim["material"]:
            material.add(cid)
        elif claim["failing"] or claim["human_review"]:
            raise RecordBuildError(
                f"non-material claim {cid} cannot be failing or require human review"
            )
    if not material:
        raise RecordBuildError("ground truth must contain at least one material claim")
    return claims, material


def build_assessment_template(
    *,
    pair_path: Path,
    ground_truth_path: Path,
) -> dict[str, Any]:
    pair = _load(pair_path)
    _validate_pair(pair)
    gt = _load(ground_truth_path)
    claims, material = _validate_ground_truth(gt, pair)
    pair_dir = pair_path.parent

    evidence: dict[str, dict[str, Any]] = {}
    for condition in ("baseline", "showmewhy"):
        result_path = pair_dir / condition / "result.txt"
        if not result_path.is_file():
            raise RecordBuildError(f"missing {condition} result.txt")
        evidence[condition] = {
            "result_path": str(result_path),
            "result_sha256": _sha256(result_path),
        }

    return {
        "version": "v5-assessment-1",
        "task_id": pair["task_id"],
        "pair_id": pair["pairing"]["pair_id"],
        "claim_catalog": [
            {"id": claim["id"], "text": claim["text"]}
            for claim in claims
            if claim["id"] in material
        ],
        "evidence": evidence,
        "baseline": {
            "inspected_claim_ids": [],
            "detected_failure_ids": [],
            "detected_counterexample_ids": [],
            "verification_seconds": None,
        },
        "showmewhy": {
            "surfaced_claim_ids": [],
            "verified_claim_ids": [],
            "refuted_claim_ids": [],
            "open_claim_ids": [],
            "detected_failure_ids": [],
            "detected_counterexample_ids": [],
            "verification_seconds": None,
        },
    }


def _measure_text(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    tokens = 0 if not data else max(1, (len(data) + 3) // 4)
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return tokens, lines


def _seconds(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < 0
    ):
        raise RecordBuildError(f"{field} must be a non-negative number")
    return float(value)


def assemble_record(
    *,
    pair_path: Path,
    ground_truth_path: Path,
    assessment_path: Path,
) -> dict[str, Any]:
    pair = _load(pair_path)
    _validate_pair(pair)
    gt = _load(ground_truth_path)
    claims, material = _validate_ground_truth(gt, pair)
    assessment = _load(assessment_path)

    if assessment.get("version") != "v5-assessment-1":
        raise RecordBuildError("assessment must use v5-assessment-1")
    if assessment.get("task_id") != pair["task_id"]:
        raise RecordBuildError("assessment task_id does not match pair")
    if assessment.get("pair_id") != pair["pairing"]["pair_id"]:
        raise RecordBuildError("assessment pair_id does not match pair")

    pair_dir = pair_path.parent
    for condition in ("baseline", "showmewhy"):
        evidence = assessment.get("evidence", {}).get(condition)
        if not isinstance(evidence, dict):
            raise RecordBuildError(f"assessment.evidence.{condition} is required")
        result_path = pair_dir / condition / "result.txt"
        if not result_path.is_file():
            raise RecordBuildError(f"missing {condition} result.txt")
        if evidence.get("result_sha256") != _sha256(result_path):
            raise RecordBuildError(
                f"assessment {condition} result hash does not match captured evidence"
            )

    gt_material = {claim["id"] for claim in claims if claim["material"]}
    failures = {claim["id"] for claim in claims if claim["material"] and claim["failing"]}
    review = {
        claim["id"]
        for claim in claims
        if claim["material"] and claim["human_review"]
    }
    counterexamples = {
        claim["id"] for claim in claims if claim["counterexample"]
    }

    baseline = assessment.get("baseline")
    showmewhy = assessment.get("showmewhy")
    if not isinstance(baseline, dict) or not isinstance(showmewhy, dict):
        raise RecordBuildError("assessment baseline/showmewhy blocks are required")

    baseline_ids = {
        "inspected_claim_ids": _ids(
            baseline.get("inspected_claim_ids"),
            "assessment.baseline.inspected_claim_ids",
        ),
        "detected_failure_ids": _ids(
            baseline.get("detected_failure_ids"),
            "assessment.baseline.detected_failure_ids",
        ),
        "detected_counterexample_ids": _ids(
            baseline.get("detected_counterexample_ids"),
            "assessment.baseline.detected_counterexample_ids",
        ),
    }
    smw_ids = {
        field: _ids(showmewhy.get(field), f"assessment.showmewhy.{field}")
        for field in (
            "surfaced_claim_ids",
            "verified_claim_ids",
            "refuted_claim_ids",
            "open_claim_ids",
            "detected_failure_ids",
            "detected_counterexample_ids",
        )
    }

    for field, values in {**baseline_ids, **smw_ids}.items():
        if not set(values) <= gt_material:
            raise RecordBuildError(f"{field} contains ids outside material claim catalog")

    if set(smw_ids["surfaced_claim_ids"]) != set(smw_ids["open_claim_ids"]):
        raise RecordBuildError("ShowMeWhy surfaced_claim_ids must equal open_claim_ids")
    closed_sets = [
        set(smw_ids["verified_claim_ids"]),
        set(smw_ids["refuted_claim_ids"]),
        set(smw_ids["open_claim_ids"]),
    ]
    if (
        closed_sets[0] & closed_sets[1]
        or closed_sets[0] & closed_sets[2]
        or closed_sets[1] & closed_sets[2]
    ):
        raise RecordBuildError("ShowMeWhy closure sets must be pairwise disjoint")

    baseline_tokens, baseline_lines = _measure_text(pair_dir / "baseline" / "result.txt")
    smw_tokens, smw_lines = _measure_text(pair_dir / "showmewhy" / "result.txt")

    return {
        "task_id": pair["task_id"],
        "domain": pair["domain"],
        "pairing": _pairing_anchor(pair),
        "ground_truth": {
            "material_claim_ids": sorted(gt_material),
            "failing_claim_ids": sorted(failures),
            "human_review_claim_ids": sorted(review),
            "counterexample_ids": sorted(counterexamples),
            "oracle_refs": list(gt["oracle_refs"]),
            "labeler_count": gt["labeler_count"],
            "adjudicated": gt["adjudicated"],
            "blinded_to_showmewhy": True,
        },
        "baseline": {
            **baseline_ids,
            "inspection_tokens": baseline_tokens,
            "inspection_lines": baseline_lines,
            "verification_seconds": _seconds(
                baseline.get("verification_seconds"),
                "assessment.baseline.verification_seconds",
            ),
        },
        "showmewhy": {
            **smw_ids,
            "inspection_tokens": smw_tokens,
            "inspection_lines": smw_lines,
            "verification_seconds": _seconds(
                showmewhy.get("verification_seconds"),
                "assessment.showmewhy.verification_seconds",
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V5 blinded labels and scoreable records")
    sub = parser.add_subparsers(dest="command", required=True)

    gt = sub.add_parser("ground-truth-template")
    gt.add_argument("--manifest", type=Path, required=True)
    gt.add_argument("--pair", type=Path, required=True)
    gt.add_argument("--task-id", required=True)
    gt.add_argument("--out", type=Path, required=True)

    assess = sub.add_parser("assessment-template")
    assess.add_argument("--pair", type=Path, required=True)
    assess.add_argument("--ground-truth", type=Path, required=True)
    assess.add_argument("--out", type=Path, required=True)

    assemble = sub.add_parser("assemble")
    assemble.add_argument("--pair", type=Path, required=True)
    assemble.add_argument("--ground-truth", type=Path, required=True)
    assemble.add_argument("--assessment", type=Path, required=True)
    assemble.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "ground-truth-template":
            value = build_ground_truth_template(
                manifest_path=args.manifest,
                pair_path=args.pair,
                task_id=args.task_id,
            )
        elif args.command == "assessment-template":
            value = build_assessment_template(
                pair_path=args.pair,
                ground_truth_path=args.ground_truth,
            )
        else:
            value = assemble_record(
                pair_path=args.pair,
                ground_truth_path=args.ground_truth,
                assessment_path=args.assessment,
            )
        _write(args.out, value)
    except RecordBuildError as exc:
        print(f"V5 record build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
