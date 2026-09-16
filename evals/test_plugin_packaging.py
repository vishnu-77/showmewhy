import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_SKILL = ROOT / "skills" / "showmewhy" / "SKILL.md"
STANDALONE = ROOT / "standalone"
VERSION = ROOT / "VERSION"
HOOKS = ROOT / "hooks" / "hooks.json"


class PluginPackagingTests(unittest.TestCase):
    def test_plugin_manifest_is_valid(self):
        data = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "showmewhy")
        self.assertEqual(data["license"], "MIT")

    def test_skill_and_runtime_ship_atomically_in_plugin(self):
        self.assertTrue(PLUGIN_SKILL.exists(), "ShowMeWhy Skill must ship inside the marketplace plugin")
        self.assertFalse(STANDALONE.exists(), "there must be no second standalone Skill source of truth")

    def test_marketplace_uses_plugin_manifest_as_source_of_truth(self):
        data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "showmewhy")
        self.assertEqual(plugin["source"], "./")
        self.assertTrue(plugin["strict"])
        for component_key in ("skills", "hooks", "commands", "agents", "mcpServers"):
            self.assertNotIn(component_key, plugin)

    def test_plugin_uses_git_sha_for_update_detection(self):
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertNotIn("version", plugin, "plugin.json version would pin updates until a manual version bump")
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        expected = VERSION.read_text(encoding="utf-8").strip()
        self.assertEqual(marketplace["metadata"]["version"], expected)

    def test_standard_hook_file_is_auto_discoverable(self):
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertNotIn("hooks", plugin)
        self.assertTrue(HOOKS.exists())
        json.loads(HOOKS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
