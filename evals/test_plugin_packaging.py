import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SKILL = ROOT / "skills" / "showmewhy" / "SKILL.md"
VERSION = ROOT / "VERSION"


class PluginPackagingTests(unittest.TestCase):
    def test_plugin_manifest_is_valid(self):
        data = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "showmewhy")
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(data["version"], "1.0.1")

    def test_marketplace_points_to_real_skill(self):
        data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "showmewhy")
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "showmewhy")
        self.assertEqual(plugin["source"], "./")
        self.assertFalse(plugin["strict"])
        self.assertIn("./skills/showmewhy", plugin["skills"])
        self.assertTrue(SKILL.exists())

    def test_versions_are_aligned(self):
        expected = "1.0.1"
        self.assertEqual(VERSION.read_text(encoding="utf-8").strip(), expected)
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], expected)
        self.assertEqual(marketplace["metadata"]["version"], expected)


if __name__ == "__main__":
    unittest.main()
