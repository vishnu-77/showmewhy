from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
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


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkValidationError(f"{field} must be a non-empty string")
    return value


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


def _keyed(task_id: str, ids: set[str]) -> set[tuple[str, str]]:
    return {(task_id, item_id) for item_id in ids}


@dataclass(frozen=True)
class AggregateScore:
    tasks: int
    material_claims: int
    classified_material_claims: int
    claim_classification_coverage: float
    material_failures: int
    baseline_reported_failures: int
    baseline_detected_material_failures: int
    baseline_false_failure_detections: int
    baseline_material_failure_recall: float
    baseline_material_failure_precision: float
    showmewhy_reported_failures: int
    detected_material_failures: int
    false_failure_detections: int
    missed_material_failures: int
    material_failure_recall: float
    material_failure_precision: float
    material_failure_recall_delta: float
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
    baseline_reported_counterexamples: int
    baseline_detected_counterexamples: int
    baseline_false_counterexample_detections: int
    baseline_counterexample_recall: float
    baseline_counterexample_precision: float
    showmewhy_reported_counterexamples: int
    detected_counterexamples: int
    false_counterexample_detections: int
    counterexample_recall: float
    counterexample_precision: float
    inspection_token_reduction: float
    inspection_line_reduction: float
    verification_time_reduction: float


def validate_record(record: dict[str, Any]) -> None:
    if not isinstance(record, dict):
        raise BenchmarkValidationError("each benchmark record must be an object")
    _string(record.get("task_id"), "task_id")
    _string(record.get("domain"), "domain")

    pairing = record.get("pairing")
    gt = record.get("ground_truth")
    baseline = record.get("baseline")
    smw = record.get("showmewhy")
    if not isinstance(pairing, dict):
        raise BenchmarkValidationError("pairing must be an object")
    if not isinstance(gt, dict) or not isinstance(baseline, dict) or not isinstance(smw, dict):
        raise BenchmarkValidationError("ground_truth, baseline and showmewhy must be objects")

    for field in ("pair_id", "repository", "revision", "model", "agent_runtime", "tool_profile"):
        _string(pairing.get(field), f"pairing.{field}")
    prompt_hash = _string(pairing.get("task_prompt_sha256"), "pairing.task_prompt_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", prompt_hash):
        raise BenchmarkValidationError("pairing.task_prompt_sha256 must be a lowercase 64-character SHA-256 hex digest")
    repeat_index = pairing.get("repeat_index")
    if not isinstance(repeat_index, int) or isinstance(repeat_index, bool) or repeat_index < 0:
        raise BenchmarkValidationError("pairing.repeat_index must be a non-negative integer")

    material = _ids(gt.get("material_claim_ids"), "ground_truth.material_claim_ids")
    failures = _ids(gt.get("failing_claim_ids"), "ground_truth.failing_claim_ids")
    human_review = _ids(gt.get("human_review_claim_ids"), "ground_truth.human_review_claim_ids")
    _ids(gt.get("counterexample_ids"), "ground_truth.counterexample_ids")
    oracle_refs = _ids(gt.get("oracle_refs"), "ground_truth.oracle_refs")
    labeler_count = gt.get("labeler_count")
    if not isinstance(labeler_count, int) or isinstance(labeler_count, bool) or labeler_count < 1:
        raise BenchmarkValidationError("ground_truth.labeler_count must be a positive integer")
    if not isinstance(gt.get("adjudicated"), bool):
        raise BenchmarkValidationError("ground_truth.adjudicated must be boolean")
    if gt.get("blinded_to_showmewhy") is not True:
        raise BenchmarkValidationError("ground_truth.blinded_to_showmewhy must be true")

    if not material:
        raise BenchmarkValidationError("ground_truth.material_claim_ids must not be empty")
    if not oracle_refs:
        raise BenchmarkValidationError("ground_truth.oracle_refs must not be empty")
    if not failures <= material:
        raise BenchmarkValidationError("failing_claim_ids must be a subset of material_claim_ids")
    if not human_review <= material:
        raise BenchmarkValidationError("human_review_claim_ids must be a subset of material_claim_ids")

    baseline_inspected = _ids(baseline.get("inspected_claim_ids"), "baseline.inspected_claim_ids")
    baseline_failures = _ids(baseline.get("detected_failure_ids"), "baseline.detected_failure_ids")
    _ids(baseline.get("detected_counterexample_ids"), "baseline.detected_counterexample_ids")
    if not baseline_inspected:
        raise BenchmarkValidationError("baseline.inspected_claim_ids must not be empty")
    if not baseline_inspected <= material:
        raise BenchmarkValidationError("baseline.inspected_claim_ids must be a subset of material_claim_ids")
    if not baseline_failures <= material:
        raise BenchmarkValidationError("baseline.detected_failure_ids must be a subset of material_claim_ids")
    _number(baseline.get("inspection_tokens"), "baseline.inspection_tokens")
    _number(baseline.get("inspection_lines"), "baseline.inspection_lines")
    _number(baseline.get("verification_seconds"), "baseline.verification_seconds")

    surfaced = _ids(smw.get("surfaced_claim_ids"), "showmewhy.surfaced_claim_ids")
    verified = _ids(smw.get("verified_claim_ids"), "showmewhy.verified_claim_ids")
    refuted = _ids(smw.get("refuted_claim_ids"), "showmewhy.refuted_claim_ids")
    opened = _ids(smw.get("open_claim_ids"), "showmewhy.open_claim_ids")
    detected_failures = _ids(smw.get("detected_failure_ids"), "showmewhy.detected_failure_ids")
    _ids(smw.get("detected_counterexample_ids"), "showmewhy.detected_counterexample_ids")

    for field, ids in (("surfaced", surfaced), ("verified", verified), ("refuted", refuted), ("open", opened)):
        if not ids <= material:
            raise BenchmarkValidationError(f"showmewhy {field} claim ids must be a subset of material_claim_ids")

    if not detected_failures <= material:
        raise BenchmarkValidationError("showmewhy.detected_failure_ids must be a subset of material_claim_ids")
    if verified & refuted or verified & opened or refuted & opened:
        raise BenchmarkValidationError("verified/refuted/open claim sets must be pairwise disjoint")
    if surfaced != opened:
        raise BenchmarkValidationError("surfaced_claim_ids must exactly match open_claim_ids for the default V5 verification surface")

    _number(smw.get("inspection_tokens"), "showmewhy.inspection_tokens")
    _number(smw.get("inspection_lines"), "showmewhy.inspection_lines")
    _number(smw.get("verification_seconds"), "showmewhy.verification_seconds")


