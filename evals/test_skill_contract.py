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
        self.assertIn("perform the necessary investigation first", self.skill)

    def test_default_budget_is_300(self):
        self.assertIn("300-token soft budget", self.skill)

    def test_chain_of_thought_is_not_claimed(self):
        self.assertIn("private chain-of-thought", self.skill)
        self.assertIn("must never be presented as the model's hidden reasoning trace", self.skill)

    def test_causal_safety_is_explicit(self):
        self.assertIn("`CAUSED_BY` is a high bar", self.skill)
        self.assertIn("allowed a defect to pass undetected", self.skill)

    def test_quantified_claims_require_coverage(self):
        self.assertIn("Every material quantified claim must be covered by observable evidence", self.skill)

    def test_monitor_contract_is_present(self):
        for field in ("Evidence", "Guard", "Risk", "Budget"):
            self.assertIn(field, self.skill)

    def test_version_file_is_semver(self):
        self.assertRegex(VERSION.read_text(encoding="utf-8").strip(), r"^\d+\.\d+\.\d+$")

    def test_skill_internal_references_are_portable(self):
        self.assertIn("references/showmewhy-receipt.schema.json", self.skill)
        self.assertNotIn("standalone/showmewhy/references/showmewhy-receipt.schema.json", self.skill)

    def test_readme_is_version_agnostic(self):
        self.assertNotRegex(self.readme, r"(?m)^##\s+V\d+")
        self.assertIn("Release history belongs in", self.readme)


if __name__ == "__main__":
    unittest.main()
