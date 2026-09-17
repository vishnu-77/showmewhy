import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "evals" / "v5"
sys.path.insert(0, str(V5))

from scorer import BenchmarkValidationError, load_records, score_records


class V5BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_path = V5 / "fixtures" / "smoke.json"
        cls.records = load_records(cls.fixture_path)

    def test_smoke_fixture_primary_metrics(self):
        score = score_records(self.records)
        self.assertEqual(score.tasks, 2)
        self.assertEqual(score.material_claims, 7)
        self.assertEqual(score.claim_classification_coverage, 1.0)
        self.assertEqual(score.material_failures, 2)
        self.assertEqual(score.baseline_detected_material_failures, 1)
        self.assertEqual(score.baseline_material_failure_recall, 0.5)
        self.assertEqual(score.detected_material_failures, 2)
        self.assertEqual(score.missed_material_failures, 0)
        self.assertEqual(score.material_failure_recall, 1.0)
        self.assertEqual(score.material_failure_recall_delta, 0.5)
        self.assertEqual(score.material_failure_miss_rate, 0.0)
        self.assertEqual(score.false_closures, 0)
        self.assertAlmostEqual(score.verification_surface_reduction, 5 / 7)

    def test_smoke_fixture_secondary_metrics(self):
        score = score_records(self.records)
        self.assertEqual(score.baseline_material_failure_precision, 1.0)
        self.assertEqual(score.material_failure_precision, 1.0)
        self.assertEqual(score.verification_surface_precision, 1.0)
        self.assertEqual(score.verification_surface_recall, 1.0)
        self.assertEqual(score.baseline_counterexample_recall, 0.5)
        self.assertEqual(score.counterexample_recall, 1.0)
        self.assertEqual(score.counterexample_precision, 1.0)
        self.assertAlmostEqual(score.inspection_token_reduction, 1 - (480 / 1400))
        self.assertAlmostEqual(score.inspection_line_reduction, 1 - (72 / 210))
        self.assertAlmostEqual(score.verification_time_reduction, 1 - (165 / 420))

    def test_false_closure_is_counted_not_hidden_by_high_recall(self):
        rows = deepcopy(self.records)
        first = rows[0]
        first["showmewhy"]["verified_claim_ids"] = ["c1", "c2", "c4"]
        first["showmewhy"]["refuted_claim_ids"] = []
        score = score_records(rows)
        self.assertEqual(score.material_failure_recall, 1.0)
        self.assertEqual(score.false_closures, 1)
        self.assertAlmostEqual(score.false_closure_rate, 1 / 4)

    def test_false_failure_detection_reduces_precision_without_inflating_recall(self):
        rows = deepcopy(self.records)
        rows[0]["showmewhy"]["detected_failure_ids"].append("c1")
        score = score_records(rows)
        self.assertEqual(score.material_failure_recall, 1.0)
        self.assertEqual(score.false_failure_detections, 1)
        self.assertAlmostEqual(score.material_failure_precision, 2 / 3)

    def test_false_counterexample_detection_is_visible(self):
        rows = deepcopy(self.records)
        rows[0]["showmewhy"]["detected_counterexample_ids"].append("x-spurious")
        score = score_records(rows)
        self.assertEqual(score.counterexample_recall, 1.0)
        self.assertEqual(score.false_counterexample_detections, 1)
        self.assertAlmostEqual(score.counterexample_precision, 2 / 3)

    def test_default_surface_must_equal_open_claims(self):
        rows = deepcopy(self.records)
        rows[0]["showmewhy"]["surfaced_claim_ids"] = []
        with self.assertRaisesRegex(BenchmarkValidationError, "surfaced_claim_ids"):
            score_records(rows)

    def test_failure_detection_ids_must_still_reference_material_claims(self):
        rows = deepcopy(self.records)
        rows[0]["showmewhy"]["detected_failure_ids"].append("not-a-material-claim")
        with self.assertRaisesRegex(BenchmarkValidationError, "detected_failure_ids"):
            score_records(rows)

    def test_task_ids_must_be_unique(self):
        rows = deepcopy(self.records)
        rows[1]["task_id"] = rows[0]["task_id"]
        with self.assertRaisesRegex(BenchmarkValidationError, "task_id values must be unique"):
            score_records(rows)

    def test_pair_ids_must_be_unique(self):
        rows = deepcopy(self.records)
        rows[1]["pairing"]["pair_id"] = rows[0]["pairing"]["pair_id"]
        with self.assertRaisesRegex(BenchmarkValidationError, "pairing.pair_id values must be unique"):
            score_records(rows)

    def test_pairing_prompt_hash_must_be_sha256(self):
        rows = deepcopy(self.records)
        rows[0]["pairing"]["task_prompt_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(BenchmarkValidationError, "task_prompt_sha256"):
            score_records(rows)

    def test_ground_truth_must_be_blinded_to_showmewhy(self):
        rows = deepcopy(self.records)
        rows[0]["ground_truth"]["blinded_to_showmewhy"] = False
        with self.assertRaisesRegex(BenchmarkValidationError, "blinded_to_showmewhy"):
            score_records(rows)

    def test_ground_truth_requires_independent_oracle_reference(self):
        rows = deepcopy(self.records)
        rows[0]["ground_truth"]["oracle_refs"] = []
        with self.assertRaisesRegex(BenchmarkValidationError, "oracle_refs"):
            score_records(rows)

    def test_fixture_is_explicitly_non_claim_bearing(self):
        readme = (V5 / "README.md").read_text(encoding="utf-8")
        self.assertIn("evidence of product effectiveness", readme)


if __name__ == "__main__":
    unittest.main()
