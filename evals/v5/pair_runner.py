from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PairRunError(RuntimeError):
    pass


FORBIDDEN_EXECUTION_KEYS = {
    "ground_truth",
    "oracle_refs",
    "failing_claim_ids",
    "human_review_claim_ids",
    "counterexample_ids",
    "accepted_fix_revision",
    "expected_pre_fix",
    "expected_post_fix",
}

ESSENTIAL_ENV = (
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SystemRoot",
    "COMSPEC",
    "PATHEXT",
    "LANG",
    "LC_ALL",
    "TERM",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "CLAUDE_CONFIG_DIR",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_OAUTH_TOKEN",
)

PAIR_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SHOWMEWHY_REPO = Path(__file__).resolve().parents[2]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _expand_argv(argv: list[str]) -> list[str]:
    replacements = {
        "{python}": os.sys.executable,
        "{showmewhy_repo}": str(SHOWMEWHY_REPO),
    }
    out: list[str] = []
    for arg in argv:
        expanded = arg
        for token, value in replacements.items():
            expanded = expanded.replace(token, value)
        out.append(expanded)
    return out


def _run_git(
    checkout: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(
        ["git", "-C", str(checkout), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    if check and process.returncode != 0:
        output = process.stdout.decode("utf-8", errors="replace")
        raise PairRunError(
            f"git {' '.join(args)} failed ({process.returncode}):\n{output[-8000:]}"
        )
    return process


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_EXECUTION_KEYS:
                raise PairRunError(
                    f"execution spec contains forbidden ground-truth/oracle field {path}.{key}"
                )
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PairRunError(f"{field} must be a non-empty string")
    return value


def _load_spec(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PairRunError("pair spec must be a JSON object")
    _walk_forbidden(data)

    if data.get("version") != "v5-pair-spec-2":
        raise PairRunError("pair spec version must be v5-pair-spec-2")

    for field in (
        "task_id",
        "domain",
        "repository",
        "revision",
        "task_prompt",
        "model",
        "agent_runtime",
        "tool_profile",
    ):
        _require_string(data.get(field), field)

    repeat_index = data.get("repeat_index")
    if (
        not isinstance(repeat_index, int)
        or isinstance(repeat_index, bool)
        or repeat_index < 0
    ):
        raise PairRunError("repeat_index must be a non-negative integer")

    command = data.get("command")
    if not isinstance(command, dict):
        raise PairRunError("command must be an object")
    argv = command.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or any(not isinstance(arg, str) or not arg for arg in argv)
    ):
        raise PairRunError("command.argv must be a non-empty list of non-empty strings")

    timeout_seconds = command.get("timeout_seconds", 3600)
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or timeout_seconds <= 0
    ):
        raise PairRunError("command.timeout_seconds must be a positive integer")

    pass_env = command.get("pass_env", [])
    if (
        not isinstance(pass_env, list)
        or any(not isinstance(name, str) or not name for name in pass_env)
        or len(pass_env) != len(set(pass_env))
    ):
        raise PairRunError(
            "command.pass_env must be a unique list of environment-variable names"
        )

    prompt_hash = _sha256_text(data["task_prompt"])
    expected_hash = data.get("task_prompt_sha256")
    if expected_hash is not None:
        if not isinstance(expected_hash, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_hash
        ):
            raise PairRunError(
                "task_prompt_sha256 must be a lowercase SHA-256 digest"
            )
        if expected_hash != prompt_hash:
            raise PairRunError("task_prompt_sha256 does not match task_prompt bytes")

    pair_id = data.get("pair_id")
    if pair_id is not None:
        _require_string(pair_id, "pair_id")
        if not PAIR_ID_RE.fullmatch(pair_id):
            raise PairRunError(
                "pair_id may contain only letters, numbers, dot, underscore and dash"
            )

    allowed_top = {
        "version",
        "task_id",
        "domain",
        "repository",
        "revision",
        "task_prompt",
        "task_prompt_sha256",
        "model",
        "agent_runtime",
        "tool_profile",
        "repeat_index",
        "pair_id",
        "command",
    }
    unknown = set(data) - allowed_top
    if unknown:
        raise PairRunError(
            f"unknown pair spec fields: {', '.join(sorted(unknown))}"
        )

    allowed_command = {"argv", "timeout_seconds", "pass_env"}
    unknown_command = set(command) - allowed_command
    if unknown_command:
        raise PairRunError(
            f"unknown command fields: {', '.join(sorted(unknown_command))}"
        )
    return data


def _derive_pair_id(spec: dict[str, Any], prompt_hash: str) -> str:
    explicit = spec.get("pair_id")
    if explicit:
        return explicit
    canonical = "\n".join(
        [
            spec["task_id"],
            spec["repository"],
            spec["revision"],
            prompt_hash,
            spec["model"],
            spec["agent_runtime"],
            spec["tool_profile"],
            str(spec["repeat_index"]),
        ]
    )
    suffix = _sha256_text(canonical)[:12]
    safe_task = re.sub(r"[^A-Za-z0-9._-]+", "-", spec["task_id"]).strip("-")
    return f"{safe_task or 'task'}-r{spec['repeat_index']}-{suffix}"


def _build_env(
    *,
    pass_env: list[str],
    condition: str,
    pair_id: str,
    prompt_hash: str,
    prompt_file: Path,
    output_dir: Path,
    workspace: Path,
    spec: dict[str, Any],
    baseline_result_file: Path | None = None,
) -> tuple[dict[str, str], list[str]]:
    env: dict[str, str] = {}
    inherited_names: set[str] = set()
    for name in ESSENTIAL_ENV:
        if name in os.environ:
            env[name] = os.environ[name]
            inherited_names.add(name)

    missing: list[str] = []
    for name in pass_env:
        if name not in os.environ:
            missing.append(name)
        else:
            env[name] = os.environ[name]
            inherited_names.add(name)
    if missing:
        raise PairRunError(
            "requested pass_env variables are missing: "
            + ", ".join(sorted(missing))
        )

    env.update(
        {
            "SHOWMEWHY_V5_CONDITION": condition,
            "SHOWMEWHY_V5_PAIR_ID": pair_id,
            "SHOWMEWHY_V5_PROMPT_SHA256": prompt_hash,
            "SHOWMEWHY_V5_PROMPT_FILE": str(prompt_file),
            "SHOWMEWHY_V5_OUTPUT_DIR": str(output_dir),
            "SHOWMEWHY_V5_WORKSPACE": str(workspace),
            "SHOWMEWHY_V5_MODEL": spec["model"],
            "SHOWMEWHY_V5_AGENT_RUNTIME": spec["agent_runtime"],
            "SHOWMEWHY_V5_TOOL_PROFILE": spec["tool_profile"],
        }
    )
    if baseline_result_file is not None:
        env["SHOWMEWHY_V5_BASE_RESULT_FILE"] = str(baseline_result_file)
    return env, sorted(inherited_names)


def _write_bytes(path: Path, data: bytes) -> dict[str, Any]:
    path.write_bytes(data)
    return {
        "path": path.name,
        "sha256": _sha256_bytes(data),
        "bytes": len(data),
        "lines": data.count(b"\n")
        + (1 if data and not data.endswith(b"\n") else 0),
    }


def _snapshot_patch(workspace: Path, start_revision: str) -> bytes:
    """Snapshot all Git-visible worktree content without mutating the real index."""

    index_text = (
        _run_git(workspace, "rev-parse", "--git-path", "index")
        .stdout.decode("utf-8", errors="replace")
        .strip()
    )
    index_path = Path(index_text)
    if not index_path.is_absolute():
        index_path = (workspace / index_path).resolve()

    fd, temp_name = tempfile.mkstemp(prefix="showmewhy-v5-index-")
    os.close(fd)
    temp_index = Path(temp_name)
    try:
        if index_path.exists():
            shutil.copy2(index_path, temp_index)
        else:
            temp_index.unlink(missing_ok=True)

        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(temp_index)
        _run_git(workspace, "add", "-A", "--", ".", env=env)
        return _run_git(
            workspace,
            "diff",
            "--cached",
            "--binary",
            start_revision,
            "--",
            env=env,
        ).stdout
    finally:
        temp_index.unlink(missing_ok=True)


def _repository_state(
    workspace: Path,
    start_revision: str,
) -> tuple[str, bytes, bytes]:
    final_head = (
        _run_git(workspace, "rev-parse", "HEAD")
        .stdout.decode("utf-8", errors="replace")
        .strip()
    )
    status = _run_git(
        workspace, "status", "--porcelain=v1", "--untracked-files=all"
    ).stdout
    patch = _snapshot_patch(workspace, start_revision)
    return final_head, status, patch


def _state_fingerprint(
    final_head: str,
    status: bytes,
    patch: bytes,
) -> str:
    canonical = (
        final_head.encode("utf-8")
        + b"\0"
        + status
        + b"\0"
        + patch
    )
    return _sha256_bytes(canonical)


def _git_snapshot(
    workspace: Path,
    start_revision: str,
    output_dir: Path,
) -> dict[str, Any]:
    final_head, status, patch = _repository_state(
        workspace, start_revision
    )
    changed_files = []
    for line in status.decode("utf-8", errors="replace").splitlines():
        if len(line) >= 4:
            changed_files.append(line[3:])

    return {
        "start_revision": start_revision,
        "final_head": final_head,
        "state_sha256": _state_fingerprint(
            final_head, status, patch
        ),
        "status": _write_bytes(output_dir / "workspace.status", status),
        "diff": _write_bytes(output_dir / "workspace.diff", patch),
        "changed_files": changed_files,
    }


def _run_condition(
    *,
    condition: str,
    workspace: Path,
    output_dir: Path,
    prompt_file: Path,
    prompt_hash: str,
    pair_id: str,
    spec: dict[str, Any],
    baseline_result_file: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    command = spec["command"]
    argv = _expand_argv(list(command["argv"]))
    timeout_seconds = int(command.get("timeout_seconds", 3600))
    env, inherited_names = _build_env(
        pass_env=list(command.get("pass_env", [])),
        condition=condition,
        pair_id=pair_id,
        prompt_hash=prompt_hash,
        prompt_file=prompt_file,
        output_dir=output_dir,
        workspace=workspace,
        spec=spec,
        baseline_result_file=baseline_result_file,
    )

    started_wall = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    timed_out = False
    try:
        process = subprocess.run(
            argv,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        return_code = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = None
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""

    seconds = round(time.monotonic() - started, 3)
    stdout_meta = _write_bytes(output_dir / "stdout.log", stdout)
    stderr_meta = _write_bytes(output_dir / "stderr.log", stderr)
    git_meta = _git_snapshot(workspace, spec["revision"], output_dir)

    adapter_artifacts = sorted(
        p.name
        for p in output_dir.iterdir()
        if p.is_file()
        and p.name
        not in {"stdout.log", "stderr.log", "workspace.status", "workspace.diff"}
    )

    return {
        "condition": condition,
        "role": (
            "task-agent-result"
            if condition == "baseline"
            else "posthoc-verification"
        ),
        "status": (
            "valid" if return_code == 0 and not timed_out else "invalid"
        ),
        "started_at": started_wall,
        "seconds": seconds,
        "return_code": return_code,
        "timed_out": timed_out,
        "stdout": stdout_meta,
        "stderr": stderr_meta,
        "git": git_meta,
        "adapter_artifacts": adapter_artifacts,
        "environment": {
            "mode": "minimal-plus-auth-env",
            "inherited_names": inherited_names,
            "condition_variable": "SHOWMEWHY_V5_CONDITION",
        },
    }


def _add_worktree(source: Path, destination: Path, revision: str) -> None:
    _run_git(source, "cat-file", "-e", f"{revision}^{{commit}}")
    process = _run_git(
        source,
        "worktree",
        "add",
        "--detach",
        str(destination),
        revision,
        check=False,
    )
    if process.returncode != 0:
        output = process.stdout.decode("utf-8", errors="replace")
        raise PairRunError(
            f"failed to create worktree: {output[-8000:]}"
        )
    actual = (
        _run_git(destination, "rev-parse", "HEAD")
        .stdout.decode("utf-8", errors="replace")
        .strip()
    )
    if actual != revision:
        raise PairRunError(
            f"worktree revision mismatch: expected {revision}, got {actual}"
        )


def _remove_worktree(source: Path, destination: Path) -> None:
    _run_git(
        source,
        "worktree",
        "remove",
        "--force",
        str(destination),
        check=False,
    )
    shutil.rmtree(destination, ignore_errors=True)


def run_pair(
    *,
    spec_path: Path,
    source_checkout: Path,
    output_root: Path,
    keep_worktrees: bool = False,
) -> dict[str, Any]:
    spec = _load_spec(spec_path)
    source_checkout = source_checkout.resolve()
    output_root = output_root.resolve()

    probe = _run_git(
        source_checkout, "rev-parse", "--show-toplevel", check=False
    )
    if probe.returncode != 0:
        raise PairRunError(
            f"source checkout is not a Git working tree: {source_checkout}"
        )

    prompt_bytes = spec["task_prompt"].encode("utf-8")
    prompt_hash = _sha256_bytes(prompt_bytes)
    pair_id = _derive_pair_id(spec, prompt_hash)
    pair_dir = output_root / pair_id
    if pair_dir.exists():
        raise PairRunError(
            f"pair output already exists: {pair_dir}. "
            "Use a new repeat_index/pair_id; evidence is append-only."
        )
    pair_dir.mkdir(parents=True, exist_ok=False)
    prompt_file = pair_dir / "task.prompt.txt"
    prompt_file.write_bytes(prompt_bytes)

    resolved_argv = _expand_argv(list(spec["command"]["argv"]))
    argv_canonical = json.dumps(
        resolved_argv, separators=(",", ":"), ensure_ascii=False
    )

    bundle: dict[str, Any] = {
        "version": "v5-pair-run-2",
        "design": "single-task-posthoc-verification",
        "pair_status": "running",
        "task_id": spec["task_id"],
        "domain": spec["domain"],
        "pairing": {
            "pair_id": pair_id,
            "repository": spec["repository"],
            "revision": spec["revision"],
            "task_prompt_sha256": prompt_hash,
            "model": spec["model"],
            "agent_runtime": spec["agent_runtime"],
            "tool_profile": spec["tool_profile"],
            "repeat_index": spec["repeat_index"],
        },
        "task_prompt": {
            "path": prompt_file.name,
            "sha256": prompt_hash,
            "bytes": len(prompt_bytes),
        },
        "execution_order": ["baseline", "showmewhy"],
        "task_execution_count": 1,
        "command": {
            "argv_template": spec["command"]["argv"],
            "argv": resolved_argv,
            "argv_sha256": _sha256_text(argv_canonical),
            "timeout_seconds": spec["command"].get(
                "timeout_seconds", 3600
            ),
            "pass_env_names": spec["command"].get("pass_env", []),
        },
        "conditions": {},
        "workspace_equivalence": {
            "pre_verification": "not_checked",
            "post_verification": "not_checked",
        },
        "ground_truth_present": False,
    }
    bundle_path = pair_dir / "pair.json"
    bundle_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    worktree_root = Path(
        tempfile.mkdtemp(prefix=f"showmewhy-v5-{pair_id}-")
    )
    workspace = worktree_root / "task"

    try:
        _add_worktree(source_checkout, workspace, spec["revision"])

        baseline = _run_condition(
            condition="baseline",
            workspace=workspace,
            output_dir=pair_dir / "baseline",
            prompt_file=prompt_file,
            prompt_hash=prompt_hash,
            pair_id=pair_id,
            spec=spec,
        )
        bundle["conditions"]["baseline"] = baseline
        bundle_path.write_text(
            json.dumps(bundle, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if baseline["status"] != "valid":
            bundle["pair_status"] = "invalid"
            bundle_path.write_text(
                json.dumps(bundle, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise PairRunError(
                f"baseline task execution is invalid; inspect {bundle_path}"
            )

        baseline_result = pair_dir / "baseline" / "result.txt"
        if not baseline_result.is_file() or not baseline_result.read_text(
            encoding="utf-8"
        ).strip():
            bundle["pair_status"] = "invalid"
            bundle_path.write_text(
                json.dumps(bundle, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise PairRunError(
                "baseline adapter did not persist a non-empty result.txt"
            )

        baseline_state_hash = baseline["git"]["state_sha256"]
        pre_head, pre_status, pre_patch = _repository_state(
            workspace, spec["revision"]
        )
        if (
            _state_fingerprint(
                pre_head, pre_status, pre_patch
            )
            != baseline_state_hash
        ):
            bundle["workspace_equivalence"][
                "pre_verification"
            ] = "mismatch"
            bundle["pair_status"] = "invalid"
            bundle_path.write_text(
                json.dumps(bundle, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise PairRunError(
                "completed workspace changed between task execution and verification"
            )
        bundle["workspace_equivalence"][
            "pre_verification"
        ] = "identical"

        showmewhy = _run_condition(
            condition="showmewhy",
            workspace=workspace,
            output_dir=pair_dir / "showmewhy",
            prompt_file=prompt_file,
            prompt_hash=prompt_hash,
            pair_id=pair_id,
            spec=spec,
            baseline_result_file=baseline_result,
        )
        bundle["conditions"]["showmewhy"] = showmewhy

        if showmewhy["git"]["state_sha256"] != baseline_state_hash:
            bundle["workspace_equivalence"][
                "post_verification"
            ] = "modified"
            bundle["pair_status"] = "invalid"
            bundle_path.write_text(
                json.dumps(bundle, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise PairRunError(
                "ShowMeWhy verification modified the completed task workspace"
            )

        bundle["workspace_equivalence"][
            "post_verification"
        ] = "identical"
        valid = showmewhy["status"] == "valid"
        bundle["pair_status"] = "valid" if valid else "invalid"
        bundle_path.write_text(
            json.dumps(bundle, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if not valid:
            raise PairRunError(
                f"post-hoc ShowMeWhy verification is invalid; inspect {bundle_path}"
            )
        return bundle
    finally:
        if not keep_worktrees:
            if workspace.exists():
                _remove_worktree(source_checkout, workspace)
            shutil.rmtree(worktree_root, ignore_errors=True)
        else:
            bundle["worktree_root"] = str(worktree_root)
            bundle_path.write_text(
                json.dumps(bundle, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run one V5 task agent, then apply post-hoc ShowMeWhy "
            "verification in the exact same completed workspace without ground truth."
        )
    )
    parser.add_argument(
        "spec", type=Path, help="v5-pair-spec-2 JSON file"
    )
    parser.add_argument(
        "--source-checkout",
        type=Path,
        required=True,
        help="Local Git checkout containing the pinned revision",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where append-only pair evidence is written",
    )
    parser.add_argument(
        "--keep-worktrees",
        action="store_true",
        help=(
            "Keep the temporary task worktree for debugging; its path is "
            "recorded in pair.json"
        ),
    )
    args = parser.parse_args()

    try:
        result = run_pair(
            spec_path=args.spec,
            source_checkout=args.source_checkout,
            output_root=args.output_dir,
            keep_worktrees=args.keep_worktrees,
        )
    except PairRunError as exc:
        print(f"paired execution failed: {exc}", file=os.sys.stderr)
        raise SystemExit(1)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
