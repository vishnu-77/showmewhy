import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from showmewhy_runtime.common import runtime_root
from showmewhy_runtime.compressors import compress_text, replace_response_text
from showmewhy_runtime.evidence import EvidenceStore
from showmewhy_runtime.hook import process_event


class V2RuntimeTests(unittest.TestCase):
    def _pytest_log(self):
        noise = "\n".join(f"diagnostic line {i}: verbose context that is not material" for i in range(220))
        return noise + "\nFAILED tests/test_auth.py::test_expired_session - AssertionError: expected 401 got 200\n= 1 failed, 127 passed in 3.4s =\n"

    def test_pytest_compression_is_material(self):
        raw = self._pytest_log()
        result = compress_text(raw, target_tokens=300)
        self.assertEqual(result.kind, "test")
        self.assertEqual(result.status, "failed")
        self.assertIn("1 failed, 127 passed", result.text)
        self.assertIn("test_expired_session", result.text)
        self.assertLess(len(result.text), len(raw) * 0.5)

    def test_bash_shape_is_preserved(self):
        response = {"stdout": "old", "stderr": "important stderr", "interrupted": False, "isImage": False}
        out = replace_response_text("Bash", response, "compact")
        self.assertEqual(out["stdout"], "compact")
        self.assertEqual(out["stderr"], "important stderr")
        self.assertEqual(set(out), set(response))

    def test_unknown_shape_fails_open(self):
        self.assertIsNone(replace_response_text("Read", {"content": "old"}, "compact"))

    def test_evidence_is_written_before_replacement_without_repo_pollution(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {"cwd": project_td, "session_id": "s1", "tool_use_id": "t1", "tool_name": "Bash", "tool_input": {"command": "pytest -q"}, "tool_response": {"stdout": self._pytest_log(), "stderr": "", "interrupted": False, "isImage": False}}
                output, digest = process_event(event, target_tokens=300)
                self.assertIn("updatedToolOutput", output["hookSpecificOutput"])
                self.assertGreater(digest["tokens_avoided"], 0)
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertIn("test_expired_session", stored["tool_response"]["stdout"])
                self.assertTrue((runtime_root(project_td) / "runs" / f"{digest['run_id']}.json").exists())
                self.assertFalse((Path(project_td) / ".showmewhy").exists())
                self.assertTrue(runtime_root(project_td).is_relative_to(Path(state_td).resolve()))

    def test_shadow_mode_never_replaces(self):
        with tempfile.TemporaryDirectory() as td:
            event = {"cwd": td, "tool_name": "Bash", "tool_input": {}, "tool_response": {"stdout": self._pytest_log(), "stderr": "", "interrupted": False, "isImage": False}}
            output, digest = process_event(event, mode="shadow", target_tokens=300)
            self.assertEqual(output, {})
            self.assertIsNotNone(digest)

    def test_short_output_passes_through(self):
        event = {"tool_name": "Bash", "tool_response": {"stdout": "ok", "stderr": ""}}
        output, digest = process_event(event, target_tokens=300)
        self.assertEqual(output, {})
        self.assertIsNone(digest)


if __name__ == "__main__":
    unittest.main()
