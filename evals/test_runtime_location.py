import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from showmewhy_runtime.common import project_root, runtime_root, state_home


class RuntimeLocationTests(unittest.TestCase):
    def test_explicit_home_override_is_respected(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                self.assertEqual(state_home(), Path(state_td).resolve())
                root = runtime_root(project_td)
                self.assertTrue(root.is_relative_to(Path(state_td).resolve()))
                self.assertFalse((Path(project_td) / ".showmewhy").exists())

    def test_git_root_is_project_boundary_for_subdirectories(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            project = Path(project_td)
            (project / ".git").mkdir()
            nested = project / "src" / "service"
            nested.mkdir(parents=True)
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                self.assertEqual(project_root(nested), project.resolve())
                self.assertEqual(runtime_root(project), runtime_root(nested))

    def test_git_worktree_file_is_project_boundary(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            project = Path(project_td)
            (project / ".git").write_text("gitdir: /tmp/example\n", encoding="utf-8")
            nested = project / "packages" / "api"
            nested.mkdir(parents=True)
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                self.assertEqual(project_root(nested), project.resolve())
                self.assertEqual(runtime_root(project), runtime_root(nested))

    def test_different_projects_are_isolated(self):
        with tempfile.TemporaryDirectory() as first_td, tempfile.TemporaryDirectory() as second_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                first = runtime_root(first_td)
                second = runtime_root(second_td)
                self.assertNotEqual(first, second)
                self.assertEqual(first.parent, second.parent)

    def test_project_namespace_is_stable(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                self.assertEqual(runtime_root(project_td), runtime_root(project_td))


if __name__ == "__main__":
    unittest.main()
