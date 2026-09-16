# ShowMeWhy runtime

The runtime is optional and local to the user's machine. The `/showmewhy` Skill works without it.

## Storage

ShowMeWhy does **not** create runtime folders inside consumer repositories.

Runtime evidence and policy state are stored in an OS-appropriate global state directory, partitioned by a stable project namespace:

```text
macOS   ~/Library/Application Support/ShowMeWhy/projects/<project>-<hash>/
Linux   $XDG_STATE_HOME/showmewhy/projects/<project>-<hash>/
        or ~/.local/state/showmewhy/projects/<project>-<hash>/
Windows %LOCALAPPDATA%\ShowMeWhy\projects\<project>-<hash>\
```

Set `SHOWMEWHY_HOME` to override the global state root, for example in CI or when state should live on a separate volume.

A git repository root is the project boundary, including worktrees where `.git` is a file. Running Claude from different subdirectories of the same repository therefore uses the same ShowMeWhy state. Outside git, the working directory itself is the boundary.

This keeps `git status` clean: ShowMeWhy does not require `.gitignore` changes in projects that use it.

## Context compression

Claude Code `Bash` results above the active context target can be compacted after raw output is stored under the project's global `evidence/` namespace. Unsupported or short output fails open.

## Provenance

Compressed runs produce execution digests and typed provenance graphs under the same global project namespace in `runs/` and `provenance/`.

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli provenance <run-id>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli compare <before> <after>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli view <run-id> --out provenance.html
```

## Adaptive policy

V4 uses feedback metrics only. It never copies run summaries, findings, code or raw tool output into the policy log.

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli feedback <run-id> --reopened no --material-loss no
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli policy
```

Policy bands:

| Condition | Mode | Target |
|---|---|---:|
| fewer than 3 feedback samples | replace | 700 |
| low reopen + ≥90% complete + useful compression | replace | 500 |
| reopen ≥35% or completeness <75% | replace | 1,100 |
| any reported material loss | shadow | 1,200 |

Material loss creates a sticky safety lock. It can only be cleared explicitly:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli policy-unlock
```

Explicit `SHOWMEWHY_MODE` and `SHOWMEWHY_CONTEXT_BUDGET_TOKENS` values override the adaptive recommendation.
