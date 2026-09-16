# ShowMeWhy

<div align="center">

**Don't tell me everything. Show me why.**

Evidence-backed answers for Claude Code.

`CONCLUSION → EVIDENCE → PROVENANCE → COST`

```text
/showmewhy
```

</div>

---

## The README in 30 seconds

```text
WHAT
A clean /showmewhy command for turning agent work into an inspectable decision receipt.

WHY
verbose output → signal → evidence path → conclusion

PROOF
raw evidence is retained before compression, provenance is inspectable,
and CI installs the real Claude runtime on Linux, macOS and Windows.

COST
less material carried forward when the runtime can safely compress it.
```

ShowMeWhy is built for the moment after Claude has done real work and you do not want another wall of narration. It leads with the result, keeps the evidence that materially supports it, shows the shortest useful provenance path, preserves decision-changing caveats, and can account for the context cost of the result. The visible habit is deliberately one command: **`/showmewhy`**.

[Install](#install) · [See the difference](#see-the-difference) · [The receipt](#the-showmewhy-receipt) · [Proof](#dont-trust-the-readme-show-me-the-proof) · [Deep dive](#deep-dive)

## Install

### macOS, Linux and WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.ps1 | iex
```

Then open a new Claude Code session:

```bash
claude
```

and use:

```text
/showmewhy why are my authentication tests failing?
```

The installer deliberately sets up two separate pieces. A **personal Claude Skill** is installed at `~/.claude/skills/showmewhy/`, which gives you the clean `/showmewhy` command. A **runtime-only plugin** is installed alongside it for hooks, evidence retention, context compression, provenance and adaptive safety. The plugin may appear internally in `claude plugin list` as `showmewhy@showmewhy`; that is implementation detail, not the command you type.

The installers are plain text in this repository. If you prefer to inspect before executing, read [`install.sh`](install.sh) or [`install.ps1`](install.ps1), then run the local file.

## See the difference

Without ShowMeWhy, the useful answer can be buried inside tool output, repeated observations and narrative explanation:

```text
pytest output
├── hundreds of passing lines
├── 5 failures
├── stack traces
├── repeated explanation
└── root cause somewhere near the end
```

With ShowMeWhy:

```text
AUTH REGRESSION

5 authentication tests failed.

WHY
middleware changed
      ↓
validation skipped
      ↓
expired session accepted
      ↓
authentication tests failed

MONITOR
Evidence  tests/auth.spec.ts::rejects_expired_session — FAIL before, PASS after
Guard     CI must keep rejects_expired_session green
Risk      MEDIUM
Budget    1,600 / 2,000 tokens · REWARDED

────────────────────────────────
ShowMeWhy · ~184 / 300 tokens · ↓72%
```

**Less narration. More justification.**

## The ShowMeWhy Receipt

The receipt is the product primitive. It is small enough to scan quickly but structured enough to inspect when the conclusion matters.

```text
┌──────────────────────────────────────────────┐
│ SHOWMEWHY RECEIPT                            │
├──────────────────────────────────────────────┤
│ WHAT                                         │
│ Authentication regression                    │
│                                              │
│ WHY                                          │
│ middleware → validation → failing test       │
│                                              │
│ PROOF                                        │
│ auth.spec.ts::rejects_expired_session        │
│                                              │
│ HOW SURE                                     │
│ HIGH · directly reproduced                   │
│                                              │
│ COST                                         │
│ ~184 / 300 tokens · ↓72%                     │
└──────────────────────────────────────────────┘
```

`WHY` is observable provenance, **not private chain-of-thought**. ShowMeWhy distinguishes observations, evidence, inference, conclusions and caveats. It does not turn correlation into causation merely because a causal story sounds plausible.

```text
CORRELATED_WITH  ≠  CAUSED_BY
```

## Don't trust the README. Show me the proof.

ShowMeWhy treats its own packaging the same way it treats an answer: claims should have inspectable evidence. CI does more than parse manifests.

| Claim | Release gate |
|---|---|
| The core contracts still work | Python test matrix on 3.11, 3.12 and 3.13 |
| The runtime is a valid Claude plugin | `claude plugin validate` on a clean runner |
| The plugin actually loads | real marketplace add + install + fresh-process `plugin list` |
| `/showmewhy` is global rather than plugin-namespaced | personal Skill is verified at `~/.claude/skills/showmewhy/` and the plugin cache is checked for an auto-discovered ShowMeWhy Skill |
| Installation is repeatable | the installer is run twice on the same clean runner |
| The install works across the supported desktop shells | acceptance runs on Ubuntu, macOS and Windows |

A release is created only after the main test workflow succeeds. Release history belongs in [`CHANGELOG.md`](CHANGELOG.md) and [GitHub Releases](https://github.com/vishnu-77/showmewhy/releases), not in this README.

## How it works

```text
                         CLAUDE CODE
                             │
                       /showmewhy
                             │
                  personal ShowMeWhy Skill
                             │
                             ▼
                     SHOWMEWHY RECEIPT
                 WHAT · WHY · PROOF · COST

Meanwhile, for eligible tool output:

verbose Bash result
        │
        ├──────────────→ retained raw evidence
        │                     evidence://...
        ▼
deterministic digest
        │
        ▼
agent context
        │
        ▼
typed provenance
        │
        ▼
adaptive safety policy
```

The design principle is simple:

> **The model can read less than the human can inspect.**

Raw output is retained locally before an eligible Bash result is compressed. Unsupported, short or uncertain results pass through unchanged, stderr is preserved, and the runtime fails open rather than hiding information when safe compression is not justified.

## Trust invariants

```text
SHOWMEWHY WILL                              SHOWMEWHY WILL NOT

✓ retain raw evidence first                × expose private chain-of-thought
✓ fail open when parsing is uncertain      × invent confidence percentages
✓ preserve material stderr                 × turn correlation into causation
✓ expose inspectable provenance            × claim spent compute was "saved"
✓ back off when evidence is reopened       × learn task solutions into policy
✓ enter shadow mode after reported loss    × hide material risk to hit a budget
```

Confidence is qualitative and included only when the evidence supports it. Risk is independent of confidence: a conclusion can be strongly evidenced and still describe a high-risk condition.

## One command, several views

```text
/showmewhy
    default decision receipt

/showmewhy why
    shortest useful evidence path

/showmewhy short
    smallest justified answer

/showmewhy visual
    table, timeline, tree or graph when structure helps

/showmewhy compare
    compact structured comparison

/showmewhy monitor
    evidence · guard · risk · next-task budget

/showmewhy impact
    context reduction and operational-impact accounting

/showmewhy json
    machine-readable receipt

/showmewhy deep
    larger evidence budget for complex work
```

These are soft presentation budgets. Correctness, security-relevant findings and material caveats take priority over being short.

## Deep dive

<details>
<summary><strong>Context compression</strong></summary>

The runtime watches eligible verbose Bash `PostToolUse` results. It stores raw evidence first, then uses deterministic parsers for recognised output shapes and creates a compact execution digest for subsequent context. A short, unsupported or low-confidence result is not replaced merely to produce a smaller number.

Runtime state is local under `.showmewhy/`, which is ignored by Git. Shadow mode can be forced with `SHOWMEWHY_MODE=shadow`, and a manual context target can be provided with `SHOWMEWHY_CONTEXT_BUDGET_TOKENS`.

</details>

<details>
<summary><strong>Inspectable provenance</strong></summary>

Retained runs can be represented as typed provenance graphs. Evidence and execution artefacts receive stable local addresses such as `evidence://sha256/<digest>#tool_response` and `run://<run-id>#findings/<n>`. Relationships include `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `OBSERVED_IN`, `VERIFIED_BY`, `CORRELATED_WITH` and `CAUSED_BY`.

A `CAUSED_BY` edge requires an explicit causal basis. The provenance graph is an inspectable evidence structure, not a reconstructed hidden reasoning trace.

</details>

<details>
<summary><strong>Adaptive safety policy</strong></summary>

Compression adapts from operational feedback rather than task content. Repeated evidence reopening or incomplete parsing makes the policy more conservative. Reported material information loss activates a sticky safety lock and forces shadow mode until it is explicitly reviewed and cleared. Policy feedback stores operational metrics; it does not learn source code, raw tool output, generated answers or task solutions.

</details>

<details>
<summary><strong>Token and operational-impact accounting</strong></summary>

ShowMeWhy separates presentation reduction from context actually avoided. Making already-generated prose shorter does not undo inference cost. Operational CO₂e avoidance is only appropriate when the runtime genuinely prevents material from entering later model context and the estimate has a defensible baseline. Assumptions remain visible rather than being collapsed into a fixed token-to-tree claim.

See [`standalone/showmewhy/references/impact-methodology.md`](standalone/showmewhy/references/impact-methodology.md).

</details>

<details>
<summary><strong>Local inspection</strong></summary>

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli provenance <run-id>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli compare <before-run> <after-run>
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli view <run-id> --out provenance.html
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli feedback <run-id> --reopened no --material-loss no
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli policy
```

The machine-readable receipt schema lives at [`standalone/showmewhy/references/showmewhy-receipt.schema.json`](standalone/showmewhy/references/showmewhy-receipt.schema.json).

</details>

## Development

Run the deterministic contract, runtime, provenance, policy and packaging tests with:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

The repository follows `feature/*` → `develop` → `main`, with release publication gated by the main CI result. Security reports should follow [`SECURITY.md`](SECURITY.md); contribution guidance is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Project

**Local-first · fail-open · inspectable**

[Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Releases](https://github.com/vishnu-77/showmewhy/releases) · [MIT Licence](LICENSE)
