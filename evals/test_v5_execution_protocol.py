from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "evals" / "v5"
PILOT = V5 / "pilot"
PAIRS = PILOT / "pairs"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


adapter = load_module("v5_claude_adapter", V5 / "claude_adapter.py")
builder = load_module("v5_record_builder", V5 / "record_builder.py")
pair_runner = load_module("v5_pair_runner_protocol", V5 / "pair_runner.py")


class V5ExecutionProtocolTests(unittest.TestCase):
    def test_six_frozen_pair_specs_match_selection_manifest_without_oracle_leakage(self):
        manifest = json.loads((PILOT / "manifest.json").read_text(encoding="utf-8"))
        tasks = {task["task_id"]: task for task in manifest["tasks"]}
        specs = sorted(PAIRS.glob("*.json"))
        self.assertEqual(len(specs), 6)
        self.assertEqual({path.stem for path in specs}, set(tasks))

        forbidden = pair_runner.FORBIDDEN_EXECUTION_KEYS
        for path in specs:
            with self.subTest(spec=path.name):
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw)
                task = tasks[data["task_id"]]
                self.assertEqual(data["repository"], task["repository"])
                self.assertEqual(data["revision"], task["pre_fix_revision"])
                self.assertEqual(data["task_prompt"], task["task_prompt"])
                self.assertEqual(
                    data["task_prompt_sha256"],
                    hashlib.sha256(data["task_prompt"].encode("utf-8")).hexdigest(),
                )
                self.assertEqual(data["model"], "claude-sonnet-5")
                self.assertEqual(data["agent_runtime"], "claude-code-cli")
                self.assertEqual(data["tool_profile"], "v5-code-bare-v1")
                self.assertEqual(
                    data["command"]["argv"],
                    ["{python}", "{showmewhy_repo}/evals/v5/claude_adapter.py"],
                )
                for key in forbidden:
                    self.assertNotIn(f'"{key}"', raw)

    def test_portable_argv_placeholders_expand_to_current_checkout(self):
        argv = pair_runner._expand_argv(
            ["{python}", "{showmewhy_repo}/evals/v5/claude_adapter.py"]
        )
        self.assertEqual(Path(argv[0]).resolve(), Path(os.sys.executable).resolve())
        self.assertEqual(
            Path(argv[1]).resolve(),
            (ROOT / "evals" / "v5" / "claude_adapter.py").resolve(),
        )

    def _adapter_run(self, condition: str):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        workspace = root / "workspace"
        output = root / condition
        workspace.mkdir()
        output.mkdir()
        prompt = root / "prompt.txt"
        prompt.write_text("Fix the bug and add tests.", encoding="utf-8")
        digest = hashlib.sha256(prompt.read_bytes()).hexdigest()

        env = {
            "SHOWMEWHY_V5_CONDITION": condition,
            "SHOWMEWHY_V5_PAIR_ID": "fixture-r0",
            "SHOWMEWHY_V5_PROMPT_SHA256": digest,
            "SHOWMEWHY_V5_PROMPT_FILE": str(prompt),
            "SHOWMEWHY_V5_OUTPUT_DIR": str(output),
            "SHOWMEWHY_V5_WORKSPACE": str(workspace),
            "SHOWMEWHY_V5_MODEL": "claude-sonnet-5",
            "SHOWMEWHY_V5_AGENT_RUNTIME": "claude-code-cli",
            "SHOWMEWHY_V5_TOOL_PROFILE": "v5-code-bare-v1",
        }
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(list(argv))
            if argv[1:] == ["--version"]:
                return SimpleNamespace(returncode=0, stdout="2.1.999\n", stderr="")
            response = {
                "result": (
                    "SHOWMEWHY\n\nNEEDS YOU\n1  boundary remains open\n\nDO NEXT\nRun it."
                    if condition == "showmewhy"
                    else "Implemented the fix and added tests."
                ),
                "is_error": False,
                "subtype": "success",
                "session_id": "session-fixture",
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "total_cost_usd": 0.01,
            }
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(response),
                stderr="",
            )

        old_cwd = Path.cwd()
        try:
            os.chdir(workspace)
            with patch.dict(os.environ, env, clear=False), patch.object(
                adapter.shutil, "which", return_value="/fake/claude"
            ), patch.object(adapter.subprocess, "run", side_effect=fake_run):
                rc = adapter.run()
        finally:
            os.chdir(old_cwd)
        return output, calls, rc

    def test_adapter_baseline_is_bare_and_has_no_showmewhy_treatment(self):
        output, calls, rc = self._adapter_run("baseline")
        self.assertEqual(rc, 0)
        invocation = calls[0]
        self.assertIn("--bare", invocation)
        self.assertIn("--permission-mode", invocation)
        self.assertNotIn("--append-system-prompt-file", invocation)
        meta = json.loads((output / "adapter.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["treatment"], "none")
        self.assertIsNone(meta["treatment_sha256"])
        self.assertTrue((output / "result.txt").is_file())

    def test_adapter_showmewhy_hashes_canonical_skill_treatment(self):
        output, calls, rc = self._adapter_run("showmewhy")
        self.assertEqual(rc, 0)
        invocation = calls[0]
        self.assertIn("--bare", invocation)
        self.assertIn("--append-system-prompt-file", invocation)
        meta = json.loads((output / "adapter.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["treatment"], "canonical-skill-system-append")
        expected_skill = hashlib.sha256(
            (ROOT / "skills" / "showmewhy" / "SKILL.md").read_bytes()
        ).hexdigest()
        self.assertEqual(meta["canonical_skill_sha256"], expected_skill)
        self.assertTrue(meta["treatment_sha256"])
        self.assertTrue((output / "showmewhy-treatment.md").is_file())

    def _raw_pair(self, root: Path) -> Path:
        pair_dir = root / "pair"
        (pair_dir / "baseline").mkdir(parents=True)
        (pair_dir / "showmewhy").mkdir()
        (pair_dir / "baseline" / "result.txt").write_text(
            "Claim A is fixed. Claim B is safe.\n", encoding="utf-8"
        )
        (pair_dir / "showmewhy" / "result.txt").write_text(
            "SHOWMEWHY\n\nNEEDS YOU\nClaim B lacks a boundary witness.\n",
            encoding="utf-8",
        )
        pair = {
            "version": "v5-pair-run-1",
            "pair_status": "valid",
            "task_id": "fixture-task",
            "domain": "code",
            "pairing": {
                "pair_id": "fixture-task-r0",
                "repository": "fixture/repo",
                "revision": "a" * 40,
                "task_prompt_sha256": "b" * 64,
                "model": "claude-sonnet-5",
                "agent_runtime": "claude-code-cli",
                "tool_profile": "v5-code-bare-v1",
                "repeat_index": 0,
            },
            "task_prompt": {"path": "task.prompt.txt", "sha256": "b" * 64, "bytes": 1},
            "execution_order": ["baseline", "showmewhy"],
            "command": {},
            "conditions": {
                "baseline": {"status": "valid"},
                "showmewhy": {"status": "valid"},
            },
            "ground_truth_present": False,
        }
        path = pair_dir / "pair.json"
        path.write_text(json.dumps(pair), encoding="utf-8")
        return path

    def _ground_truth(self, pair_path: Path) -> Path:
        pair = json.loads(pair_path.read_text(encoding="utf-8"))
        gt = {
            "version": "v5-ground-truth-1",
            "task_id": pair["task_id"],
            "domain": pair["domain"],
            "pairing": pair["pairing"],
            "task_prompt": "fixture",
            "oracle_refs": ["oracle://fixture"],
            "boundary_notes": "fixture",
            "labeler_count": 2,
            "adjudicated": True,
            "blinded_to_showmewhy": True,
            "claims": [
                {
                    "id": "C1",
                    "text": "Claim A works",
                    "material": True,
                    "failing": False,
                    "human_review": False,
                    "counterexample": False,
                },
                {
                    "id": "C2",
                    "text": "Claim B is safe",
                    "material": True,
                    "failing": True,
                    "human_review": True,
                    "counterexample": True,
                },
            ],
        }
        path = pair_path.parent / "ground-truth.json"
        path.write_text(json.dumps(gt), encoding="utf-8")
        return path

    def test_ground_truth_template_does_not_read_or_embed_condition_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            pair = json.loads(pair_path.read_text(encoding="utf-8"))
            manifest = {
                "tasks": [{
                    "task_id": "fixture-task",
                    "repository": "fixture/repo",
                    "pre_fix_revision": "a" * 40,
                    "task_prompt_sha256": "b" * 64,
                    "task_prompt": "fixture prompt",
                    "oracle_refs": ["oracle://fixture"],
                    "boundary_notes": "fixture boundary",
                }]
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            value = builder.build_ground_truth_template(
                manifest_path=manifest_path,
                pair_path=pair_path,
                task_id="fixture-task",
            )
            serialized = json.dumps(value)
            self.assertNotIn("Claim A is fixed", serialized)
            self.assertNotIn("Claim B lacks", serialized)
            self.assertFalse(value["blinded_to_showmewhy"])
            self.assertEqual(value["claims"], [])
            self.assertEqual(value["pairing"], pair["pairing"])

    def test_record_builder_hash_anchors_assessment_and_produces_scorer_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            gt_path = self._ground_truth(pair_path)
            template = builder.build_assessment_template(
                pair_path=pair_path,
                ground_truth_path=gt_path,
            )
            template["baseline"].update({
                "inspected_claim_ids": ["C1", "C2"],
                "detected_failure_ids": [],
                "detected_counterexample_ids": [],
                "verification_seconds": 30.0,
            })
            template["showmewhy"].update({
                "surfaced_claim_ids": ["C2"],
                "verified_claim_ids": ["C1"],
                "refuted_claim_ids": [],
                "open_claim_ids": ["C2"],
                "detected_failure_ids": ["C2"],
                "detected_counterexample_ids": ["C2"],
                "verification_seconds": 12.0,
            })
            assessment = pair_path.parent / "assessment.json"
            assessment.write_text(json.dumps(template), encoding="utf-8")

            record = builder.assemble_record(
                pair_path=pair_path,
                ground_truth_path=gt_path,
                assessment_path=assessment,
            )
            self.assertEqual(record["ground_truth"]["failing_claim_ids"], ["C2"])
            self.assertEqual(record["showmewhy"]["open_claim_ids"], ["C2"])
            self.assertGreater(record["baseline"]["inspection_tokens"], 0)
            self.assertGreater(record["showmewhy"]["inspection_lines"], 0)

            # Tampering after assessment must invalidate the packet.
            (pair_path.parent / "showmewhy" / "result.txt").write_text(
                "tampered\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(builder.RecordBuildError, "hash"):
                builder.assemble_record(
                    pair_path=pair_path,
                    ground_truth_path=gt_path,
                    assessment_path=assessment,
                )


if __name__ == "__main__":
    unittest.main()
