import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "showmewhy" / "scripts" / "verification_surface.py"
CASES = ROOT / "evals" / "reference_cases"

spec = importlib.util.spec_from_file_location("verification_surface", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class VerificationSurfaceTests(unittest.TestCase):
    def test_reference_cases(self):
        files = sorted(p for p in CASES.glob("*.json"))
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            with self.subTest(case=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                report = module.analyse(payload["manifest"])
                expected = payload["expected"]
                self.assertEqual(report["status"], expected["status"])
                self.assertEqual(report["do_next"]["claim_id"], expected["next_claim"])
                self.assertEqual(
                    [c["id"] for c in report["unresolved"]],
                    expected["unresolved"],
                )

    def test_refuting_witness_overrides_support(self):
        claim = {
            "id": "C1",
            "text": "All users require MFA",
            "obligation": "Find policy support and search for exceptions",
            "risk": "high",
            "required_witnesses": ["source", "counterexample"],
            "witnesses": [
                {"kind": "source", "source": "policy:4.2", "outcome": "supports"},
                {"kind": "counterexample", "source": "policy:7.1 legacy admin", "outcome": "refutes"},
            ],
            "next_action": "Resolve the legacy-admin exception.",
        }
        self.assertEqual(module.assess_claim(claim)["state"], "refuted")

    def test_missing_required_witness_keeps_claim_open(self):
        claim = {
            "id": "C1",
            "text": "Migration is backwards compatible",
            "obligation": "Exercise current and legacy clients",
            "risk": "high",
            "required_witnesses": ["execution", "regression"],
            "witnesses": [
                {"kind": "execution", "source": "new-client fixture", "outcome": "supports"}
            ],
            "next_action": "Run the legacy-client fixture.",
        }
        assessed = module.assess_claim(claim)
        self.assertEqual(assessed["state"], "open")
        self.assertEqual(assessed["missing_witnesses"], ["regression"])

    def test_default_surface_shows_only_three_unresolved_items(self):
        claims = []
        for i in range(497):
            claims.append({
                "id": f"V{i}",
                "text": f"verified claim {i}",
                "obligation": "source confirms claim",
                "risk": "low",
                "required_witnesses": ["source"],
                "witnesses": [{"kind": "source", "source": f"fixture:{i}", "outcome": "supports"}],
                "next_action": "No action.",
            })
        for i in range(3):
            claims.append({
                "id": f"O{i}",
                "text": f"open claim {i}",
                "obligation": "boundary must be exercised",
                "risk": "high" if i == 0 else "medium",
                "required_witnesses": ["boundary"],
                "witnesses": [],
                "unresolved_reason": "No boundary witness exists.",
                "next_action": f"Exercise boundary {i}.",
            })
        report = module.analyse({"result": "Large change is mostly verified.", "claims": claims})
        rendered = module.render_default(report)
        self.assertIn("497 verified · 3 need you", rendered)
        self.assertIn("open claim 0", rendered)
        self.assertNotIn("verified claim 0", rendered)
        self.assertLess(len(rendered), 900)

    def test_more_than_three_open_items_are_collapsed(self):
        claims = []
        for i in range(7):
            claims.append({
                "id": f"O{i}",
                "text": f"gap {i}",
                "obligation": "source required",
                "risk": "medium",
                "required_witnesses": ["source"],
                "witnesses": [],
                "unresolved_reason": "No source witness.",
                "next_action": f"Verify gap {i}.",
            })
        report = module.analyse({"result": "Seven material gaps remain.", "claims": claims})
        rendered = module.render_default(report)
        self.assertIn("+4 more · use why mode", rendered)
        self.assertNotIn("gap 3", rendered)

    def test_verified_surface_has_no_needs_you(self):
        manifest = {
            "result": "The measured claim is supported.",
            "claims": [{
                "id": "C1",
                "text": "Latency fell from 120ms to 90ms",
                "obligation": "measure before and after",
                "risk": "low",
                "required_witnesses": ["measurement"],
                "witnesses": [{"kind": "measurement", "source": "benchmark.csv rows 2-3", "outcome": "supports"}],
                "next_action": "No action required.",
            }],
        }
        rendered = module.render_default(module.analyse(manifest))
        self.assertIn("VERIFIED", rendered)
        self.assertNotIn("NEEDS YOU", rendered)

    def test_agent_assertion_is_not_a_supported_witness_kind(self):
        manifest = {
            "result": "Claim",
            "claims": [{
                "id": "C1",
                "text": "Tests pass",
                "obligation": "rerun tests",
                "risk": "medium",
                "required_witnesses": ["execution"],
                "witnesses": [{"kind": "agent_assertion", "source": "agent said done", "outcome": "supports"}],
                "next_action": "Run tests.",
            }],
        }
        with self.assertRaises(module.VerificationError):
            module.analyse(manifest)


    def test_manifest_requires_all_schema_required_claim_fields(self):
        manifest = {
            "result": "Claim",
            "claims": [{
                "id": "C1",
                "text": "Tests pass",
                "obligation": "rerun tests",
                "required_witnesses": ["execution"],
                "witnesses": [],
                "next_action": "Run tests.",
            }],
        }
        with self.assertRaisesRegex(module.VerificationError, "missing required field"):
            module.analyse(manifest)

    def test_manifest_rejects_duplicate_required_witness_kinds(self):
        manifest = {
            "result": "Claim",
            "claims": [{
                "id": "C1",
                "text": "Migration is safe",
                "obligation": "exercise boundary",
                "risk": "high",
                "required_witnesses": ["boundary", "boundary"],
                "witnesses": [],
                "next_action": "Exercise boundary.",
            }],
        }
        with self.assertRaisesRegex(module.VerificationError, "unique witness kinds"):
            module.analyse(manifest)

    def test_manifest_rejects_fields_outside_canonical_schema(self):
        manifest = {
            "result": "Claim",
            "claims": [{
                "id": "C1",
                "text": "Tests pass",
                "obligation": "rerun tests",
                "risk": "medium",
                "required_witnesses": ["execution"],
                "witnesses": [{
                    "kind": "execution",
                    "source": "pytest",
                    "outcome": "supports",
                    "confidence": "high",
                }],
                "next_action": "No action.",
            }],
        }
        with self.assertRaisesRegex(module.VerificationError, "unsupported field"):
            module.analyse(manifest)

    def test_manifest_rejects_non_boolean_control_fields(self):
        manifest = {
            "result": "Claim",
            "claims": [{
                "id": "C1",
                "text": "Tests pass",
                "obligation": "rerun tests",
                "risk": "medium",
                "material": "yes",
                "required_witnesses": ["execution"],
                "witnesses": [],
                "next_action": "Run tests.",
            }],
        }
        with self.assertRaisesRegex(module.VerificationError, "material must be a boolean"):
            module.analyse(manifest)

    def test_refuted_surface_uses_observable_refuting_witness_not_freeform_reason(self):
        manifest = {
            "result": "The universal claim is false.",
            "claims": [{
                "id": "C1",
                "text": "All users require MFA",
                "obligation": "search for exceptions",
                "risk": "high",
                "required_witnesses": ["source", "counterexample"],
                "witnesses": [
                    {"kind": "source", "source": "policy:4.2", "outcome": "supports"},
                    {"kind": "counterexample", "source": "policy:7.1 legacy bypass", "outcome": "refutes"},
                ],
                "unresolved_reason": "Agent-provided prose must not hide the refuting witness.",
                "next_action": "Resolve the exception.",
            }],
        }
        rendered = module.render_default(module.analyse(manifest))
        self.assertIn("Refuted by policy:7.1 legacy bypass.", rendered)
        self.assertNotIn("Agent-provided prose must not hide", rendered)


if __name__ == "__main__":
    unittest.main()
