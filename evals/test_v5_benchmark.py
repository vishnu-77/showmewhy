import json
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
        self.assertEqual(score.material_failures, 2)
        self.assertEqual(score.detected_material_failures, 2)
        self.assertEqual(score.missed_material_failures, 0)
        self.assertEqual(score.material_failure_recall, 1.0)
        self.assertEqual(score.material_failure_miss_rate, 0.0)
        self.assertEqual(score.false_closures, 0)
        self.assertAlmostEqual(score.verification_surface_reduction, 5 / 7)

    def test_smoke_fixture_secondary_metrics(self):
        score = score_records(self.records)
        self.assertEqual(score.verification_surface_precision, 1.0)
        self.assertEqual(score.verification_surface_recall, 1.0)
        self.assertEqual(score.counterexample_recall, 1.0)
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

    def test_default_surface_must_equal_open_claims(self):
        rows = deepcopy(self.records)
        rows[0]["showmewhy"]["surfaced_claim_ids"] = []
        with self.assertRaisesRegex(BenchmarkValidationError, "surfaced_claim_ids"):
            score_records(rows)

    def test_detected_failures_cannot_invent_ground_truth_failures(self):
        rows = deepcopy(self.records)
        rows[0]["showmewhy"]["detected_failure_ids"].append("c1")
        with self.assertRaisesRegex(BenchmarkValidationError, "detected_failure_ids"):
            score_records(rows)

    def test_fixture_is_explicitly_non_claim_bearing(self):
        readme = (V5 / "README.md").read_text(encoding="utf-8")
        self.assertIn("not", readme.lower())
        self.assertIn("evidence of product effectiveness", readme)


if __name__ == "__main__":
    unittest.main()
