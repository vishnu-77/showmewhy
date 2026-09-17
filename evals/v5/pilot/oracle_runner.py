from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class OracleValidationError(RuntimeError):
    pass


def _run(
    args: list[str] | str,
    *,
    cwd: Path,
    shell: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        args,
        cwd=cwd,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    if check and process.returncode != 0:
        rendered = args if isinstance(args, str) else shlex.join(args)
        raise OracleValidationError(
            f"command failed ({process.returncode}): {rendered}\n{process.stdout[-8000:]}"
        )
    return process


def _load_task(manifest_path: Path, task_id: str) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [task for task in manifest.get("tasks", []) if task.get("task_id") == task_id]
    if len(matches) != 1:
        raise OracleValidationError(f"expected exactly one task named {task_id!r}")
    task = matches[0]
    if task.get("selection_status") != "selected_unexecuted":
        raise OracleValidationError("oracle validation only accepts selected_unexecuted tasks")
    if task.get("execution_status") != "not_run":
        raise OracleValidationError("selection manifest must not claim benchmark execution")
    return task


def _write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate_oracle(
    *,
    manifest_path: Path,
    task_id: str,
    workspace: Path,
    result_path: Path,
) -> dict[str, Any]:
    task = _load_task(manifest_path, task_id)
    workspace = workspace.resolve()
    if not (workspace / ".git").exists():
        raise OracleValidationError(f"workspace is not a git checkout: {workspace}")

    base = task["pre_fix_revision"]
    accepted = task["accepted_fix_revision"]
    pr_number = int(task["pr_number"])
    test_paths = list(task["upstream_test_paths"])
    command = str(task["reproducer_command"])

    _run(["git", "fetch", "origin", base, accepted], cwd=workspace)
    pull_ref = f"refs/pull/{pr_number}/head"
    _run(["git", "fetch", "origin", f"{pull_ref}:refs/remotes/origin/showmewhy-pilot-head"], cwd=workspace)
    pr_head = _run(["git", "rev-parse", "refs/remotes/origin/showmewhy-pilot-head"], cwd=workspace).stdout.strip()

    patch = _run(
        ["git", "diff", "--binary", base, pr_head, "--", *test_paths],
        cwd=workspace,
    ).stdout
    if not patch.strip():
        raise OracleValidationError("accepted PR head contains no test-path diff for this pilot task")
    patch_sha256 = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    patch_path = result_path.parent / f"{task_id}.test-oracle.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(patch, encoding="utf-8")

    result: dict[str, Any] = {
        "version": "v5-pilot-oracle-1",
        "task_id": task_id,
        "repository": task["repository"],
        "pr_number": pr_number,
        "pre_fix_revision": base,
        "accepted_fix_revision": accepted,
        "accepted_pr_head": pr_head,
        "test_patch_sha256": patch_sha256,
        "test_paths": test_paths,
        "reproducer_command": command,
        "pre_fix": {"status": "not_run"},
        "accepted_fix": {"status": "not_run"},
        "oracle_validated": False,
    }
    _write_result(result_path, result)

    _run(["git", "reset", "--hard"], cwd=workspace)
    _run(["git", "clean", "-fdx"], cwd=workspace)
    _run(["git", "checkout", "--detach", base], cwd=workspace)
    _run(["git", "apply", "--check", str(patch_path)], cwd=workspace)
    _run(["git", "apply", str(patch_path)], cwd=workspace)

    started = time.monotonic()
    pre = _run(command, cwd=workspace, shell=True, check=False)
    pre_seconds = round(time.monotonic() - started, 3)
    result["pre_fix"] = {
        "status": "expected_failure" if pre.returncode != 0 else "unexpected_pass",
        "return_code": pre.returncode,
        "seconds": pre_seconds,
        "output_tail": pre.stdout[-12000:],
    }
    _write_result(result_path, result)
    if pre.returncode == 0:
        raise OracleValidationError(
            "pre-fix checkout passed the accepted regression test; task is not a valid failing oracle"
        )

    _run(["git", "reset", "--hard"], cwd=workspace)
    _run(["git", "clean", "-fdx"], cwd=workspace)
    _run(["git", "checkout", "--detach", accepted], cwd=workspace)

    started = time.monotonic()
    fixed = _run(command, cwd=workspace, shell=True, check=False)
    fixed_seconds = round(time.monotonic() - started, 3)
    result["accepted_fix"] = {
        "status": "pass" if fixed.returncode == 0 else "failure",
        "return_code": fixed.returncode,
        "seconds": fixed_seconds,
        "output_tail": fixed.stdout[-12000:],
    }
    result["oracle_validated"] = pre.returncode != 0 and fixed.returncode == 0
    _write_result(result_path, result)

    if fixed.returncode != 0:
        raise OracleValidationError(
            "accepted-fix checkout did not pass the same regression command; oracle is not reproducible"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate one V5 pilot oracle by requiring regression-test failure before the fix and pass after it."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = validate_oracle(
            manifest_path=args.manifest,
            task_id=args.task_id,
            workspace=args.workspace,
            result_path=args.result,
        )
    except OracleValidationError as exc:
        print(f"oracle validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
