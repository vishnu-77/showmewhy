from pathlib import Path
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
        self.assertIn("user-invocable: true", self.skill)
        self.assertIn("disable-model-invocation: true", self.skill)
        self.assertIn("/showmewhy", self.readme)

    def test_default_budget_is_300(self):
        self.assertIn("300-token soft budget", self.skill)
        self.assertIn("/showmewhy` | 300 tokens", self.readme)

    def test_chain_of_thought_is_not_claimed(self):
        self.assertIn("not private chain-of-thought", self.readme)
        self.assertIn("must never be presented as the model's hidden reasoning trace", self.skill)

    def test_monitor_contract_is_present(self):
        for field in ("Evidence", "Guard", "Risk", "Budget"):
            self.assertIn(field, self.skill)
        self.assertIn("1,200–2,000 tokens", self.skill)
        self.assertIn("800–1,800 tokens", self.skill)

    def test_version_file(self):
        self.assertEqual(VERSION.read_text(encoding="utf-8").strip(), "1.0.0")

    def test_skill_internal_references_are_portable(self):
        self.assertIn("references/showmewhy-receipt.schema.json", self.skill)
        self.assertNotIn("skills/showmewhy/references/showmewhy-receipt.schema.json", self.skill)


if __name__ == "__main__":
    unittest.main()
