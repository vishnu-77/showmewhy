from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "evals" / "v5" / "pilot"
sys.path.insert(0, str(PILOT))

from oracle_runner import OracleValidationError, validate_oracle


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


class V5OracleRunnerTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, str, str]:
        origin = root / "origin.git"
        author = root / "author"
        subject = root / "subject"
        origin.mkdir()
        author.mkdir()
        git(origin, "init", "--bare")
        git(author, "init")
        git(author, "config", "user.name", "V5 Test")
        git(author, "config", "user.email", "v5@example.invalid")

        (author / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        git(author, "add", "app.py")
        git(author, "commit", "-m", "base")
        base = git(author, "rev-parse", "HEAD")

        (author / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        (author / "test_behavior.py").write_text(
            "from app import VALUE\nassert VALUE == 2, f'expected 2, got {VALUE}'\n",
            encoding="utf-8",
        )
        git(author, "add", "app.py", "test_behavior.py")
        git(author, "commit", "-m", "accepted fix")
        accepted = git(author, "rev-parse", "HEAD")

        git(author, "remote", "add", "origin", str(origin))
        git(author, "push", "origin", f"{accepted}:refs/heads/main")
        git(author, "push", "origin", f"{accepted}:refs/pull/1/head")
        git(root, "clone", str(origin), str(subject))
        git(subject, "checkout", "--detach", base)
        return origin, subject, base, accepted

    def _manifest(self, path: Path, *, base: str, accepted: str) -> None:
        path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "task_id": "fixture-task",
                            "repository": "fixture/local",
                            "pr_number": 1,
                            "pre_fix_revision": base,
                            "accepted_fix_revision": accepted,
                            "upstream_test_paths": ["test_behavior.py"],
                            "reproducer_command": f"{sys.executable} test_behavior.py",
                            "selection_status": "selected_unexecuted",
                            "execution_status": "not_run",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_runner_requires_pre_fix_failure_and_accepted_fix_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, subject, base, accepted = self._fixture(root)
            manifest = root / "manifest.json"
            result_path = root / "evidence" / "result.json"
            self._manifest(manifest, base=base, accepted=accepted)

            result = validate_oracle(
                manifest_path=manifest,
                task_id="fixture-task",
                workspace=subject,
                result_path=result_path,
                pre_fix_allowed_return_codes={1},
            )

            self.assertTrue(result["oracle_validated"])
            self.assertEqual(result["pre_fix"]["status"], "expected_failure")
            self.assertNotEqual(result["pre_fix"]["return_code"], 0)
            self.assertEqual(result["accepted_fix"]["status"], "pass")
            self.assertEqual(result["accepted_fix"]["return_code"], 0)
            self.assertEqual(len(result["test_patch_sha256"]), 64)
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertTrue(persisted["oracle_validated"])


    def test_runner_rejects_non_oracle_failure_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, subject, base, accepted = self._fixture(root)
            manifest = root / "manifest.json"
            result_path = root / "evidence" / "result.json"
            self._manifest(manifest, base=base, accepted=accepted)

            with self.assertRaisesRegex(
                OracleValidationError, "non-oracle exit code"
            ):
                validate_oracle(
                    manifest_path=manifest,
                    task_id="fixture-task",
                    workspace=subject,
                    result_path=result_path,
                    pre_fix_allowed_return_codes={2},
                )

            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["pre_fix"]["status"], "invalid_failure")
            self.assertFalse(persisted["oracle_validated"])

    def test_execution_prefix_wraps_manifest_reproducer(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, subject, base, accepted = self._fixture(root)
            manifest = root / "manifest.json"
            result_path = root / "evidence" / "result.json"
            self._manifest(manifest, base=base, accepted=accepted)

            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["tasks"][0]["reproducer_command"] = "test_behavior"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            prefix = f"{subprocess.list2cmdline([sys.executable])} -m"

            result = validate_oracle(
                manifest_path=manifest,
                task_id="fixture-task",
                workspace=subject,
                result_path=result_path,
                execution_prefix=prefix,
                pre_fix_allowed_return_codes={1},
            )

            self.assertTrue(result["oracle_validated"])
            self.assertEqual(result["execution_prefix"], prefix)
            self.assertEqual(
                result["effective_reproducer_command"], f"{prefix} test_behavior"
            )

    def test_result_evidence_must_live_outside_subject_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, subject, base, accepted = self._fixture(root)
            manifest = root / "manifest.json"
            self._manifest(manifest, base=base, accepted=accepted)

            with self.assertRaisesRegex(OracleValidationError, "outside the subject checkout"):
                validate_oracle(
                    manifest_path=manifest,
                    task_id="fixture-task",
                    workspace=subject,
                    result_path=subject / "result.json",
                )


if __name__ == "__main__":
    unittest.main()
