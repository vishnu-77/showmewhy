# ShowMeWhy

**Don't tell me everything. Show me why.**

ShowMeWhy is a small Agent Skill that turns verbose AI output into a concise conclusion, the right visual structure, and an evidence-backed explanation.

```text
/showmewhy
```

## What it changes

**Before**

> A long explanation of what the agent inspected, commands it ran, several paragraphs of observations, repeated tool output, and the conclusion near the end.

**After**

```text
AUTH REGRESSION

5 / 428 tests failed.

Cause
Session validation was bypassed after the middleware change.

WHY

middleware changed
      ↓
validation skipped
      ↓
expired session accepted
      ↓
5 authentication tests failed

Confidence: HIGH

MONITOR
Evidence  tests/auth.spec.ts::rejects_expired_session — FAIL before fix, PASS after fix
Guard     CI must keep `rejects_expired_session` green
Risk      MEDIUM
Budget    1,600 / 2,000 tokens · REWARDED

────────────────────────────────
ShowMeWhy · ~184 / 300 tokens · ↓ 72%
Est. operational CO₂e equivalent · ~0.26 g*
```

`*` Low-confidence reference estimate unless a runtime-specific energy profile is supplied. See [impact methodology](skills/showmewhy/references/impact-methodology.md).

## Install

Using the Agent Skills CLI:

```bash
npx skills add vishnu-77/showmewhy --skill showmewhy
```

For Claude Code globally:

```bash
npx skills add vishnu-77/showmewhy --skill showmewhy -g -a claude-code
```

For Codex:

```bash
npx skills add vishnu-77/showmewhy --skill showmewhy -g -a codex
```

> The repository is private during the preview. Your Git credentials must have access to install it directly.

## Use

In Claude Code, invoke the skill explicitly:

```text
/showmewhy
```

You can also give it a target:

```text
/showmewhy why did these tests fail?
/showmewhy compare Redis and PostgreSQL for this design
/showmewhy visual
/showmewhy monitor
/showmewhy short
```

The default output has a **300-token soft budget**. Correctness and material caveats override the budget.

## Output contract

ShowMeWhy uses up to four layers:

1. **Conclusion** — answer first.
2. **Signal** — only the facts that materially matter.
3. **Visual** — a table, tree, timeline, compact bars, or graph when structure is easier to see than read.
4. **Why** — observable evidence connected to the conclusion.

Simple answers stay simple. A visual is not mandatory.

## The Why graph

The Why graph is provenance, not private chain-of-thought.

```text
[OBSERVATION]
401 changed to 200
        │
     SUPPORTS
        ▼
[EVIDENCE]
expired sessions accepted
        │
     SUPPORTS
        ▼
[CONCLUSION]
authentication regression
```

ShowMeWhy separates observations, evidence, inference, conclusions, and caveats. It must not convert correlation into causation without support.

## Risk / reward monitor

For substantive conclusions, ShowMeWhy can add a compact monitor that makes the answer falsifiable and gives the next step a deterministic token envelope:

```text
MONITOR
Evidence  tests/auth.spec.ts::rejects_expired_session — FAIL before fix, PASS after fix
Guard     CI must keep `rejects_expired_session` green
Risk      MEDIUM
Budget    1,600 / 2,000 tokens · REWARDED
```

The evidence line must point to something another developer can check. The guard is the concrete test, invariant, policy, or alert that should detect the same failure class if it returns. It does **not** claim recurrence is impossible.

Budget policy:

| Monitor state | Requirement | Next-task band |
|---|---|---:|
| `REWARDED` | verified evidence + concrete guard | 1,200–2,000 tokens |
| `CONSTRAINED` | unverified evidence or missing guard | 800–1,800 tokens |

Risk selects the point inside the band: LOW favours the upper bound, HIGH the lower bound. V0 reports the recommendation; runtime enforcement belongs to a future hook.

Run the deterministic monitor directly:

```bash
python3 skills/showmewhy/scripts/monitor.py \
  --evidence-verified yes \
  --guard-present yes \
  --risk medium
```

## Token budgets

| Invocation | Soft budget |
|---|---:|
| `/showmewhy short` | 150 tokens |
| `/showmewhy` | 300 tokens |
| `/showmewhy visual` | 350 tokens |
| `/showmewhy why` | 450 tokens |
| `/showmewhy deep` | 700 tokens |

The receipt reports approximate token reduction when exact host usage data is unavailable.

## Impact receipt

ShowMeWhy can include a compact receipt:

```text
────────────────────────────────
ShowMeWhy · ~126 / 300 tokens · ↓ 68%
Est. operational CO₂e equivalent · ~0.14 g*
```

There are two different claims:

- **Presentation reduction**: a shorter representation of text that already exists. This does not retroactively avoid the compute used to generate the source.
- **Operational CO₂e avoided**: valid only when tokens are actually prevented from being generated or consumed, such as a future pre-generation or hook integration.

V0 reports the first as a **CO₂e equivalent**. It does not claim that previously generated emissions were undone.

The reference calculator is available at:

```bash
python3 skills/showmewhy/scripts/impact.py \
  --source-tokens 1000 \
  --output-tokens 250 \
  --budget 300
```

All energy, PUE, carbon-intensity and tree-equivalence assumptions are configurable.

## Visual selection

| Information | Default representation |
|---|---|
| Cause / evidence | Directed graph |
| Comparison | Markdown table |
| Sequence | Timeline |
| Architecture | Component graph |
| Hierarchy | Tree |
| Distribution | Compact bars |
| Dependencies | Dependency graph |
| Simple result | Text only |

The visual should reduce reading, not decorate the answer.

## Examples

- [Debugging](examples/debugging.md)
- [Architecture](examples/architecture.md)
- [Security](examples/security.md)

## Compatibility

The core skill follows the Agent Skills `SKILL.md` format. Claude Code exposes user-invocable skills through the `/` menu, so the intended Claude interaction is `/showmewhy`.

The skill keeps runtime-specific behaviour minimal so the same core can be installed in other Agent Skills-compatible tools. Claude-specific invocation metadata is ignored by hosts that do not implement it.

## V0 scope

V0 is intentionally just the skill plus two small deterministic calculators:

```text
/showmewhy
    ↓
concise conclusion
    +
useful visual
    +
evidence-backed why
    +
one-line verifiable evidence
    +
recurrence guard
    +
risk/reward next-task budget
    +
impact receipt
```

No account. No dashboard. No API key. No background service.

## Development

Run the test suite:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

Development is integrated through `develop`; feature work uses `feature/*` branches. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please report security issues privately. See [SECURITY.md](SECURITY.md).

## Licence

MIT. See [LICENSE](LICENSE).
