<div align="center">

# ShowMeWhy

**Review only what the AI couldn't prove.**

Turn agent output into the smallest remaining verification surface.

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

Then use:

```text
/showmewhy:showmewhy
```

or give it a fresh question:

```text
/showmewhy:showmewhy is this migration actually safe to ship?
```

The installer sets up one marketplace-managed plugin containing the Skill, hooks and runtime, enables ShowMeWhy marketplace auto-update, and removes the older copied personal Skill if one exists.

## What it does

AI makes work cheap to produce and expensive to trust. ShowMeWhy tries to remove that verification debt before it reaches you.

It does **not** review everything and hand you a longer report. Internally it breaks a result into material claims, defines what would establish or refute them, gathers observable witnesses, closes what it can, and surfaces only what remains unresolved.

```text
Agent: Done. Authentication migration complete. All tests pass.

/showmewhy:showmewhy

SHOWMEWHY

Authentication migration works for the tested paths,
but legacy-token compatibility is still unverified.

2 verified · 1 need you

NEEDS YOU
1  Pre-migration mobile tokens remain compatible · HIGH
   No pre-migration mobile token was exercised.

DO NEXT
Run a pre-migration mobile token through the new verifier.
```

**Most tools show you more. ShowMeWhy tries to remove what you no longer need to review.**

## Before / after

<table>
<tr>
<td width="50%" valign="top">

### Before

> The agent changed 47 files and says the migration is complete. Tests are green, the new token path works, and the middleware has been updated. You still need to inspect the diff, work out which claims matter, decide whether the tests actually prove them, look for compatibility issues, and figure out what to check next.

</td>
<td width="50%" valign="top">

### After

```text
SHOWMEWHY

Migration works for tested paths.

18 verified · 2 need you

NEEDS YOU
1  Rollback behaviour · HIGH
   Rollback was never executed.

2  Legacy-client compatibility
   No old-client fixture was exercised.

DO NEXT
Run migrate → write → rollback → read.
```

</td>
</tr>
</table>

## The output

Default ShowMeWhy output has three jobs:

```text
RESULT      the narrowest defensible conclusion
NEEDS YOU   only material claims still open or refuted
DO NEXT     one action that closes the highest-value gap
```

No proof DAG. No mandatory MONITOR block. No carbon footer. No catalogue of every passing check.

If everything material can be independently settled:

```text
SHOWMEWHY

The measured claim is supported.

VERIFIED
6 material claims independently settled.

DO NEXT
No material verification gap found.
```

Use `why` mode when you actually want the expanded claim/witness ledger.

## The rules

1. **Agent assertions are not evidence.** “Done”, “tests pass”, and confidence language never close a claim by themselves.
2. **Verify claims, not line counts.** A 10-line security change can matter more than 10,000 generated lines.
3. **Every material claim gets an obligation.** What would establish it? What would refute it?
4. **Prefer witnesses over prose.** Executions, sources, measurements, invariants, boundaries, regressions and counterexamples beat another explanation.
5. **Broad claims get attacked.** “All”, “safe”, “backwards compatible”, “no regression”, and “production-ready” should trigger counterexample or boundary checks.
6. **Only three states exist.** `VERIFIED`, `REFUTED`, `OPEN`.
7. **Default output shows the remaining work.** At most three unresolved items, then one concrete `DO NEXT`.

The full contract lives in [`skills/showmewhy/SKILL.md`](skills/showmewhy/SKILL.md).

## Works beyond code

The verification primitive is domain-general. The witnesses change; the contract does not.

| Domain | Material claim | Example witness | Typical unresolved gap |
|---|---|---|---|
| Code | “migration is backwards compatible” | old-client regression fixture | legacy client never exercised |
| Policy | “all production identities require MFA” | clause + exception search | legacy bypass exists |
| Research | “method reduces energy use” | direct measurement | only token proxy measured |
| Contract | “all notice periods are 14 days” | clause search across schedules | conflicting 30-day clause |
| Data | “migration preserves semantics” | invariant + downstream fixture | null behaviour untested |
| Architecture | “single point of failure removed” | dependency/failure probe | shared Redis still exists |

Deterministic reference cases for these domains live in [`evals/reference_cases/`](evals/reference_cases/).

## Why this is different

Most review systems **add findings**. ShowMeWhy's target is the opposite: **shrink the human verification surface**.

