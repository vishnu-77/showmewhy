# ShowMeWhy

**Don't tell me everything. Show me why.**

ShowMeWhy is a Claude Code plugin and Agent Skill that turns verbose agent work into a compact, evidence-backed decision receipt. Instead of returning another wall of explanation, it leads with the conclusion, keeps only the signals that matter, shows the shortest inspectable evidence path, preserves material caveats, and can report the context cost of reaching the result. The goal is simple: make agent output easier to trust, easier to verify, and cheaper to carry forward.

```text
/showmewhy
```

## Install

The recommended installation is the full Claude Code plugin because it includes the `/showmewhy` Skill together with the local runtime used for evidence retention, context compression, provenance and adaptive safety. Use the explicit HTTPS repository URL so installation does not depend on local SSH host-key configuration.

```bash
claude plugin marketplace add https://github.com/vishnu-77/showmewhy.git && claude plugin install showmewhy@showmewhy
```

The repository is private during preview, so Git on the local machine must already be authenticated for `vishnu-77/showmewhy`. After installation, start Claude Code normally and invoke ShowMeWhy in the same conversation where the work is happening.

```text
/showmewhy why are my authentication tests failing?
```

If only the prompt-level Agent Skill is wanted, without the Claude runtime hook, install the Skill directly:

```bash
npx skills add vishnu-77/showmewhy --skill showmewhy
```

## The receipt

A ShowMeWhy Receipt is deliberately small enough to scan but structured enough to inspect. A typical result looks like this:

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

The `WHY` section is observable provenance rather than private chain-of-thought. ShowMeWhy distinguishes observations, evidence, inference, conclusions and caveats, and it does not promote correlation into causation without explicit support. Confidence is qualitative and omitted when the available evidence does not justify it.

## How it works

ShowMeWhy can operate purely as a response transformation, but the Claude Code plugin also watches eligible verbose Bash results before they are carried further into agent context. Raw output is retained locally first, then a deterministic parser produces a compact execution digest for the model. Short, unsupported or uncertain outputs pass through unchanged, stderr is preserved, and the runtime fails open rather than hiding information when it cannot safely compress a result. Runtime state is kept under `.showmewhy/`, which is ignored by Git.

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

Each retained run can also be represented as a typed provenance graph. Evidence and execution artefacts receive stable local addresses such as `evidence://sha256/<digest>#tool_response` and `run://<run-id>#findings/<n>`, while relationships such as `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `OBSERVED_IN`, `VERIFIED_BY`, `CORRELATED_WITH` and `CAUSED_BY` describe how the result was justified. A `CAUSED_BY` edge is rejected unless an explicit causal basis is attached, so the graph remains an inspectable evidence structure rather than a narrative invented after the fact.

ShowMeWhy also adjusts context compression from operational feedback rather than task content. Repeated low-reopen, high-completeness runs can permit tighter compression, while frequent raw-evidence reopening or incomplete parsing moves the policy in a more conservative direction. Any reported material information loss activates a sticky safety lock that forces shadow mode until it is explicitly reviewed and cleared. The policy log stores run identifiers and operational metrics such as reopen state, parser completeness and compression percentage; it does not learn or retain task solutions, source code, generated summaries or raw tool output.

## Modes

`/showmewhy` is the primary habit. Optional modes include `short` for the smallest useful answer, `why` for the evidence path, `visual` when a table, timeline, tree or graph reduces cognitive load, `compare` for structured comparison, `deep` for a larger evidence budget, `monitor` for evidence/guard/risk/budget reporting, `impact` for context and operational-impact accounting, and `json` for a machine-readable receipt. These are soft presentation budgets rather than hard truncation rules; correctness, security-relevant findings and material caveats always take priority.

## Evidence, risk and guards

For substantive conclusions, ShowMeWhy can attach one independently verifiable evidence line and one concrete recurrence guard. Evidence should resolve to an observable artefact such as a test result, file and line, command output, source citation or retained run. A guard describes how recurrence will be detected through a named regression test, CI check, assertion, invariant or alert; it never claims that a failure has become impossible. Risk is assessed independently from confidence so a well-supported conclusion can still be high-risk when the blast radius is large.

## Token and operational-impact accounting

ShowMeWhy separates presentation reduction from context actually avoided. Making an answer shorter after the model has already generated it is reported as presentation reduction, not as energy or emissions saved. When the runtime genuinely prevents verbose material from entering subsequent model context, the avoided context can be measured and used for an explicitly modelled operational CO₂e estimate. The methodology keeps energy use, PUE and grid-carbon assumptions visible and does not claim a fixed token-to-tree conversion. See [`skills/showmewhy/references/impact-methodology.md`](skills/showmewhy/references/impact-methodology.md) for the calculation model.

## Local inspection

Raw evidence remains available locally when a compressed digest is not enough. Provenance, run comparison and the local static viewer can be invoked from the runtime CLI, and adaptive-policy feedback can be recorded explicitly when evidence was reopened or material information was lost.

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli provenance <run-id>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli compare <before-run> <after-run>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli view <run-id> --out provenance.html
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli feedback <run-id> --reopened no --material-loss no
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli policy
```

Shadow mode can be forced with `SHOWMEWHY_MODE=shadow`, and a manual context target can be supplied with `SHOWMEWHY_CONTEXT_BUDGET_TOKENS`. An adaptive safety lock should only be cleared after the underlying material-loss event has been reviewed.

## Machine-readable output

`/showmewhy json` emits the same receipt contract in machine-readable form. The schema is maintained at [`skills/showmewhy/references/showmewhy-receipt.schema.json`](skills/showmewhy/references/showmewhy-receipt.schema.json), allowing other tools to consume conclusions, evidence, caveats, confidence, monitor data and impact metadata without scraping prose.

## Privacy and security

ShowMeWhy is local-first. Raw runtime evidence stays on the machine unless the user explicitly moves or shares it, adaptive-policy feedback stores operational metrics rather than task content, unsupported parser states fail open, and security-relevant information is not intentionally suppressed merely to meet a size target. See [`SECURITY.md`](SECURITY.md) for security reporting and the repository's trust assumptions.

## Development

The deterministic contract, runtime, provenance, policy and plugin-packaging tests can be run with:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

CI also installs Claude Code on a clean runner and verifies the real marketplace-add, plugin-install and fresh-process discovery path so packaging failures are caught before release. Development follows `feature/*` → `develop` → `release/*` → `main`.

Release history belongs in [`CHANGELOG.md`](CHANGELOG.md) and GitHub Releases rather than in this README.

## Licence

MIT. See [`LICENSE`](LICENSE).
