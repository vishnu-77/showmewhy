# ShowMeWhy runtime

The runtime is optional and local. The `/showmewhy` Skill works without it.

## Context compression

Claude Code `Bash` results above the active context target can be compacted after raw output is stored under `.showmewhy/evidence/`. Unsupported or short output fails open.

## Provenance

Compressed runs produce execution digests and typed provenance graphs under `.showmewhy/runs/` and `.showmewhy/provenance/`.

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
