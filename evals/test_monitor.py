import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "standalone" / "showmewhy" / "scripts" / "monitor.py"
spec = importlib.util.spec_from_file_location("showmewhy_monitor", MODULE_PATH)
monitor = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def test_rewarded_low(self):
        r = monitor.assess(True, True, "low")
        self.assertEqual((r["budget_min"], r["budget_max"], r["recommended_next_tokens"]), (1200, 2000, 2000))

    def test_rewarded_medium(self):
        r = monitor.assess(True, True, "medium")
        self.assertEqual(r["recommended_next_tokens"], 1600)

    def test_rewarded_high(self):
        r = monitor.assess(True, True, "high")
        self.assertEqual(r["recommended_next_tokens"], 1200)

    def test_missing_guard_constrains(self):
        r = monitor.assess(True, False, "medium")
        self.assertEqual((r["state"], r["budget_min"], r["budget_max"], r["recommended_next_tokens"]), ("CONSTRAINED", 800, 1800, 1300))

    def test_unverified_high_is_minimum(self):
        r = monitor.assess(False, True, "high")
        self.assertEqual(r["recommended_next_tokens"], 800)


if __name__ == "__main__":
    unittest.main()
