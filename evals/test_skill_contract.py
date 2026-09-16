from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "showmewhy" / "SKILL.md"
README = ROOT / "README.md"
VERSION = ROOT / "VERSION"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")

    def test_manual_invocation_is_explicit(self):
        self.assertIn("name: showmewhy", self.skill)
        self.assertIn("user-invocable: true", self.skill)
        self.assertIn("disable-model-invocation: true", self.skill)

    def test_fresh_questions_are_supported(self):
        self.assertIn("Do not refuse merely because no prior answer exists", self.skill)
        self.assertIn("answer or investigate it first", self.skill)

    def test_default_budget_is_compact(self):
        self.assertIn("220-token soft budget", self.skill)

    def test_default_surface_is_gap_first(self):
        for phrase in ("NEEDS YOU", "DO NEXT", "VERIFIED"):
            self.assertIn(phrase, self.skill)
        self.assertIn("at most **3** unresolved items", self.skill)
        self.assertIn("show only material `OPEN` or `REFUTED` claims", self.skill)

    def test_monitor_and_impact_are_not_default(self):
        self.assertIn("never include this automatically in ordinary runs", self.skill)
        self.assertIn("Do not print a provenance graph, arrow chain, MONITOR block", self.skill)
        self.assertIn("Only in `impact` mode", self.skill)

    def test_chain_of_thought_is_not_claimed(self):
        self.assertIn("private chain-of-thought", self.skill)
        self.assertIn("Do not expose private reasoning", self.skill)

    def test_witness_contract_is_present(self):
        for kind in ("execution", "source", "measurement", "invariant", "counterexample", "boundary", "regression", "comparison"):
            self.assertIn(f"`{kind}`", self.skill)
        self.assertIn("Agent assertions", self.skill)

    def test_three_closure_states_are_explicit(self):
        for state in ("`VERIFIED`", "`REFUTED`", "`OPEN`"):
            self.assertIn(state, self.skill)

    def test_causal_safety_is_explicit(self):
        self.assertIn("`CAUSED_BY` remains a high bar", self.skill)
        self.assertIn("allowed a defect to survive undetected", self.skill)

    def test_quantified_claims_require_coverage(self):
        self.assertIn("Every material quantified claim must be covered by observable evidence", self.skill)

    def test_verification_surface_schema_is_canonical(self):
        self.assertIn("references/verification-surface.schema.json", self.skill)
        self.assertIn("scripts/verification_surface.py", self.skill)

    def test_version_file_is_semver(self):
        self.assertRegex(VERSION.read_text(encoding="utf-8").strip(), r"^\d+\.\d+\.\d+$")

    def test_readme_is_version_agnostic(self):
        self.assertNotRegex(self.readme, r"(?m)^##\s+V\d+")
        self.assertIn("Release history belongs in", self.readme)

    def test_readme_leads_with_verification_wedge(self):
        self.assertIn("Review only what the AI couldn't prove", self.readme)
        self.assertIn("Most tools show you more", self.readme)
        self.assertIn("Works beyond code", self.readme)


if __name__ == "__main__":
    unittest.main()
