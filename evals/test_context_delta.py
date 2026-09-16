import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "showmewhy" / "scripts" / "context_delta.py"
CASES = ROOT / "evals" / "context_delta_cases.json"

spec = importlib.util.spec_from_file_location("context_delta", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ContextDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES.read_text(encoding="utf-8"))

    def test_cross_domain_reference_cases(self):
        self.assertGreaterEqual(len(self.cases), 4)
        for case in self.cases:
            with self.subTest(case=case["name"]):
                report = module.analyse_delta(case["manifest"])
                expected = case["expected"]
                self.assertEqual(report["status"], expected["status"])
                self.assertEqual(
                    [a["id"] for a in report["broken_assumptions"]],
                    expected["broken_assumptions"],
                )
                transition = next(t for t in report["transitions"] if t["claim_id"] == expected["transition"][0])
                self.assertEqual(
                    [transition["claim_id"], transition["from"], transition["to"]],
                    expected["transition"],
                )
                self.assertEqual(report["do_next"]["claim_id"], expected["next_claim"])

    def test_network_case_exposes_context_gap_without_retrospective_story(self):
        case = next(c for c in self.cases if c["name"] == "network-policy-cross-repo-blocker")
        report = module.analyse_delta(case["manifest"])
        rendered = module.render_delta(report)
        self.assertIn("SHOWMEWHY · DELTA", rendered)
        self.assertIn("BROKEN ASSUMPTION", rendered)
        self.assertIn("PI-906", rendered)
        self.assertIn("hl2-saas-helm", rendered)
        self.assertIn("shared-chart release history", rendered)
        self.assertNotIn("I wrote", rendered)
        self.assertNotIn("you pushed", rendered)
        self.assertLess(len(rendered), 1400)

    def test_new_evidence_is_detected_from_current_claim_witnesses(self):
        case = next(c for c in self.cases if c["name"] == "contract-schedule-conflict")
        report = module.analyse_delta(case["manifest"])
        sources = {e["source"] for e in report["new_evidence"]}
        self.assertIn("Schedule B: 30 days", sources)

    def test_resolved_transition_is_not_mislabeled_as_regression(self):
        manifest = {
            "previous": {
                "result": "Compatibility remains unverified.",
                "claims": [{
                    "id": "C1",
                    "text": "Legacy clients remain compatible",
                    "obligation": "Run legacy-client regression",
                    "risk": "high",
                    "required_witnesses": ["regression"],
                    "witnesses": [],
                    "next_action": "Run the legacy-client fixture."
                }]
            },
            "current": {
                "result": "Legacy-client compatibility is now verified.",
                "claims": [{
                    "id": "C1",
                    "text": "Legacy clients remain compatible",
                    "obligation": "Run legacy-client regression",
                    "risk": "high",
                    "required_witnesses": ["regression"],
                    "witnesses": [{
                        "kind": "regression",
                        "source": "legacy-client fixture -> pass",
                        "outcome": "supports"
                    }],
                    "next_action": "No action required."
                }]
            }
        }
        report = module.analyse_delta(manifest)
        self.assertEqual(report["status"], "resolved")
        self.assertEqual(report["transitions"][0]["change"], "resolved")
        self.assertIn("RESOLVED", module.render_delta(report))

    def test_unchanged_state_stays_unchanged(self):
        claim = {
            "id": "C1",
            "text": "Measured latency fell",
            "obligation": "Compare equivalent measurements",
            "risk": "low",
            "required_witnesses": ["measurement"],
            "witnesses": [{
                "kind": "measurement",
                "source": "benchmark.csv",
                "outcome": "supports"
            }],
            "next_action": "No action required."
        }
        report = module.analyse_delta({
            "previous": {"result": "Latency fell.", "claims": [claim]},
            "current": {"result": "Latency fell.", "claims": [claim]},
        })
        self.assertEqual(report["status"], "unchanged")
        self.assertEqual(report["transitions"], [])
        self.assertIn("UNCHANGED", module.render_delta(report))

    def test_invalid_assumption_witness_wins(self):
        case = next(c for c in self.cases if c["name"] == "policy-mfa-exception")
        report = module.analyse_delta(case["manifest"])
        self.assertEqual(report["broken_assumptions"][0]["state"], "invalidated")
        self.assertTrue(report["broken_assumptions"][0]["refuting_witnesses"])


if __name__ == "__main__":
    unittest.main()