def score_records(records: Iterable[dict[str, Any]]) -> AggregateScore:
    rows = list(records)
    if not rows:
        raise BenchmarkValidationError("benchmark corpus must contain at least one task")

    task_ids = [row.get("task_id") for row in rows if isinstance(row, dict)]
    if len(task_ids) != len(set(task_ids)):
        raise BenchmarkValidationError("task_id values must be unique across the corpus")
    pair_ids = [row.get("pairing", {}).get("pair_id") for row in rows if isinstance(row, dict)]
    if len(pair_ids) != len(set(pair_ids)):
        raise BenchmarkValidationError("pairing.pair_id values must be unique across the corpus")
    for row in rows:
        validate_record(row)

    material_claims = 0
    classified_claims: set[tuple[str, str]] = set()
    failures: set[tuple[str, str]] = set()
    baseline_reported_failures: set[tuple[str, str]] = set()
    smw_reported_failures: set[tuple[str, str]] = set()
    expected_review: set[tuple[str, str]] = set()
    surfaced: set[tuple[str, str]] = set()
    correctly_surfaced: set[tuple[str, str]] = set()
    counterexamples: set[tuple[str, str]] = set()
    baseline_reported_counterexamples: set[tuple[str, str]] = set()
    smw_reported_counterexamples: set[tuple[str, str]] = set()
    verified_count = 0
    false_closures = 0

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
        baseline_failure_ids = set(baseline["detected_failure_ids"])
        baseline_counter_ids = set(baseline["detected_counterexample_ids"])
        smw_surface = set(smw["surfaced_claim_ids"])
        smw_verified = set(smw["verified_claim_ids"])
        smw_refuted = set(smw["refuted_claim_ids"])
        smw_open = set(smw["open_claim_ids"])
        smw_failure_ids = set(smw["detected_failure_ids"])
        smw_counter_ids = set(smw["detected_counterexample_ids"])

        material_claims += len(material)
        failures |= _keyed(task_id, failing)
        baseline_reported_failures |= _keyed(task_id, baseline_failure_ids)
        smw_reported_failures |= _keyed(task_id, smw_failure_ids)
        expected_review |= _keyed(task_id, review)
        surfaced |= _keyed(task_id, smw_surface)
        correctly_surfaced |= _keyed(task_id, smw_surface & review)
        classified_claims |= _keyed(task_id, smw_verified | smw_refuted | smw_open)
        counterexamples |= _keyed(task_id, gt_counter)
        baseline_reported_counterexamples |= _keyed(task_id, baseline_counter_ids)
        smw_reported_counterexamples |= _keyed(task_id, smw_counter_ids)

        verified_count += len(smw_verified)
        false_closures += len(smw_verified & (failing | review))

        baseline_surface += len(baseline["inspected_claim_ids"])
        baseline_tokens += float(baseline["inspection_tokens"])
        baseline_lines += float(baseline["inspection_lines"])
        baseline_seconds += float(baseline["verification_seconds"])
        smw_tokens += float(smw["inspection_tokens"])
        smw_lines += float(smw["inspection_lines"])
        smw_seconds += float(smw["verification_seconds"])

    if not failures:
        raise BenchmarkValidationError("benchmark corpus must contain at least one ground-truth material failure")
    if not expected_review:
        raise BenchmarkValidationError("benchmark corpus must contain at least one claim requiring human review")

    baseline_true_failures = baseline_reported_failures & failures
    baseline_false_failures = baseline_reported_failures - failures
    smw_true_failures = smw_reported_failures & failures
    smw_false_failures = smw_reported_failures - failures
    missed_failures = failures - smw_true_failures

    baseline_true_counterexamples = baseline_reported_counterexamples & counterexamples
    baseline_false_counterexamples = baseline_reported_counterexamples - counterexamples
    smw_true_counterexamples = smw_reported_counterexamples & counterexamples
    smw_false_counterexamples = smw_reported_counterexamples - counterexamples

    baseline_failure_recall = _ratio(len(baseline_true_failures), len(failures))
    smw_failure_recall = _ratio(len(smw_true_failures), len(failures))

    return AggregateScore(
        tasks=len(rows),
        material_claims=material_claims,
        classified_material_claims=len(classified_claims),
        claim_classification_coverage=_ratio(len(classified_claims), material_claims),
        material_failures=len(failures),
        baseline_reported_failures=len(baseline_reported_failures),
        baseline_detected_material_failures=len(baseline_true_failures),
        baseline_false_failure_detections=len(baseline_false_failures),
        baseline_material_failure_recall=baseline_failure_recall,
        baseline_material_failure_precision=_ratio(len(baseline_true_failures), len(baseline_reported_failures)),
        showmewhy_reported_failures=len(smw_reported_failures),
        detected_material_failures=len(smw_true_failures),
        false_failure_detections=len(smw_false_failures),
        missed_material_failures=len(missed_failures),
        material_failure_recall=smw_failure_recall,
        material_failure_precision=_ratio(len(smw_true_failures), len(smw_reported_failures)),
        material_failure_recall_delta=smw_failure_recall - baseline_failure_recall,
        material_failure_miss_rate=_ratio(len(missed_failures), len(failures)),
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
        baseline_reported_counterexamples=len(baseline_reported_counterexamples),
        baseline_detected_counterexamples=len(baseline_true_counterexamples),
        baseline_false_counterexample_detections=len(baseline_false_counterexamples),
        baseline_counterexample_recall=_ratio(len(baseline_true_counterexamples), len(counterexamples)),
        baseline_counterexample_precision=_ratio(len(baseline_true_counterexamples), len(baseline_reported_counterexamples)),
        showmewhy_reported_counterexamples=len(smw_reported_counterexamples),
        detected_counterexamples=len(smw_true_counterexamples),
        false_counterexample_detections=len(smw_false_counterexamples),
        counterexample_recall=_ratio(len(smw_true_counterexamples), len(counterexamples)),
        counterexample_precision=_ratio(len(smw_true_counterexamples), len(smw_reported_counterexamples)),
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
