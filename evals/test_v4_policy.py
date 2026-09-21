import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from showmewhy_runtime.common import runtime_root
from showmewhy_runtime.hook import process_event
from showmewhy_runtime.policy import clear_safety_lock, load_feedback, recommend_policy, record_feedback


class V4PolicyTests(unittest.TestCase):
    def _write_run(self, cwd, run_id, *, complete=True, confidence="high", compression=80.0, avoided=1000):
        root = runtime_root(cwd) / "runs"
        root.mkdir(parents=True, exist_ok=True)
        run = {
            "run_id": run_id,
            "parser": {"complete": complete, "confidence": confidence, "name": "pytest"},
            "compression_pct": compression,
            "tokens_avoided": avoided,
        }
        (root / f"{run_id}.json").write_text(json.dumps(run), encoding="utf-8")

    def _feedback(self, cwd, idx, *, reopened=False, material_loss=False, complete=True, compression=80.0):
        run_id = f"run-{idx:012x}"
        self._write_run(cwd, run_id, complete=complete, compression=compression)
        return record_feedback(run_id, reopened=reopened, material_loss=material_loss, cwd=cwd)

    def test_cold_start_observes_without_replacing(self):
        with tempfile.TemporaryDirectory() as td:
            policy = recommend_policy(td)
            self.assertEqual(policy["target_tokens"], 700)
            self.assertEqual(policy["mode"], "shadow")


    def test_three_clean_feedback_samples_allow_baseline_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            for idx in range(3):
                self._feedback(td, idx, reopened=False, complete=True, compression=60.0)
            policy = recommend_policy(td)
            self.assertEqual(policy["mode"], "replace")
            self.assertEqual(policy["target_tokens"], 700)

    def test_low_reopen_complete_runs_allow_stronger_compression(self):
        with tempfile.TemporaryDirectory() as td:
            for idx in range(5):
                self._feedback(td, idx, reopened=False, complete=True, compression=80.0)
            policy = recommend_policy(td)
            self.assertEqual(policy["target_tokens"], 500)
            self.assertFalse(policy["safety_lock"])

    def test_high_reopen_rate_preserves_more_context(self):
        with tempfile.TemporaryDirectory() as td:
            for idx in range(5):
                self._feedback(td, idx, reopened=idx < 3, complete=True, compression=80.0)
            policy = recommend_policy(td)
            self.assertEqual(policy["target_tokens"], 1100)

    def test_low_parser_completeness_preserves_more_context(self):
        with tempfile.TemporaryDirectory() as td:
            for idx in range(4):
                self._feedback(td, idx, complete=idx == 0, compression=80.0)
            self.assertEqual(recommend_policy(td)["target_tokens"], 1100)

    def test_material_loss_sets_sticky_shadow_lock(self):
        with tempfile.TemporaryDirectory() as td:
            self._feedback(td, 1, material_loss=True)
            self._feedback(td, 2, material_loss=False)
            policy = recommend_policy(td)
            self.assertTrue(policy["safety_lock"])
            self.assertEqual(policy["mode"], "shadow")
            self.assertEqual(policy["target_tokens"], 1200)
            state = clear_safety_lock(td)
            self.assertFalse(state["safety_lock"])
            self.assertFalse(recommend_policy(td)["safety_lock"])


    def test_safety_lock_cannot_be_bypassed_by_explicit_replace_mode(self):
        with tempfile.TemporaryDirectory() as td:
            self._feedback(td, 1, material_loss=True)
            raw = "\n".join("." * 120 for _ in range(40)) + "\n127 passed in 2s\n"
            event = {
                "cwd": td,
                "tool_name": "Bash",
                "tool_input": {"command": "pytest -q"},
                "tool_response": {"stdout": raw, "stderr": ""},
            }
            output, digest = process_event(event, mode="replace", target_tokens=100)
            self.assertEqual(output, {})
            self.assertEqual(digest["policy"]["mode"], "shadow")
            self.assertTrue(digest["policy"]["safety_lock"])

    def test_feedback_contains_metrics_not_task_content(self):
        with tempfile.TemporaryDirectory() as td:
            event = self._feedback(td, 1)
            self.assertEqual(set(event), {"version", "created_unix", "run_id", "reopened", "material_loss", "parser_complete", "parser_confidence", "compression_pct", "tokens_avoided"})
            stored = load_feedback(td)
            serialized = json.dumps(stored)
            self.assertNotIn("summary", serialized)
            self.assertNotIn("findings", serialized)
            self.assertNotIn("tool_response", serialized)

    def test_safety_lock_prevents_context_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            self._feedback(td, 1, material_loss=True)
            raw = "\n".join(f"noise line {i}" for i in range(800)) + "\n= 1 failed, 20 passed in 2s =\n"
            event = {"cwd": td, "tool_name": "Bash", "tool_input": {"command": "pytest"}, "tool_response": {"stdout": raw, "stderr": ""}}
            output, digest = process_event(event)
            self.assertEqual(output, {})
            self.assertIsNotNone(digest)
            self.assertTrue(digest["policy"]["safety_lock"])
            self.assertEqual(digest["policy"]["mode"], "shadow")


if __name__ == "__main__":
    unittest.main()
