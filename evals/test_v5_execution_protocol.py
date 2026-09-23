from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
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


builder = load_module("v5_record_builder", V5 / "record_builder.py")
pair_runner = load_module("v5_pair_runner_protocol", V5 / "pair_runner.py")


class V5ExecutionProtocolTests(unittest.TestCase):
    def test_six_frozen_pair_specs_match_selection_manifest_without_oracle_leakage(self):
        manifest = json.loads(
            (PILOT / "manifest.json").read_text(encoding="utf-8")
        )
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
                self.assertEqual(data["version"], "v5-pair-spec-2")
                self.assertEqual(data["repository"], task["repository"])
                self.assertEqual(data["revision"], task["pre_fix_revision"])
                self.assertEqual(data["task_prompt"], task["task_prompt"])
                self.assertEqual(
                    data["task_prompt_sha256"],
                    hashlib.sha256(
                        data["task_prompt"].encode("utf-8")
                    ).hexdigest(),
                )
                self.assertEqual(data["model"], "__runtime__")
                self.assertEqual(data["agent_runtime"], "__runtime__")
                self.assertEqual(data["tool_profile"], "__runtime__")
                self.assertEqual(data["repeat_index"], 0)
                self.assertEqual(data["command"]["argv"], ["__runtime__"])
                self.assertEqual(data["command"].get("pass_env"), [])
                self.assertNotIn("claude", raw.lower())
                self.assertNotIn("anthropic", raw.lower())
                for key in forbidden:
                    self.assertNotIn(f'"{key}"', raw)

    def test_runtime_identity_and_adapter_are_supplied_at_execution_time(self):
        spec = pair_runner._load_spec(
            PAIRS / "pytest-warning-module-attribution.json"
        )
        env = {
            "SHOWMEWHY_V5_EXECUTION_MODEL": "example-model",
            "SHOWMEWHY_V5_EXECUTION_RUNTIME": "example-agent@1.0",
            "SHOWMEWHY_V5_EXECUTION_TOOL_PROFILE": "read-write-local",
            "SHOWMEWHY_V5_ADAPTER_ARGV_JSON": json.dumps(
                ["python", "/tmp/example_adapter.py"]
            ),
            "SHOWMEWHY_V5_ADAPTER_PASS_ENV_JSON": json.dumps(
                ["EXAMPLE_PROVIDER_TOKEN"]
            ),
            "SHOWMEWHY_V5_TIMEOUT_SECONDS": "900",
        }
        with patch.dict(os.environ, env, clear=False):
            resolved = pair_runner._resolve_execution_spec(spec)

        self.assertEqual(resolved["model"], "example-model")
        self.assertEqual(
            resolved["agent_runtime"], "example-agent@1.0"
        )
        self.assertEqual(
            resolved["tool_profile"], "read-write-local"
        )
        self.assertEqual(
            resolved["command"]["argv"],
            ["python", "/tmp/example_adapter.py"],
        )
        self.assertEqual(
            resolved["command"]["pass_env"],
            ["EXAMPLE_PROVIDER_TOKEN"],
        )
        self.assertEqual(
            resolved["command"]["timeout_seconds"],
            900,
        )

    def test_missing_runtime_configuration_fails_before_provider_execution(self):
        spec = pair_runner._load_spec(
            PAIRS / "pytest-warning-module-attribution.json"
        )
        names = [
            "SHOWMEWHY_V5_EXECUTION_MODEL",
            "SHOWMEWHY_V5_EXECUTION_RUNTIME",
            "SHOWMEWHY_V5_EXECUTION_TOOL_PROFILE",
            "SHOWMEWHY_V5_ADAPTER_ARGV_JSON",
            "SHOWMEWHY_V5_ADAPTER_PASS_ENV_JSON",
            "SHOWMEWHY_V5_TIMEOUT_SECONDS",
        ]
        clean = {name: "" for name in names}
        with patch.dict(os.environ, clean, clear=False):
            with self.assertRaisesRegex(
                pair_runner.PairRunError,
                "missing required runtime environment variable",
            ):
                pair_runner._resolve_execution_spec(spec)

    def test_runner_has_no_implicit_provider_credentials(self):
        self.assertNotIn("ANTHROPIC_API_KEY", pair_runner.ESSENTIAL_ENV)
        self.assertNotIn("CLAUDE_CONFIG_DIR", pair_runner.ESSENTIAL_ENV)
        self.assertNotIn(
            "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB",
            pair_runner.ESSENTIAL_ENV,
        )

    def _raw_pair(self, root: Path) -> Path:
        pair_dir = root / "pair"
        (pair_dir / "baseline").mkdir(parents=True)
        (pair_dir / "showmewhy").mkdir()
        (pair_dir / "baseline" / "result.txt").write_text(
            "Claim A is fixed. Claim B is safe.\n",
            encoding="utf-8",
        )
        (pair_dir / "showmewhy" / "result.txt").write_text(
            "SHOWMEWHY\n\n"
            "NEEDS YOU\n"
            "Claim B lacks a boundary witness.\n",
            encoding="utf-8",
        )
        pair = {
            "version": "v5-pair-run-2",
            "design": "single-task-posthoc-verification",
            "pair_status": "valid",
            "task_id": "fixture-task",
            "domain": "code",
            "pairing": {
                "pair_id": "fixture-task-r0",
                "repository": "fixture/repo",
                "revision": "a" * 40,
                "task_prompt_sha256": "b" * 64,
                "model": "claude-sonnet-5",
                "agent_runtime": "claude-code-cli@2.1.278",
                "tool_profile": "v5-posthoc-restricted-v2",
                "repeat_index": 0,
            },
            "task_prompt": {
                "path": "task.prompt.txt",
                "sha256": "b" * 64,
                "bytes": 1,
            },
            "execution_order": ["baseline", "showmewhy"],
            "task_execution_count": 1,
            "command": {},
            "conditions": {
                "baseline": {
                    "status": "valid",
                    "role": "task-agent-result",
                },
                "showmewhy": {
                    "status": "valid",
                    "role": "posthoc-verification",
                },
            },
            "workspace_equivalence": {
                "pre_verification": "identical",
                "post_verification": "identical",
            },
            "ground_truth_present": False,
        }
        path = pair_dir / "pair.json"
        path.write_text(
            json.dumps(pair),
            encoding="utf-8",
        )
        return path

    def _ground_truth(self, pair_path: Path) -> Path:
        pair = json.loads(
            pair_path.read_text(encoding="utf-8")
        )
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
                },
                {
                    "id": "C2",
                    "text": "Claim B is safe",
                    "material": True,
                    "failing": True,
                    "human_review": True,
                },
            ],
            "counterexamples": [
                {
                    "id": "X1",
                    "description": (
                        "A concrete boundary input refutes Claim B."
                    ),
                    "claim_ids": ["C2"],
                }
            ],
        }
        path = pair_path.parent / "ground-truth.json"
        path.write_text(
            json.dumps(gt),
            encoding="utf-8",
        )
        return path

    def test_ground_truth_template_does_not_read_or_embed_condition_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            pair = json.loads(
                pair_path.read_text(encoding="utf-8")
            )
            manifest = {
                "tasks": [
                    {
                        "task_id": "fixture-task",
                        "repository": "fixture/repo",
                        "pre_fix_revision": "a" * 40,
                        "task_prompt_sha256": "b" * 64,
                        "task_prompt": "fixture prompt",
                        "oracle_refs": ["oracle://fixture"],
                        "boundary_notes": "fixture boundary",
                    }
                ]
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )
            value = builder.build_ground_truth_template(
                manifest_path=manifest_path,
                pair_path=pair_path,
                task_id="fixture-task",
            )
            serialized = json.dumps(value)
            self.assertNotIn(
                "Claim A is fixed",
                serialized,
            )
            self.assertNotIn(
                "Claim B lacks",
                serialized,
            )
            self.assertFalse(
                value["blinded_to_showmewhy"]
            )
            self.assertEqual(value["claims"], [])
            self.assertEqual(
                value["counterexamples"],
                [],
            )
            self.assertEqual(
                value["pairing"],
                pair["pairing"],
            )

    def _completed_assessment(
        self,
        pair_path: Path,
        gt_path: Path,
    ) -> dict:
        template = builder.build_assessment_template(
            pair_path=pair_path,
            ground_truth_path=gt_path,
        )
        template["baseline"].update(
            {
                "review_completed_blind_to_ground_truth": True,
                "mapping_completed_after_timer": True,
                "inspected_claim_ids": ["C1", "C2"],
                "detected_failure_ids": [],
                "detected_counterexample_ids": [],
                "verification_seconds": 30.0,
            }
        )
        template["showmewhy"].update(
            {
                "review_completed_blind_to_ground_truth": True,
                "mapping_completed_after_timer": True,
                "surfaced_claim_ids": ["C2"],
                "verified_claim_ids": ["C1"],
                "refuted_claim_ids": [],
                "open_claim_ids": ["C2"],
                "detected_failure_ids": ["C2"],
                "detected_counterexample_ids": ["X1"],
                "verification_seconds": 12.0,
            }
        )
        return template

    def test_assessment_template_does_not_expose_ground_truth_labels(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            gt_path = self._ground_truth(pair_path)
            template = builder.build_assessment_template(
                pair_path=pair_path,
                ground_truth_path=gt_path,
            )
            serialised = json.dumps(template)
            self.assertNotIn("Claim A works", serialised)
            self.assertNotIn("A concrete boundary input", serialised)
            self.assertTrue(
                template["review_protocol"][
                    "ground_truth_hidden_during_review"
                ]
            )
            self.assertFalse(
                template["baseline"][
                    "review_completed_blind_to_ground_truth"
                ]
            )

    def test_record_builder_hash_anchors_assessment_and_produces_scorer_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            gt_path = self._ground_truth(pair_path)
            assessment_value = self._completed_assessment(
                pair_path,
                gt_path,
            )
            assessment = (
                pair_path.parent / "assessment.json"
            )
            assessment.write_text(
                json.dumps(assessment_value),
                encoding="utf-8",
            )

            record = builder.assemble_record(
                pair_path=pair_path,
                ground_truth_path=gt_path,
                assessment_path=assessment,
            )
            self.assertEqual(
                record["ground_truth"]["failing_claim_ids"],
                ["C2"],
            )
            self.assertEqual(
                record["ground_truth"]["counterexample_ids"],
                ["X1"],
            )
            self.assertEqual(
                record["showmewhy"]["open_claim_ids"],
                ["C2"],
            )
            self.assertEqual(
                record["showmewhy"][
                    "detected_counterexample_ids"
                ],
                ["X1"],
            )
            self.assertGreater(
                record["baseline"]["inspection_tokens"],
                0,
            )
            self.assertGreater(
                record["showmewhy"]["inspection_lines"],
                0,
            )

            (
                pair_path.parent
                / "showmewhy"
                / "result.txt"
            ).write_text(
                "tampered\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                builder.RecordBuildError,
                "hash",
            ):
                builder.assemble_record(
                    pair_path=pair_path,
                    ground_truth_path=gt_path,
                    assessment_path=assessment,
                )

    def test_unblinded_or_in_timer_mapping_assessment_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            gt_path = self._ground_truth(pair_path)
            assessment = self._completed_assessment(
                pair_path,
                gt_path,
            )
            assessment["baseline"][
                "review_completed_blind_to_ground_truth"
            ] = False
            assessment_path = (
                pair_path.parent / "assessment-unblinded.json"
            )
            assessment_path.write_text(
                json.dumps(assessment),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                builder.RecordBuildError,
                "blind human review",
            ):
                builder.assemble_record(
                    pair_path=pair_path,
                    ground_truth_path=gt_path,
                    assessment_path=assessment_path,
                )

    def test_inspection_cost_uses_hash_anchored_files_actually_reviewed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            gt_path = self._ground_truth(pair_path)
            pair_dir = pair_path.parent

            extra = (
                pair_dir
                / "baseline"
                / "workspace.diff"
            )
            extra.write_text(
                "diff evidence\n" * 20,
                encoding="utf-8",
            )

            assessment = self._completed_assessment(
                pair_path,
                gt_path,
            )
            assessment["baseline"][
                "inspection_artifacts"
            ].append(
                {
                    "path": "baseline/workspace.diff",
                    "sha256": hashlib.sha256(
                        extra.read_bytes()
                    ).hexdigest(),
                }
            )
            assessment["baseline"][
                "detected_counterexample_ids"
            ] = ["X-FALSE-POSITIVE"]
            assessment_path = (
                pair_dir / "assessment-inspection.json"
            )
            assessment_path.write_text(
                json.dumps(assessment),
                encoding="utf-8",
            )

            record = builder.assemble_record(
                pair_path=pair_path,
                ground_truth_path=gt_path,
                assessment_path=assessment_path,
            )
            baseline_result = (
                pair_dir
                / "baseline"
                / "result.txt"
            )
            result_only_tokens = max(
                1,
                (
                    len(baseline_result.read_bytes())
                    + 3
                )
                // 4,
            )
            self.assertGreater(
                record["baseline"]["inspection_tokens"],
                result_only_tokens,
            )
            self.assertEqual(
                record["baseline"][
                    "detected_counterexample_ids"
                ],
                ["X-FALSE-POSITIVE"],
            )

    def test_inspection_artifact_hash_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            gt_path = self._ground_truth(pair_path)
            assessment = self._completed_assessment(
                pair_path,
                gt_path,
            )
            assessment["baseline"][
                "inspection_artifacts"
            ][0]["sha256"] = "0" * 64
            assessment_path = (
                pair_path.parent
                / "assessment-bad-hash.json"
            )
            assessment_path.write_text(
                json.dumps(assessment),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                builder.RecordBuildError,
                "hash does not match",
            ):
                builder.assemble_record(
                    pair_path=pair_path,
                    ground_truth_path=gt_path,
                    assessment_path=assessment_path,
                )

    def test_old_or_nonidentical_pair_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pair_path = self._raw_pair(root)
            pair = json.loads(
                pair_path.read_text(encoding="utf-8")
            )
            pair["workspace_equivalence"][
                "post_verification"
            ] = "modified"
            pair_path.write_text(
                json.dumps(pair),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                builder.RecordBuildError,
                "modified",
            ):
                builder.build_ground_truth_template(
                    manifest_path=root / "unused.json",
                    pair_path=pair_path,
                    task_id="fixture-task",
                )


if __name__ == "__main__":
    unittest.main()
