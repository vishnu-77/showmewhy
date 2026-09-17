from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


class BenchmarkValidationError(ValueError):
    pass


def _ids(value: Any, field: str) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise BenchmarkValidationError(f"{field} must be a list of non-empty string ids")
    if len(value) != len(set(value)):
        raise BenchmarkValidationError(f"{field} contains duplicate ids")
    return set(value)


def _number(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise BenchmarkValidationError(f"{field} must be a non-negative number")
    return float(value)


def _ratio(num: float, den: float) -> float:
    return 0.0 if den == 0 else num / den


def _reduction(current: float, baseline: float) -> float:
    if baseline <= 0:
        raise BenchmarkValidationError("paired baseline must be greater than zero for reduction metrics")
    return 1.0 - (current / baseline)


@dataclass(frozen=True)
class AggregateScore:
    tasks: int
    material_claims: int
    material_failures: int
    detected_material_failures: int
    missed_material_failures: int
    material_failure_recall: float
    material_failure_miss_rate: float
    verified_claims: int
    false_closures: int
    false_closure_rate: float
    expected_human_review_claims: int
    surfaced_claims: int
    correctly_surfaced_claims: int
    verification_surface_precision: float
    verification_surface_recall: float
    verification_surface_reduction: float
    ground_truth_counterexamples: int
    detected_counterexamples: int
    counterexample_recall: float
    inspection_token_reduction: float
    inspection_line_reduction: float
    verification_time_reduction: float


def validate_record(record: dict[str, Any]) -> None:
    if not isinstance(record, dict):
        raise BenchmarkValidationError("each benchmark record must be an object")
    if not isinstance(record.get("task_id"), str) or not record["task_id"]:
        raise BenchmarkValidationError("task_id must be a non-empty string")
    if not isinstance(record.get("domain"), str) or not record["domain"]:
        raise BenchmarkValidationError("domain must be a non-empty string")

    gt = record.get("ground_truth")
    baseline = record.get("baseline")
    smw = record.get("showmewhy")
    if not isinstance(gt, dict) or not isinstance(baseline, dict) or not isinstance(smw, dict):
        raise BenchmarkValidationError("ground_truth, baseline and showmewhy must be objects")

    material = _ids(gt.get("material_claim_ids"), "ground_truth.material_claim_ids")
    failures = _ids(gt.get("failing_claim_ids"), "ground_truth.failing_claim_ids")
    human_review = _ids(gt.get("human_review_claim_ids"), "ground_truth.human_review_claim_ids")
    _ids(gt.get("counterexample_ids"), "ground_truth.counterexample_ids")

    if not material:
        raise BenchmarkValidationError("ground_truth.material_claim_ids must not be empty")
    if not failures <= material:
        raise BenchmarkValidationError("failing_claim_ids must be a subset of material_claim_ids")
    if not human_review <= material:
        raise BenchmarkValidationError("human_review_claim_ids must be a subset of material_claim_ids")

    baseline_inspected = _ids(baseline.get("inspected_claim_ids"), "baseline.inspected_claim_ids")
    if not baseline_inspected:
        raise BenchmarkValidationError("baseline.inspected_claim_ids must not be empty")
    if not baseline_inspected <= material:
        raise BenchmarkValidationError("baseline.inspected_claim_ids must be a subset of material_claim_ids")
    _number(baseline.get("inspection_tokens"), "baseline.inspection_tokens")
    _number(baseline.get("inspection_lines"), "baseline.inspection_lines")
    _number(baseline.get("verification_seconds"), "baseline.verification_seconds")

    surfaced = _ids(smw.get("surfaced_claim_ids"), "showmewhy.surfaced_claim_ids")
    verified = _ids(smw.get("verified_claim_ids"), "showmewhy.verified_claim_ids")
    refuted = _ids(smw.get("refuted_claim_ids"), "showmewhy.refuted_claim_ids")
    opened = _ids(smw.get("open_claim_ids"), "showmewhy.open_claim_ids")
    detected_failures = _ids(smw.get("detected_failure_ids"), "showmewhy.detected_failure_ids")
    detected_counterexamples = _ids(smw.get("detected_counterexample_ids"), "showmewhy.detected_counterexample_ids")

    for field, ids in (("surfaced", surfaced), ("verified", verified), ("refuted", refuted), ("open", opened)):
        if not ids <= material:
            raise BenchmarkValidationError(f"showmewhy {field} claim ids must be a subset of material_claim_ids")

    if verified & refuted or verified & opened or refuted & opened:
        raise BenchmarkValidationError("verified/refuted/open claim sets must be pairwise disjoint")
    if surfaced != opened:
        raise BenchmarkValidationError("surfaced_claim_ids must exactly match open_claim_ids for the default V5 verification surface")
    if not detected_failures <= failures:
        raise BenchmarkValidationError("detected_failure_ids must be a subset of ground-truth failing_claim_ids")

    counterexamples = set(gt["counterexample_ids"])
    if not detected_counterexamples <= counterexamples:
        raise BenchmarkValidationError("detected_counterexample_ids must be a subset of ground-truth counterexample_ids")

    _number(smw.get("inspection_tokens"), "showmewhy.inspection_tokens")
    _number(smw.get("inspection_lines"), "showmewhy.inspection_lines")
    _number(smw.get("verification_seconds"), "showmewhy.verification_seconds")


def score_records(records: Iterable[dict[str, Any]]) -> AggregateScore:
    rows = list(records)
    if not rows:
        raise BenchmarkValidationError("benchmark corpus must contain at least one task")
    for row in rows:
        validate_record(row)

    material_claims = 0
    failures: set[tuple[str, str]] = set()
    detected_failures: set[tuple[str, str]] = set()
    verified_count = 0
    false_closures = 0
    expected_review: set[tuple[str, str]] = set()
    surfaced: set[tuple[str, str]] = set()
    correctly_surfaced: set[tuple[str, str]] = set()
    counterexamples: set[tuple[str, str]] = set()
    detected_counterexamples: set[tuple[str, str]] = set()

    baseline_surface = 0
    baseline_tokens = 0.0
    baseline_lines = 0.0
    baseline_seconds = 0.0
    smw_tokens = 0.0
    smw_lines = 0.0
    smw_seconds = 0.0

    for row in rows:
        task_id = row["task_id"]
        gt = row["ground_truth"]
        baseline = row["baseline"]
        smw = row["showmewhy"]

        material = set(gt["material_claim_ids"])
        failing = set(gt["failing_claim_ids"])
        review = set(gt["human_review_claim_ids"])
        gt_counter = set(gt["counterexample_ids"])
        smw_surface = set(smw["surfaced_claim_ids"])
        smw_verified = set(smw["verified_claim_ids"])

        material_claims += len(material)
        failures |= {(task_id, claim_id) for claim_id in failing}
        detected_failures |= {(task_id, claim_id) for claim_id in smw["detected_failure_ids"]}
        expected_review |= {(task_id, claim_id) for claim_id in review}
        surfaced |= {(task_id, claim_id) for claim_id in smw_surface}
        correctly_surfaced |= {(task_id, claim_id) for claim_id in (smw_surface & review)}
        counterexamples |= {(task_id, item_id) for item_id in gt_counter}
        detected_counterexamples |= {(task_id, item_id) for item_id in smw["detected_counterexample_ids"]}

        verified_count += len(smw_verified)
        false_closures += len(smw_verified & (failing | review))

        baseline_surface += len(baseline["inspected_claim_ids"])
        baseline_tokens += float(baseline["inspection_tokens"])
        baseline_lines += float(baseline["inspection_lines"])
        baseline_seconds += float(baseline["verification_seconds"])
        smw_tokens += float(smw["inspection_tokens"])
        smw_lines += float(smw["inspection_lines"])
        smw_seconds += float(smw["verification_seconds"])

    detected_failure_count = len(detected_failures)
    failure_count = len(failures)
    missed_failure_count = failure_count - detected_failure_count

    return AggregateScore(
        tasks=len(rows),
        material_claims=material_claims,
        material_failures=failure_count,
        detected_material_failures=detected_failure_count,
        missed_material_failures=missed_failure_count,
        material_failure_recall=_ratio(detected_failure_count, failure_count),
        material_failure_miss_rate=_ratio(missed_failure_count, failure_count),
        verified_claims=verified_count,
        false_closures=false_closures,
        false_closure_rate=_ratio(false_closures, verified_count),
        expected_human_review_claims=len(expected_review),
        surfaced_claims=len(surfaced),
        correctly_surfaced_claims=len(correctly_surfaced),
        verification_surface_precision=_ratio(len(correctly_surfaced), len(surfaced)),
        verification_surface_recall=_ratio(len(correctly_surfaced), len(expected_review)),
        verification_surface_reduction=_reduction(len(surfaced), baseline_surface),
        ground_truth_counterexamples=len(counterexamples),
        detected_counterexamples=len(detected_counterexamples),
        counterexample_recall=_ratio(len(detected_counterexamples), len(counterexamples)),
        inspection_token_reduction=_reduction(smw_tokens, baseline_tokens),
        inspection_line_reduction=_reduction(smw_lines, baseline_lines),
        verification_time_reduction=_reduction(smw_seconds, baseline_seconds),
    )


def load_records(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("tasks")
    if not isinstance(data, list):
        raise BenchmarkValidationError("benchmark JSON must be a list or an object with a tasks list")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a paired ShowMeWhy V5 verification benchmark corpus.")
    parser.add_argument("corpus", type=Path, help="JSON corpus containing paired baseline and ShowMeWhy results")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON metrics")
    args = parser.parse_args()

    score = score_records(load_records(args.corpus))
    print(json.dumps(asdict(score), indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
