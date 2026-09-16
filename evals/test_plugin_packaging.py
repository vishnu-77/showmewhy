import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SKILL = ROOT / "skills" / "showmewhy" / "SKILL.md"
VERSION = ROOT / "VERSION"
HOOKS = ROOT / "hooks" / "hooks.json"


class PluginPackagingTests(unittest.TestCase):
    def test_plugin_manifest_is_valid(self):
        data = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "showmewhy")
        self.assertEqual(data["license"], "MIT")
        self.assertTrue(SKILL.exists())

    def test_marketplace_uses_plugin_manifest_as_source_of_truth(self):
        data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "showmewhy")
        self.assertEqual(plugin["source"], "./")
        self.assertTrue(plugin["strict"])
        for component_key in ("skills", "hooks", "commands", "agents", "mcpServers"):
            self.assertNotIn(component_key, plugin)

    def test_versions_are_aligned(self):
        expected = VERSION.read_text(encoding="utf-8").strip()
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], expected)
        self.assertEqual(marketplace["metadata"]["version"], expected)

    def test_hook_path_exists_when_declared(self):
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        hook_path = plugin.get("hooks")
        if hook_path:
            self.assertTrue(hook_path.startswith("./"))
            self.assertTrue((ROOT / hook_path[2:]).exists())
            json.loads(HOOKS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
