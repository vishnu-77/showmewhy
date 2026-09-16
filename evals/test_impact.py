import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).parents[1] / "standalone" / "showmewhy" / "scripts" / "impact.py"
spec = importlib.util.spec_from_file_location("impact", SCRIPT)
impact = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(impact)


class ImpactTests(unittest.TestCase):
    def test_reference_profile_math(self):
        result = impact.calculate(1000, 250, budget=300)
        self.assertEqual(result["reduced_tokens"], 750)
        self.assertEqual(result["reduction_pct"], 75.0)
        self.assertTrue(result["within_budget"])
        self.assertFalse(result["realised_avoidance_claim"])
        self.assertAlmostEqual(result["estimated_energy_equivalent_wh"], 0.999, places=6)
        self.assertAlmostEqual(result["estimated_operational_co2e_equivalent_g"], 0.3996, places=6)

    def test_hook_basis_changes_claim_label(self):
        result = impact.calculate(1000, 250, basis="hook")
        self.assertTrue(result["realised_avoidance_claim"])
        self.assertIn("estimated_operational_co2e_avoided_g", result)
        self.assertNotIn("estimated_operational_co2e_equivalent_g", result)

    def test_no_negative_reduction(self):
        result = impact.calculate(100, 200)
        self.assertEqual(result["reduced_tokens"], 0)
        self.assertEqual(result["estimated_operational_co2e_equivalent_g"], 0)

    def test_zero_source(self):
        result = impact.calculate(0, 0)
        self.assertEqual(result["reduction_pct"], 0)

    def test_fallback_token_estimator(self):
        self.assertEqual(impact.estimate_tokens("abcdefgh"), 2)


if __name__ == "__main__":
    unittest.main()
