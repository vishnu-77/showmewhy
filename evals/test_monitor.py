import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "skills" / "showmewhy" / "scripts" / "monitor.py"
spec = importlib.util.spec_from_file_location("showmewhy_monitor", MODULE_PATH)
monitor = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def test_clean_session_is_low_risk(self):
        r = monitor.assess(verified=12, open_count=0, refuted=0, high_risk_open=0, next_action="")
        self.assertEqual(r["risk"], "LOW")
        self.assertEqual(r["next"], "No material verification gap found.")

    def test_open_claims_raise_session_risk(self):
        r = monitor.assess(verified=8, open_count=2, refuted=0, high_risk_open=0, next_action="Check rollback.")
        self.assertEqual(r["risk"], "MEDIUM")
        self.assertEqual(r["next"], "Check rollback.")

    def test_high_risk_open_claim_is_high(self):
        r = monitor.assess(verified=5, open_count=1, refuted=0, high_risk_open=1, next_action="Exercise legacy token.")
        self.assertEqual(r["risk"], "HIGH")

    def test_refuted_claim_keeps_monitor_actionable(self):
        r = monitor.assess(verified=5, open_count=0, refuted=1, high_risk_open=0, next_action="Correct the policy claim.")
        self.assertEqual(r["risk"], "MEDIUM")
        self.assertEqual(r["refuted"], 1)

    def test_monitor_has_no_token_reward_band(self):
        r = monitor.assess(verified=1, open_count=1, refuted=0, high_risk_open=0, next_action="Verify C2.")
        self.assertNotIn("state", r)
        self.assertNotIn("recommended_next_tokens", r)
        self.assertNotIn("budget_min", r)

    def test_invalid_high_risk_count_rejected(self):
        with self.assertRaises(ValueError):
            monitor.assess(verified=0, open_count=0, refuted=0, high_risk_open=1, next_action="")


if __name__ == "__main__":
    unittest.main()
