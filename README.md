# ShowMeWhy

**Don't tell me everything. Show me why.**

ShowMeWhy turns verbose agent output into a concise, evidence-backed receipt: **what happened, why it is justified, what could change the conclusion, and what it cost**.

```text
/showmewhy
```

## Install

### Claude Code plugin

```text
/plugin marketplace add vishnu-77/showmewhy
/plugin install showmewhy@showmewhy
```

Then invoke:

```text
/showmewhy
```

The repository is private during preview, so the local Git/GitHub environment must have access.

### Agent Skill only

```bash
npx skills add vishnu-77/showmewhy --skill showmewhy
```

The Skill-only install provides the ShowMeWhy Receipt. The Claude plugin additionally enables the optional local runtime hook.

## A ShowMeWhy Receipt

```text
AUTH REGRESSION

5 / 428 tests failed.

WHY

middleware changed
      ↓
validation skipped
      ↓
expired session accepted
      ↓
5 authentication tests failed

MONITOR
Evidence  tests/auth.spec.ts::rejects_expired_session — FAIL before, PASS after
Guard     CI must keep `rejects_expired_session` green
Risk      MEDIUM
Budget    1,600 / 2,000 tokens · REWARDED

────────────────────────────────
ShowMeWhy · ~184 / 300 tokens · ↓72%
```

The Why view is **observable provenance, not private chain-of-thought**. ShowMeWhy separates observations, evidence, inference, conclusions and caveats; correlation is not promoted to causation without support.

## Response budgets

| Invocation | Soft budget |
|---|---:|
| `/showmewhy short` | 150 tokens |
| `/showmewhy` | 300 tokens |
| `/showmewhy visual` | 350 tokens |
| `/showmewhy why` | 450 tokens |
| `/showmewhy deep` | 700 tokens |

Correctness and material caveats override compression.

## Risk / reward monitor

For substantive conclusions, the receipt can include one independently checkable evidence line and one recurrence guard.

| State | Requirement | Next-task band |
|---|---|---:|
| `REWARDED` | verified evidence + concrete guard | 1,200–2,000 |
| `CONSTRAINED` | unverified evidence or missing guard | 800–1,800 |

The guard says **how recurrence is detected**. It does not claim the failure can never happen again.

## V2 runtime: context compression

When installed as a Claude Code plugin, ShowMeWhy can intercept verbose `Bash` `PostToolUse` results before they enter subsequent agent context.

```text
verbose Bash result
       │
       ├──────→ retained raw evidence
       │
       ▼
deterministic digest
       │
       ▼
agent context
```

V2 deliberately intercepts **Bash only** by default. Short and unsupported outputs pass through unchanged. Raw output is stored before replacement and Bash response structure/stderr are preserved.

Runtime state stays local under `.showmewhy/`, which is Git-ignored.

Shadow mode:

```bash
SHOWMEWHY_MODE=shadow
```

Manual target override:

```bash
SHOWMEWHY_CONTEXT_BUDGET_TOKENS=900
```

## V3 provenance: prove the receipt

Each compressed run can produce a typed provenance graph with stable local evidence addresses:

```text
evidence://sha256/<digest>#tool_response
run://<run-id>#summary
run://<run-id>#findings/<n>
run://<run-id>#status
```

Relationships include `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `OBSERVED_IN`, `VERIFIED_BY`, `CORRELATED_WITH`, and `CAUSED_BY`.

`CAUSED_BY` is rejected unless an explicit causal basis exists.

Inspect locally:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli provenance <run-id>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli compare <before-run> <after-run>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli view <run-id> --out provenance.html
```

## V4 adaptive policy: compress only when evidence supports it

ShowMeWhy adapts its context target from local outcome metrics:

- **700 tokens** — baseline while evidence is limited;
- **500 tokens** — only after repeated low-reopen, high-completeness runs with useful compression;
- **1,100 tokens** — when raw evidence is frequently reopened or parser completeness falls;
- **shadow / 1,200 tokens** — sticky safety lock after any reported material information loss.

Feedback is explicit:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli feedback <run-id> \
  --reopened no \
  --material-loss no
```

Inspect policy:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli policy
```

Clear a safety lock only after review:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli policy-unlock
```

Adaptive feedback stores only run IDs and operational metrics such as reopen state, parser completeness and compression percentage. It does **not** store task solutions, code, summaries or raw evidence in the policy log.

## Token and CO₂e accounting

ShowMeWhy distinguishes two claims:

- **presentation reduction** — shorter text after material already exists;
- **context avoided** — tokens actually prevented from entering subsequent model context by the runtime hook.

Only the second can support a modelled **operational CO₂e avoided** estimate. Carbon estimates use explicit energy/PUE/carbon-intensity assumptions; no fixed token-to-tree conversion is claimed.

See [`skills/showmewhy/references/impact-methodology.md`](skills/showmewhy/references/impact-methodology.md).

## Machine-readable receipt

```text
/showmewhy json
```

The receipt schema lives at [`skills/showmewhy/references/showmewhy-receipt.schema.json`](skills/showmewhy/references/showmewhy-receipt.schema.json).

## Development

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

Development flows through `feature/*` → `develop` → `release/*` → `main`.

## Security

See [`SECURITY.md`](SECURITY.md). Raw runtime evidence remains local unless the user explicitly moves or shares it.

## Licence

MIT. See [`LICENSE`](LICENSE).
