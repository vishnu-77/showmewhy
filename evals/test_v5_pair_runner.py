from __future__ import annotations

import hashlib
import json
import os
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

    def _adapter(self, root: Path, *, fail_baseline: bool = False) -> Path:
        adapter = root / ("adapter_fail.py" if fail_baseline else "adapter.py")
        adapter.write_text(
            (
                "import json, os, pathlib, sys\n"
                "condition = os.environ['SHOWMEWHY_V5_CONDITION']\n"
                "workspace = pathlib.Path(os.environ['SHOWMEWHY_V5_WORKSPACE'])\n"
                "out = pathlib.Path(os.environ['SHOWMEWHY_V5_OUTPUT_DIR'])\n"
                "prompt = pathlib.Path(os.environ['SHOWMEWHY_V5_PROMPT_FILE']).read_text()\n"
                "if " + ("condition == 'baseline'" if fail_baseline else "False") + ":\n"
                "    print('forced baseline adapter failure', file=sys.stderr)\n"
                "    raise SystemExit(7)\n"
                "(workspace / 'agent-change.txt').write_text(condition + '\\n')\n"
                "(out / 'adapter.json').write_text(json.dumps({\n"
                "    'condition': condition,\n"
                "    'prompt_sha256': os.environ['SHOWMEWHY_V5_PROMPT_SHA256'],\n"
                "    'prompt': prompt,\n"
                "}, sort_keys=True))\n"
                "print('condition=' + condition)\n"
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
            "version": "v5-pair-spec-1",
            "task_id": "fixture-task",
            "domain": "code",
            "repository": "fixture/local",
            "revision": revision,
            "task_prompt": prompt,
            "task_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "model": "fixture-model",
            "agent_runtime": "fixture-agent",
            "tool_profile": "fixture-tools",
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

    def test_pair_isolated_ground_truth_blind_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root)
            spec = root / "pair-spec.json"
            self._spec(spec, revision=revision, adapter=adapter, pair_id="fixture-pair")
            output = root / "runs"

            bundle = run_pair(
                spec_path=spec,
                source_checkout=repo,
                output_root=output,
            )

            self.assertEqual(bundle["pair_status"], "valid")
            self.assertFalse(bundle["ground_truth_present"])
            self.assertEqual(bundle["execution_order"], ["baseline", "showmewhy"])
            self.assertEqual(bundle["pairing"]["revision"], revision)
            self.assertEqual(
                bundle["conditions"]["baseline"]["git"]["start_revision"], revision
            )
            self.assertEqual(
                bundle["conditions"]["showmewhy"]["git"]["start_revision"], revision
            )
            self.assertEqual(bundle["conditions"]["baseline"]["return_code"], 0)
            self.assertEqual(bundle["conditions"]["showmewhy"]["return_code"], 0)
            self.assertIn(
                "agent-change.txt",
                bundle["conditions"]["baseline"]["git"]["changed_files"],
            )
            self.assertIn(
                "agent-change.txt",
                bundle["conditions"]["showmewhy"]["git"]["changed_files"],
            )
            self.assertNotEqual(
                bundle["conditions"]["baseline"]["git"]["diff"]["sha256"],
                bundle["conditions"]["showmewhy"]["git"]["diff"]["sha256"],
            )

            pair_dir = output / "fixture-pair"
            baseline_adapter = json.loads(
                (pair_dir / "baseline" / "adapter.json").read_text(encoding="utf-8")
            )
            showmewhy_adapter = json.loads(
                (pair_dir / "showmewhy" / "adapter.json").read_text(encoding="utf-8")
            )
            self.assertEqual(baseline_adapter["condition"], "baseline")
            self.assertEqual(showmewhy_adapter["condition"], "showmewhy")
            self.assertEqual(
                baseline_adapter["prompt_sha256"],
                showmewhy_adapter["prompt_sha256"],
            )
            self.assertEqual(len(git(repo, "worktree", "list", "--porcelain").split("worktree ")), 2)

            with self.assertRaisesRegex(PairRunError, "append-only"):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=output,
                )

    def test_repeat_index_counterbalances_execution_order(self) -> None:
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
            self.assertEqual(bundle["execution_order"], ["showmewhy", "baseline"])

    def test_execution_spec_rejects_oracle_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root)
            spec = root / "pair-spec.json"
            data = self._spec(spec, revision=revision, adapter=adapter)
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
            data = self._spec(spec, revision=revision, adapter=adapter)
            data["task_prompt_sha256"] = "0" * 64
            spec.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(PairRunError, "does not match"):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=root / "runs",
                )

    def test_partial_condition_failure_persists_invalid_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo, revision = self._repo(root)
            adapter = self._adapter(root, fail_baseline=True)
            spec = root / "pair-spec.json"
            self._spec(spec, revision=revision, adapter=adapter, pair_id="invalid-pair")
            output = root / "runs"

            with self.assertRaisesRegex(PairRunError, "paired execution is invalid"):
                run_pair(
                    spec_path=spec,
                    source_checkout=repo,
                    output_root=output,
                )

            bundle = json.loads(
                (output / "invalid-pair" / "pair.json").read_text(encoding="utf-8")
            )
            self.assertEqual(bundle["pair_status"], "invalid")
            self.assertEqual(bundle["conditions"]["baseline"]["return_code"], 7)
            self.assertEqual(bundle["conditions"]["showmewhy"]["return_code"], 0)


if __name__ == "__main__":
    unittest.main()
