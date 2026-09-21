import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from showmewhy_runtime.common import runtime_root
from showmewhy_runtime.compressors import compress_text, replace_response_text, response_text
from showmewhy_runtime.evidence import EvidenceStore
from showmewhy_runtime.hook import process_event


class V2RuntimeTests(unittest.TestCase):
    def _pytest_log(self):
        noise = "\n".join(
            f"diagnostic line {i}: verbose context that is not material"
            for i in range(220)
        )
        return (
            noise
            + "\nFAILED tests/test_auth.py::test_expired_session - AssertionError: expected 401 got 200"
            + "\n= 1 failed, 127 passed in 3.4s =\n"
        )

    def _pytest_pass_log(self):
        noise = "\n".join("." * 120 for _ in range(40))
        return noise + "\n127 passed in 3.4s\n"

    def test_pytest_failure_digest_is_useful_but_not_complete(self):
        raw = self._pytest_log()
        result = compress_text(raw, target_tokens=300)
        self.assertEqual(result.kind, "test")
        self.assertEqual(result.status, "failed")
        self.assertIn("1 failed, 127 passed", result.text)
        self.assertIn("test_expired_session", result.text)
        self.assertLess(len(result.text), len(raw) * 0.5)
        self.assertFalse(result.complete)

    def test_bash_shape_is_preserved(self):
        response = {
            "stdout": "old",
            "stderr": "important stderr",
            "interrupted": False,
            "isImage": False,
        }
        out = replace_response_text("Bash", response, "compact")
        self.assertEqual(out["stdout"], "compact")
        self.assertEqual(out["stderr"], "important stderr")
        self.assertEqual(set(out), set(response))

    def test_response_parser_only_reads_replaceable_stdout(self):
        response = {
            "stdout": "127 passed in 3.4s",
            "stderr": "critical stderr remains independently visible",
        }
        self.assertEqual(response_text("Bash", response), response["stdout"])

    def test_unknown_shape_fails_open(self):
        self.assertIsNone(replace_response_text("Read", {"content": "old"}, "compact"))

    def test_evidence_is_written_before_safe_replacement_without_repo_pollution(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "session_id": "s1",
                    "tool_use_id": "t1",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest -q"},
                    "tool_response": {
                        "stdout": self._pytest_pass_log(),
                        "stderr": "",
                        "interrupted": False,
                        "isImage": False,
                    },
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=300,
                )
                self.assertIn("updatedToolOutput", output["hookSpecificOutput"])
                self.assertGreater(digest["tokens_avoided"], 0)
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertIn("127 passed", stored["tool_response"]["stdout"])
                self.assertTrue(
                    (runtime_root(project_td) / "runs" / f"{digest['run_id']}.json").exists()
                )
                self.assertFalse((Path(project_td) / ".showmewhy").exists())
                self.assertTrue(
                    runtime_root(project_td).is_relative_to(Path(state_td).resolve())
                )

    def test_failed_pytest_never_replaces_even_when_replace_is_requested(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest -q"},
                    "tool_response": {
                        "stdout": self._pytest_log(),
                        "stderr": "",
                    },
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=300,
                )
                self.assertEqual(output, {})
                self.assertFalse(digest["parser"]["complete"])
                self.assertEqual(digest["status"], "failed")

    def test_git_diff_digest_never_replaces_patch_content(self):
        body = "\n".join(
            [
                "diff --git a/app.py b/app.py",
                "index 1111111..2222222 100644",
                "--- a/app.py",
                "+++ b/app.py",
            ]
            + [f"+important semantic change {i}" for i in range(120)]
        )
        compressed = compress_text(body, target_tokens=30)
        self.assertEqual(compressed.parser, "git-diff")
        self.assertFalse(compressed.complete)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "git diff"},
                    "tool_response": {"stdout": body, "stderr": ""},
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=30,
                )
                self.assertEqual(output, {})
                self.assertFalse(digest["parser"]["complete"])

    def test_stderr_is_preserved_once_when_stdout_is_replaced(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest -q"},
                    "tool_response": {
                        "stdout": self._pytest_pass_log(),
                        "stderr": "warning emitted on stderr",
                    },
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=300,
                )
                updated = output["hookSpecificOutput"]["updatedToolOutput"]
                self.assertEqual(updated["stderr"], "warning emitted on stderr")
                self.assertNotIn("warning emitted on stderr", updated["stdout"])
                self.assertNotIn("warning emitted on stderr", digest["summary"])

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
                event = {
                    "cwd": project_td,
                    "session_id": "s-generic",
                    "tool_use_id": "t-generic",
                    "tool_name": "Bash",
                    "tool_input": {"command": "deploy"},
                    "tool_response": {
                        "stdout": raw,
                        "stderr": "",
                        "interrupted": False,
                        "isImage": False,
                    },
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=40,
                )

                self.assertEqual(output, {})
                self.assertIsNotNone(digest)
                self.assertFalse(digest["parser"]["complete"])
                self.assertTrue(
                    any(
                        "original tool output was preserved" in caveat
                        for caveat in digest["caveats"]
                    )
                )
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertIn(hidden, stored["tool_response"]["stdout"])

    def test_typescript_failure_never_replaces_visible_output(self):
        raw = "\n".join(
            f"src/file{i}.ts({i + 1},1): error TS2322: synthetic type failure {i}"
            for i in range(8)
        )
        compressed = compress_text(raw, target_tokens=20)
        self.assertEqual(compressed.parser, "tsc")
        self.assertFalse(compressed.complete)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "tsc --noEmit"},
                    "tool_response": {"stdout": raw, "stderr": ""},
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=20,
                )
                self.assertEqual(output, {})
                self.assertEqual(digest["parser"]["name"], "tsc")
                self.assertFalse(digest["parser"]["complete"])

    def test_lint_output_never_replaces_visible_output(self):
        raw = "\n".join(
            f"src/file{i}.py:{i + 1}:1: error synthetic lint failure {i}"
            for i in range(8)
        )
        compressed = compress_text(raw, target_tokens=20)
        self.assertEqual(compressed.parser, "lint")
        self.assertFalse(compressed.complete)

        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "lint"},
                    "tool_response": {"stdout": raw, "stderr": ""},
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=20,
                )
                self.assertEqual(output, {})
                self.assertEqual(digest["parser"]["name"], "lint")
                self.assertFalse(digest["parser"]["complete"])

    def test_incomplete_mixed_stdout_stderr_never_replaces(self):
        stdout = "\n".join(f"build output {i}: continuing" for i in range(100))
        stderr = "rollback path unavailable; inspect deployment state"
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "build && deploy"},
                    "tool_response": {"stdout": stdout, "stderr": stderr},
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=40,
                )
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
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "pipeline"},
                    "tool_response": {"stdout": raw, "stderr": ""},
                }
                output, digest = process_event(
                    event,
                    mode="replace",
                    target_tokens=40,
                )
                self.assertEqual(output, {})
                self.assertFalse(digest["parser"]["complete"])
                stored = EvidenceStore(project_td).get(digest["raw_ref"])
                self.assertIn(hidden_failure, stored["tool_response"]["stdout"])

    def test_invalid_environment_budget_falls_back_without_breaking_hook(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(
                os.environ,
                {
                    "SHOWMEWHY_HOME": state_td,
                    "SHOWMEWHY_MODE": "replace",
                    "SHOWMEWHY_CONTEXT_BUDGET_TOKENS": "not-a-number",
                },
                clear=False,
            ):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest -q"},
                    "tool_response": {
                        "stdout": self._pytest_pass_log(),
                        "stderr": "",
                    },
                }
                output, digest = process_event(event)
                self.assertIsNotNone(digest)
                self.assertIn("updatedToolOutput", output["hookSpecificOutput"])

    def test_digest_persistence_failure_preserves_visible_output(self):
        with tempfile.TemporaryDirectory() as project_td, tempfile.TemporaryDirectory() as state_td:
            with patch.dict(os.environ, {"SHOWMEWHY_HOME": state_td}):
                event = {
                    "cwd": project_td,
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest -q"},
                    "tool_response": {
                        "stdout": self._pytest_pass_log(),
                        "stderr": "",
                    },
                }
                with patch(
                    "showmewhy_runtime.hook.persist_digest",
                    side_effect=OSError("disk full"),
                ):
                    output, digest = process_event(
                        event,
                        mode="replace",
                        target_tokens=300,
                    )
                self.assertEqual(output, {})
                self.assertIsNotNone(digest)
                self.assertTrue(
                    any(
                        "Digest persistence failed" in caveat
                        for caveat in digest["caveats"]
                    )
                )

    def test_shadow_mode_never_replaces(self):
        with tempfile.TemporaryDirectory() as td:
            event = {
                "cwd": td,
                "tool_name": "Bash",
                "tool_input": {},
                "tool_response": {
                    "stdout": self._pytest_pass_log(),
                    "stderr": "",
                },
            }
            output, digest = process_event(
                event,
                mode="shadow",
                target_tokens=300,
            )
            self.assertEqual(output, {})
            self.assertIsNotNone(digest)

    def test_short_output_passes_through(self):
        event = {
            "tool_name": "Bash",
            "tool_response": {"stdout": "ok", "stderr": ""},
        }
        output, digest = process_event(event, target_tokens=300)
        self.assertEqual(output, {})
        self.assertIsNone(digest)


if __name__ == "__main__":
    unittest.main()
