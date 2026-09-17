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

    def test_incomplete_generic_digest_never_replaces_visible_output(self):
        lines = [f"pipeline detail {i}: ordinary output" for i in range(120)]
        hidden = "DO NOT DEPLOY: rollback path is unavailable"
        lines.insert(60, hidden)
        raw = "\n".join(lines)

        compressed = compress_text(raw, target_tokens=40)
        self.assertFalse(compressed.complete)
        self.assertNotIn(hidden, compressed.text)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {"cwd": project_td, "session_id": "s-generic", "tool_use_id": "t-generic", "tool_name": "Bash", "tool_input": {"command": "deploy"}, "tool_response": {"stdout": raw, "stderr": "", "interrupted": False, "isImage": False}}
                output, digest = process_event(event, mode="replace", target_tokens=40)

                self.assertEqual(output, {})
                self.assertIsNotNone(digest)
                self.assertFalse(digest["parser"]["complete"])
                self.assertTrue(any("original tool output was preserved" in caveat for caveat in digest["caveats"]))
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertIn(hidden, stored["tool_response"]["stdout"])

    def test_truncated_typescript_digest_never_replaces_visible_output(self):
        raw = "\n".join(
            f"src/file{i}.ts({i + 1},1): error TS2322: synthetic type failure {i}"
            for i in range(24)
        )
        compressed = compress_text(raw, target_tokens=20)
        self.assertEqual(compressed.parser, "tsc")
        self.assertFalse(compressed.complete)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {"cwd": project_td, "tool_name": "Bash", "tool_input": {"command": "tsc --noEmit"}, "tool_response": {"stdout": raw, "stderr": "", "interrupted": False, "isImage": False}}
                output, digest = process_event(event, mode="replace", target_tokens=20)
                self.assertEqual(output, {})
                self.assertEqual(digest["parser"]["name"], "tsc")
                self.assertFalse(digest["parser"]["complete"])

    def test_truncated_lint_digest_never_replaces_visible_output(self):
        raw = "\n".join(
            f"src/file{i}.py:{i + 1}:1: error synthetic lint failure {i}"
            for i in range(25)
        )
        compressed = compress_text(raw, target_tokens=20)
        self.assertEqual(compressed.parser, "lint")
        self.assertFalse(compressed.complete)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {"cwd": project_td, "tool_name": "Bash", "tool_input": {"command": "lint"}, "tool_response": {"stdout": raw, "stderr": "", "interrupted": False, "isImage": False}}
                output, digest = process_event(event, mode="replace", target_tokens=20)
                self.assertEqual(output, {})
                self.assertEqual(digest["parser"]["name"], "lint")
                self.assertFalse(digest["parser"]["complete"])

    def test_incomplete_mixed_stdout_stderr_never_replaces(self):
        stdout = "\n".join(f"build output {i}: continuing" for i in range(100))
        stderr = "rollback path unavailable; inspect deployment state"
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {"cwd": project_td, "tool_name": "Bash", "tool_input": {"command": "build && deploy"}, "tool_response": {"stdout": stdout, "stderr": stderr, "interrupted": False, "isImage": False}}
                output, digest = process_event(event, mode="replace", target_tokens=40)
                self.assertEqual(output, {})
                self.assertFalse(digest["parser"]["complete"])
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertEqual(stored["tool_response"]["stderr"], stderr)

    def test_pipeline_failure_outside_digest_window_never_replaces(self):
        lines = [f"stage detail {i}: normal" for i in range(160)]
        hidden_failure = "deploy-step exited with status 17"
        lines[80] = hidden_failure
        raw = "\n".join(lines)
        compressed = compress_text(raw, target_tokens=40)
        self.assertFalse(compressed.complete)
        self.assertNotIn(hidden_failure, compressed.text)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {"cwd": project_td, "tool_name": "Bash", "tool_input": {"command": "pipeline"}, "tool_response": {"stdout": raw, "stderr": "", "interrupted": False, "isImage": False}}
                output, digest = process_event(event, mode="replace", target_tokens=40)
                self.assertEqual(output, {})
                self.assertFalse(digest["parser"]["complete"])
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertIn(hidden_failure, stored["tool_response"]["stdout"])

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
