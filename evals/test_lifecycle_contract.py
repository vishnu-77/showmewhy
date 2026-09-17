from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LifecycleContractTests(unittest.TestCase):
    def test_release_metadata_is_aligned(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["metadata"]["version"], version)

        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertRegex(changelog, rf"(?m)^##\s+{re.escape(version)}(?:\s|$)")

    def test_skill_exposes_status_and_native_update_modes(self) -> None:
        skill = (ROOT / "skills" / "showmewhy" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`status`: inspect the installed ShowMeWhy/Claude plugin state", skill)
        self.assertIn("`update`: update ShowMeWhy through Claude Code's native plugin updater", skill)
        self.assertIn("claude plugin update showmewhy@showmewhy --scope user", skill)
        self.assertIn("/reload-plugins", skill)
        self.assertIn("`status` and `update` are lifecycle modes, not stages", skill)

    def test_public_docs_use_bare_showmewhy(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install_sh = (ROOT / "install.sh").read_text(encoding="utf-8")
        install_ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")

        self.assertIn("/showmewhy status", readme)
        self.assertIn("/showmewhy update", readme)
        self.assertNotIn("/showmewhy:showmewhy", readme)
        self.assertIn("command  /showmewhy", install_sh)
        self.assertIn("command  /showmewhy", install_ps1)

    def test_readme_documents_direct_marketplace_flow(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/plugin marketplace add vishnu-77/showmewhy", readme)
        self.assertIn("/plugin install showmewhy@showmewhy", readme)
        self.assertIn("claude plugin marketplace add vishnu-77/showmewhy", readme)
        self.assertIn("claude plugin install showmewhy@showmewhy", readme)

    def test_readme_does_not_reintroduce_project_local_state(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Runtime state is local under `.showmewhy/`", readme)
        self.assertIn("outside the consumer repository", readme)


if __name__ == "__main__":
    unittest.main()
