from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "evals" / "v5"
sys.path.insert(0, str(V5))

from pair_runner import PairRunError, run_pair


def git(cwd: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return process.stdout.strip()


class V5PairRunnerTests(unittest.TestCase):
    def _repo(self, root: Path) -> tuple[Path, str]:
        repo = root / "subject"
        repo.mkdir()
        git(repo, "init")
        git(repo, "config", "user.name", "V5 Pair Test")
        git(repo, "config", "user.email", "v5-pair@example.invalid")
        (repo / "app.txt").write_text("base\n", encoding="utf-8")
        git(repo, "add", "app.txt")
        git(repo, "commit", "-m", "base")
        return repo, git(repo, "rev-parse", "HEAD")

    def _adapter(
        self,
        root: Path,
        *,
        fail_baseline: bool = False,
        mutate_verifier: bool = False,
    ) -> Path:
        adapter = root / (
            "adapter_fail.py"
            if fail_baseline
            else "adapter_mutate.py"
            if mutate_verifier
            else "adapter.py"
        )
        adapter.write_text(
            (
                "import hashlib, json, os, pathlib, sys\n"
                "condition = os.environ['SHOWMEWHY_V5_CONDITION']\n"
                "workspace = pathlib.Path(os.environ['SHOWMEWHY_V5_WORKSPACE'])\n"
                "out = pathlib.Path(os.environ['SHOWMEWHY_V5_OUTPUT_DIR'])\n"
                "prompt = pathlib.Path(os.environ['SHOWMEWHY_V5_PROMPT_FILE']).read_text()\n"
                "if "
                + ("condition == 'baseline'" if fail_baseline else "False")
                + ":\n"
                "    print('forced baseline adapter failure', file=sys.stderr)\n"
                "    raise SystemExit(7)\n"
                "if condition == 'baseline':\n"
                "    (workspace / 'agent-change.txt').write_text('fixed\\n')\n"
                "    result = 'Implemented the fix and added regression coverage.'\n"
                "    base_hash = None\n"
                "else:\n"
                "    base_file = pathlib.Path(os.environ['SHOWMEWHY_V5_BASE_RESULT_FILE'])\n"
                "    result_bytes = base_file.read_bytes()\n"
                "    base_hash = hashlib.sha256(result_bytes).hexdigest()\n"
                "    assert (workspace / 'agent-change.txt').read_text() == 'fixed\\n'\n"
                + (
                    "    (workspace / 'agent-change.txt').write_text('verifier modified code\\n')\n"
                    if mutate_verifier
                    else ""
                )
                + "    result = 'SHOWMEWHY\\n\\nNEEDS YOU\\nBoundary evidence remains open.\\n'\n"
                "(out / 'result.txt').write_text(result)\n"
                "(out / 'adapter.json').write_text(json.dumps({\n"
                "    'condition': condition,\n"
                "    'prompt_sha256': os.environ['SHOWMEWHY_V5_PROMPT_SHA256'],\n"
                "    'prompt': prompt,\n"
                "    'baseline_result_sha256': base_hash,\n"
                "}, sort_keys=True))\n"
                "print(result)\n"
            ),
            encoding="utf-8",
        )
        return adapter

    def _spec(
        self,
        path: Path,
        *,
        revision: str,
        adapter: Path,
        repeat_index: int = 0,
        pair_id: str | None = None,
    ) -> dict[str, object]:
        prompt = "Fix the inherited-state bug and verify the boundary."
        data: dict[str, object] = {
            "version": "v5-pair-spec-2",
            "task_id": "fixture-task",
            "domain": "code",
            "repository": "fixture/local",
            "revision": revision,
            "task_prompt": prompt,
            "task_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "model": "fixture-model",
            "agent_runtime": "fixture-agent@1.0.0",
            "tool_profile": "fixture-posthoc",
            "repeat_index": repeat_index,
            "command": {
                "argv": [sys.executable, str(adapter)],
                "timeout_seconds": 30,
                "pass_env": [],
            },
        }
        if pair_id is not None:
            data["pair_id"] = pair_id
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_single_task_execution_is_cloned_for_posthoc_verification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root)
            spec = root / "pair-spec.json"
            self._spec(
                spec,
                revision=revision,
                adapter=adapter,
                pair_id="fixture-pair",
            )
            output = root / "runs"

            bundle = run_pair(
                spec_path=spec,
                source_checkout=repo,
                output_root=output,
            )

            self.assertEqual(bundle["version"], "v5-pair-run-2")
            self.assertEqual(
                bundle["design"], "single-task-posthoc-verification"
            )
            self.assertEqual(bundle["task_execution_count"], 1)
            self.assertEqual(bundle["pair_status"], "valid")
            self.assertFalse(bundle["ground_truth_present"])
            self.assertEqual(
                bundle["execution_order"], ["baseline", "showmewhy"]
            )
            self.assertEqual(
                bundle["workspace_equivalence"]["pre_verification"],
                "identical",
            )
            self.assertEqual(
                bundle["workspace_equivalence"]["post_verification"],
                "identical",
            )
            self.assertEqual(
                bundle["conditions"]["baseline"]["role"],
                "task-agent-result",
            )
            self.assertEqual(
                bundle["conditions"]["showmewhy"]["role"],
                "posthoc-verification",
            )
            self.assertIn(
                "agent-change.txt",
                bundle["conditions"]["baseline"]["git"]["changed_files"],
            )
            self.assertIn(
                "agent-change.txt",
                bundle["conditions"]["showmewhy"]["git"]["changed_files"],
            )
            self.assertEqual(
                bundle["conditions"]["baseline"]["git"]["diff"]["sha256"],
                bundle["conditions"]["showmewhy"]["git"]["diff"]["sha256"],
            )

            pair_dir = output / "fixture-pair"
            baseline_result = (
                pair_dir / "baseline" / "result.txt"
            ).read_bytes()
            show_meta = json.loads(
                (pair_dir / "showmewhy" / "adapter.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                show_meta["baseline_result_sha256"],
                hashlib.sha256(baseline_result).hexdigest(),
            )

            # Temporary evaluation worktrees were removed.
            worktrees = [
                line
                for line in git(
                    repo, "worktree", "list", "--porcelain"
                ).splitlines()
                if line.startswith("worktree ")
            ]
            self.assertEqual(len(worktrees), 1)

            with self.assertRaisesRegex(PairRunError, "append-only"):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=output,
                )

    def test_repeat_index_is_a_replicate_not_execution_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root)
            spec = root / "pair-spec.json"
            self._spec(
                spec,
                revision=revision,
                adapter=adapter,
                repeat_index=1,
                pair_id="fixture-pair-r1",
            )

            bundle = run_pair(
                spec_path=spec,
                source_checkout=repo,
                output_root=root / "runs",
            )
            self.assertEqual(bundle["pairing"]["repeat_index"], 1)
            self.assertEqual(
                bundle["execution_order"], ["baseline", "showmewhy"]
            )
            self.assertEqual(bundle["task_execution_count"], 1)

    def test_verifier_workspace_modification_invalidates_pair(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root, mutate_verifier=True)
            spec = root / "pair-spec.json"
            self._spec(
                spec,
                revision=revision,
                adapter=adapter,
                pair_id="mutating-verifier",
            )
            output = root / "runs"

            with self.assertRaisesRegex(
                PairRunError, "verification modified"
            ):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=output,
                )

            bundle = json.loads(
                (
                    output / "mutating-verifier" / "pair.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(bundle["pair_status"], "invalid")
            self.assertEqual(
                bundle["workspace_equivalence"]["post_verification"],
                "modified",
            )

    def test_execution_spec_rejects_oracle_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root)
            spec = root / "pair-spec.json"
            data = self._spec(
                spec, revision=revision, adapter=adapter
            )
            data["ground_truth"] = {"failing_claim_ids": ["secret"]}
            spec.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(PairRunError, "forbidden"):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=root / "runs",
                )

    def test_prompt_hash_must_match_exact_prompt_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root)
            spec = root / "pair-spec.json"
            data = self._spec(
                spec, revision=revision, adapter=adapter
            )
            data["task_prompt_sha256"] = "0" * 64
            spec.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(PairRunError, "does not match"):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=root / "runs",
                )

    def test_baseline_failure_persists_invalid_bundle_without_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root, fail_baseline=True)
            spec = root / "pair-spec.json"
            self._spec(
                spec,
                revision=revision,
                adapter=adapter,
                pair_id="invalid-pair",
            )
            output = root / "runs"

            with self.assertRaisesRegex(
                PairRunError, "baseline task execution is invalid"
            ):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=output,
                )

            bundle = json.loads(
                (
                    output / "invalid-pair" / "pair.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(bundle["pair_status"], "invalid")
            self.assertEqual(
                bundle["conditions"]["baseline"]["return_code"], 7
            )
            self.assertNotIn("showmewhy", bundle["conditions"])


if __name__ == "__main__":
    unittest.main()
