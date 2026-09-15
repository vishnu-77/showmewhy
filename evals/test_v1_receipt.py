import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "skills" / "showmewhy" / "scripts" / "validate_receipt.py"

spec = importlib.util.spec_from_file_location("receipt_validator", VALIDATOR)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReceiptV1Tests(unittest.TestCase):
    def test_schema_is_v1(self):
        schema = json.loads((ROOT / "skills" / "showmewhy" / "references" / "showmewhy-receipt.schema.json").read_text())
        self.assertEqual(schema["title"], "ShowMeWhy Receipt V1")
        self.assertIn("monitor", schema["required"])
        self.assertIn("impact", schema["required"])

    def test_example_receipt_validates(self):
        receipt = json.loads((ROOT / "examples" / "receipt.json").read_text())
        self.assertEqual(module.validate(receipt), [])

    def test_unknown_edge_is_rejected(self):
        receipt = json.loads((ROOT / "examples" / "receipt.json").read_text())
        receipt["why"]["edges"][0]["relation"] = "proves"
        self.assertIn("invalid edge relation", module.validate(receipt))

    def test_monitor_budget_bounds(self):
        receipt = json.loads((ROOT / "examples" / "receipt.json").read_text())
        receipt["monitor"]["next_budget_tokens"] = 2500
        self.assertIn("monitor.next_budget_tokens must be 800..2000", module.validate(receipt))

if __name__ == "__main__":
    unittest.main()
