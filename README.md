<div align="center">

# ShowMeWhy

**Don't tell me everything. Show me why.**

Evidence-backed answers for Claude Code — conclusion first, proof attached.

`WHAT → WHY → PROOF → COST`

<p>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/vishnu-77/showmewhy?style=flat" alt="License"></a>
  <a href="https://github.com/vishnu-77/showmewhy/actions/workflows/test.yml"><img src="https://github.com/vishnu-77/showmewhy/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
</p>

</div>

## Install

### macOS, Linux and WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.ps1 | iex
```

Start Claude Code, then ask:

```text
/showmewhy:showmewhy why are my authentication tests failing?
```

The installer sets up one marketplace-managed plugin containing the Skill, hooks and runtime. It also enables ShowMeWhy marketplace auto-update and removes the older copied personal Skill if one exists.

## What it does

ShowMeWhy turns either a fresh question or completed agent work into a compact, inspectable answer.

```text
WHAT      the conclusion
WHY       the shortest justified evidence path
PROOF     the observable source that supports it
COST      the context/token impact when it can be measured honestly
```

For eligible verbose Bash output, the runtime can also retain the raw evidence locally, give Claude a smaller deterministic digest, attach typed provenance, and back off when compression becomes unsafe.

## Before / after

<table>
<tr>
<td width="50%" valign="top">

### Before

> I ran the authentication suite and there are several failures. Most tests pass, but the output includes multiple stack traces and repeated middleware errors. The failures appear related to session validation after a recent middleware change. One test around expired sessions is especially relevant, and there are a few possibilities worth checking before deciding on the exact cause...

</td>
<td width="50%" valign="top">

### After

```text
AUTH REGRESSION

5 authentication tests failed.

WHY
middleware changed
      ↓
validation skipped
      ↓
expired session accepted

PROOF
rejects_expired_session
FAIL before · PASS after

Risk  MEDIUM
```

</td>
</tr>
</table>

**Less narration. More justification.**

## The receipt

```text
┌──────────────────────────────────────────────┐
│ SHOWMEWHY                                    │
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

`WHY` is observable provenance, not private chain-of-thought.

```text
CORRELATED_WITH  ≠  CAUSED_BY
```

## The rules

1. Lead with the conclusion.
2. Keep only evidence that can change the conclusion.
3. Evidence-cover material counts such as “4 fixes” or “7 failures”.
4. Treat `CAUSED_BY` as a high-evidence relationship, not a convenient story.
5. Retain raw evidence before eligible runtime compression.
6. Fail open when parsing or compression is uncertain.
7. Never present already-spent compute as emissions or tokens that were “saved”.

The complete behaviour contract lives in [`skills/showmewhy/SKILL.md`](skills/showmewhy/SKILL.md).

## How it works

```text
Claude Code
    │
    ▼
/showmewhy:showmewhy
    │
    ▼
ShowMeWhy Skill
    │
    ├──────────────→ conclusion
    ├──────────────→ evidence path
    └──────────────→ receipt

eligible Bash output
    │
    ├──────────────→ raw evidence retained locally
    ▼
deterministic digest
    │
    ▼
typed provenance
    │
    ▼
adaptive safety policy
```

> **The model can read less than the human can inspect.**

Unsupported, short or low-confidence tool results pass through unchanged. Material stderr is preserved. Reported material information loss forces the adaptive policy into shadow mode until it is explicitly reviewed and cleared.

## Views

```text
/showmewhy:showmewhy             default receipt
/showmewhy:showmewhy why         evidence path
/showmewhy:showmewhy short       maximum compression
/showmewhy:showmewhy visual      table, timeline, tree or graph
/showmewhy:showmewhy compare     compact comparison
/showmewhy:showmewhy monitor     evidence · guard · risk · budget
/showmewhy:showmewhy impact      context and operational impact
/showmewhy:showmewhy json        machine-readable receipt
/showmewhy:showmewhy deep        larger evidence budget
```

Correctness and material caveats always take priority over being short.

## Proof

ShowMeWhy's release path checks the claims that matter instead of trusting packaging alone.

| Claim | CI gate |
|---|---|
| Core contracts still work | Python 3.11, 3.12 and 3.13 |
| Claude accepts the plugin | real `claude plugin validate` |
| Marketplace install actually loads | add → install → fresh-process `plugin list` |
| Skill and runtime ship together | installed cache contains both |
| Auto-update is configured | marketplace state must have `autoUpdate: true` |
| Migration is repeatable | installer runs twice on clean runners |
| Desktop install paths work | Ubuntu, macOS and Windows acceptance |

## Under the hood

<details>
<summary><strong>Context compression</strong></summary>

Eligible verbose Bash `PostToolUse` results are stored as raw local evidence before deterministic parsing. Recognised result shapes can be replaced in model context with a smaller execution digest. Short, unsupported or low-confidence results are left untouched.

Runtime state is local under `.showmewhy/`. Shadow mode can be forced with `SHOWMEWHY_MODE=shadow`.

</details>

<details>
<summary><strong>Inspectable provenance</strong></summary>

Retained evidence and runs receive stable local addresses such as `evidence://...` and `run://...`. Provenance relationships include `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `VERIFIED_BY`, `CORRELATED_WITH` and `CAUSED_BY`.

A `CAUSED_BY` edge requires an explicit causal basis. The graph is an inspectable evidence structure, not reconstructed hidden reasoning.

</details>

<details>
<summary><strong>Adaptive safety policy</strong></summary>

The runtime adapts from operational feedback such as parser completeness, evidence reopen rate and material-loss reports. Repeated reopening makes compression more conservative. Reported material loss activates a sticky safety lock and shadow mode.

The policy does not learn source code, raw tool output, generated answers or task solutions.

</details>

<details>
<summary><strong>Token and operational-impact accounting</strong></summary>

ShowMeWhy separates presentation reduction from context actually avoided. Shortening text after it has already been generated does not undo inference cost. Operational CO₂e avoidance is only appropriate when material is genuinely prevented from entering later model context and the baseline is defensible.

See [`skills/showmewhy/references/impact-methodology.md`](skills/showmewhy/references/impact-methodology.md).

</details>

## Development

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

Release history belongs in [`CHANGELOG.md`](CHANGELOG.md) and [GitHub Releases](https://github.com/vishnu-77/showmewhy/releases), not in this README.

[Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Plugin details](PLUGIN.md) · [MIT Licence](LICENSE)

---

<div align="center">

**Local-first · fail-open · inspectable**

Star the repo if ShowMeWhy saved you from reading one more wall of agent output.

</div>
