import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_VISUALS = {"text","table","bars","tree","timeline","graph","none"}
REQUIRED_CATEGORIES = {"debugging","architecture","security","research","comparison","planning","code_review","ci_build","simple"}

class BenchmarkIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "evals" / "benchmark_cases.py"
        spec = importlib.util.spec_from_file_location("benchmark_cases", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.cases = module.CASES

    def test_release_gate_has_at_least_100_cases(self):
        self.assertGreaterEqual(len(self.cases), 100)

    def test_ids_are_unique(self):
        ids = [c["id"] for c in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_required_categories_present(self):
        self.assertTrue(REQUIRED_CATEGORIES.issubset({c["category"] for c in self.cases}))

    def test_visual_types_are_known(self):
        self.assertTrue(all(c["expect"]["visual_type"] in ALLOWED_VISUALS for c in self.cases))

    def test_token_budgets_are_bounded(self):
        self.assertTrue(all(100 <= c["expect"]["max_tokens"] <= 700 for c in self.cases))

if __name__ == "__main__":
    unittest.main()