A semantic diff can reorganise a large change. A receipt can prove that an action happened. ShowMeWhy asks a different question:

> **What material part of this result is still not independently established?**

That means a 500-line or 15,000-line change should not become a 100-line summary. If 497 of 500 material claims can be independently settled, the default surface should contain only the remaining three.

## How it works

Internally, ShowMeWhy uses a small verification grammar:

```text
CLAIM       material statement that affects trust or action
OBLIGATION  what would establish or refute it
WITNESS     observable execution, source, measurement or counterexample
SCRUTINY    does the witness really address the claim?
CLOSURE     VERIFIED · REFUTED · OPEN
SURFACE     only unresolved material claims reach the default output
```

The human does not need to see that machinery unless they ask for `why` or `json` mode.

## Views

```text
/showmewhy:showmewhy             unresolved verification surface
/showmewhy:showmewhy short       one gap + one next action
/showmewhy:showmewhy why         claim · state · witness/gap ledger
/showmewhy:showmewhy compare     compact comparison
/showmewhy:showmewhy monitor     session-level verification state
/showmewhy:showmewhy impact      context/token/operational impact
/showmewhy:showmewhy json        machine-readable verification surface
/showmewhy:showmewhy deep        broader verification, same compact final surface
```

## Battle-tested reference behaviour

The deterministic reference engine is intentionally small enough to inspect:

```bash
python skills/showmewhy/scripts/verification_surface.py \
  evals/reference_cases/code-auth.json
```

Current fixtures cover code, policy, research, contracts, data and architecture. The scale test also creates **500 material claims**, verifies 497, leaves 3 open, and asserts that the default human output does not replay the 497 settled claims.

Run the complete suite:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

## Under the hood

<details>
<summary><strong>Witness closure</strong></summary>

The deterministic reference implementation lives at [`skills/showmewhy/scripts/verification_surface.py`](skills/showmewhy/scripts/verification_surface.py). A material claim is `VERIFIED` only when its required witness kinds are present and no current witness refutes it. A refuting witness wins over supporting evidence. Missing, inconclusive, conflicting, stale or human-only evidence leaves the claim `OPEN`.

The V2 machine contract is [`skills/showmewhy/references/verification-surface.schema.json`](skills/showmewhy/references/verification-surface.schema.json).

</details>

<details>
<summary><strong>Context compression and retained evidence</strong></summary>

Eligible verbose Bash `PostToolUse` results are stored as raw local evidence before deterministic parsing. Recognised result shapes can be replaced in model context with a smaller execution digest. Short, unsupported or low-confidence results are left untouched.

Runtime state is local under `.showmewhy/`. Reported material loss forces the adaptive policy into shadow mode until explicitly reviewed and cleared.

</details>

<details>
<summary><strong>Provenance</strong></summary>

Retained evidence and runs still receive stable local addresses such as `evidence://...` and `run://...`. Typed provenance remains available for machines and deep inspection, but it is no longer the default human UI.

Private chain-of-thought is never exposed or reconstructed.

</details>

<details>
<summary><strong>Impact accounting</strong></summary>

ShowMeWhy separates presentation reduction from context actually avoided. Shortening already-generated text does not undo inference cost. Operational CO₂e estimates are available only through explicit `impact` use when the baseline is defensible.

See [`skills/showmewhy/references/impact-methodology.md`](skills/showmewhy/references/impact-methodology.md).

</details>

## Proof

ShowMeWhy's own release path uses real acceptance gates:

| Claim | CI gate |
|---|---|
| Core contracts still work | Python 3.11, 3.12 and 3.13 |
| Claude accepts the plugin | real `claude plugin validate` |
| Marketplace install actually loads | add → install → fresh-process `plugin list` |
| Skill and runtime ship together | installed cache contains both |
| Auto-update is configured | marketplace state has `autoUpdate: true` |
| Installation is repeatable | installer runs twice on clean runners |
| Desktop install paths work | Ubuntu, macOS and Windows acceptance |

Release history belongs in [`CHANGELOG.md`](CHANGELOG.md) and [GitHub Releases](https://github.com/vishnu-77/showmewhy/releases), not in this README.

## License

[MIT](LICENSE).

---

<div align="center">

**Local-first · fail-open · inspectable**

Star the repo if ShowMeWhy removed one thing you no longer had to review.

</div>
