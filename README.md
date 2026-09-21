<div align="center">

<img src="brand/showmewhy-philosopher-lockup.svg" alt="ShowMeWhy" width="460">

**Review only what the AI couldn't prove.**

Turn agent output into the smallest remaining verification surface.

<p>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/vishnu-77/showmewhy?style=flat" alt="License"></a>
  <a href="https://github.com/vishnu-77/showmewhy/actions/workflows/test.yml"><img src="https://github.com/vishnu-77/showmewhy/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
</p>

</div>

<p align="center">
  <img src="brand/showmewhy-arrange.svg" alt="ShowMeWhy arranges noisy agent output into a verification surface" width="860">
</p>

## What ShowMeWhy does

Agents are good at producing work and describing what they changed. The expensive part is deciding whether those claims are actually established.

ShowMeWhy takes an agent result, identifies the material claims, checks them against observable evidence, closes what can be independently settled, and surfaces only the remaining verification gap.

It asks one question:

> **What still needs human verification before this result should be trusted?**

### Example: the agent says the UI is fixed

```text
Agent:

State light restored.

READY                  neutral
RISK                   red
CONNECT / SCANNING     amber
VERIFY                 amber
DONE                   green

The decorative dot-matrix system stays removed.
The header and footer stay clean.
```

That response sounds complete, but it contains several independent claims. A successful build does not prove that the semantic light still exists, that every state renders correctly, or that decorative dots were removed without deleting the meaningful indicator.

Run:

```text
/showmewhy
```

If most claims can be established but one rendered state was never exercised:

```text
SHOWMEWHY

The status-light change is mostly verified.

5 verified · 1 need you

NEEDS YOU
1  DONE renders green in the actual UI · MEDIUM
   The mapping exists in code, but the DONE state was not
   exercised in the rendered component.

DO NEXT
Trigger DONE and inspect the rendered status indicator.
```

If the implementation actually removed the semantic indicator with the decorative dots:

```text
SHOWMEWHY

The requested status indicator was not fully restored.

4 verified · 1 refuted

REFUTED
1  Exactly one semantic status light remains · HIGH
   The decorative dots were removed, but the semantic state
   indicator was removed with them.

DO NEXT
Restore the single state indicator without reintroducing
the decorative dot matrix.
```

The goal is not another review report. It is to distinguish **what the agent said** from **what the evidence establishes**, then remove everything the human no longer needs to inspect.

## Install

### Claude Code marketplace

Inside Claude Code:

```text
/plugin marketplace add vishnu-77/showmewhy
/plugin install showmewhy@showmewhy
/reload-plugins
```

Then run:

```text
/showmewhy
```

or verify a fresh question directly:

```text
/showmewhy is this migration actually safe to ship?
```

The public command surface is `/showmewhy`. The Skill, hooks and runtime ship together as one marketplace-managed plugin.

### One-line installer

macOS, Linux and WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.ps1 | iex
```

The installer configures the same marketplace-managed plugin, enables marketplace auto-update and removes the legacy copied personal Skill when present.

### Status and updates

```text
/showmewhy status
/showmewhy update
```

If an update is installed during an active Claude Code session, run `/reload-plugins` or start a new session before expecting the new contract to be active.

## Verification contract

ShowMeWhy uses a small internal grammar:

| Stage | Meaning |
|---|---|
| `CLAIM` | A material statement that affects trust or action |
| `OBLIGATION` | What would establish or refute that claim |
| `WITNESS` | Observable execution, source, measurement, invariant, boundary check, regression or counterexample |
| `SCRUTINY` | Whether the witness actually addresses the claim and is current |
| `CLOSURE` | `VERIFIED`, `REFUTED` or `OPEN` |
| `SURFACE` | Only material unresolved or refuted claims shown by default |

Agent assertions, confidence language and “done” messages are not independent evidence. A passing command proves that command passed; it does not automatically establish a broader semantic claim.

Broad claims such as “safe”, “all”, “backwards compatible”, “no regression” and “production-ready” require stronger witnesses and, where appropriate, counterexamples or boundary checks.

The complete behavioural contract lives in [`skills/showmewhy/SKILL.md`](skills/showmewhy/SKILL.md).

## Default output

The normal human surface has three jobs:

```text
RESULT      narrowest defensible conclusion
NEEDS YOU   only material claims still open or refuted
DO NEXT     one action that closes the highest-value gap
```

If every material claim can be independently settled:

```text
SHOWMEWHY

The measured claim is supported.

VERIFIED
6 material claims independently settled.

DO NEXT
No material verification gap found.
```

ShowMeWhy does not expose or reconstruct private chain-of-thought. It works from observable evidence and explicit claim state.

## When evidence changes the answer

A previously supported conclusion can become unsafe when later evidence invalidates an assumption. ShowMeWhy handles that as a **Context Delta** rather than replaying the whole investigation.

```text
Earlier
PI-901 can proceed after the planned NetworkPolicy work.

Later evidence
hl2-saas-helm pins shared charts v1.5.0.
PI-823 is fixed only in v1.6.1.

/showmewhy

SHOWMEWHY · DELTA

CHANGED
PI-901 cannot safely proceed until PI-906 updates the chart pin.

BROKEN ASSUMPTION
The consumed shared-chart version is safe for NetworkPolicy enforcement.

NEW EVIDENCE
v1.5.0 is pinned; the required PI-823 fix lands in v1.6.1.

BLOCKER
PI-906 · bump the shared-chart pin.

DO NEXT
Merge PI-906, then run the planned maintenance-window smoke tests.
```

Context Delta reuses the same verifier. Internally it tracks the inspected context, relied-upon assumption, invalidating evidence and resulting state change.

## Views

| Command | Purpose |
|---|---|
| `/showmewhy` | Default unresolved surface or automatic Context Delta |
| `/showmewhy short` | One gap and one next action |
| `/showmewhy why` | Expanded claim/witness/gap ledger |
| `/showmewhy compare` | Evidence-aware comparison |
| `/showmewhy monitor` | Session-level verification state |
| `/showmewhy impact` | Context, token and operational-impact accounting |
| `/showmewhy json` | Machine-readable verification or delta output |
| `/showmewhy deep` | Broader verification with the same compact final surface |
| `/showmewhy status` | Installed version, plugin and update health |
| `/showmewhy update` | Update through Claude Code's native plugin updater |

### Composition

Several ShowMeWhy behaviours can be composed while exposing only one Claude Code command:

```text
/showmewhy /monitor /showmewhy /i-have-adhd -- investigate why auth tests fail
```

Only the first `/showmewhy` is a Claude Code command. The remaining slash-prefixed tokens are parsed by ShowMeWhy as internal stages. Unknown stages fail closed, and task text is separated with `--` so ordinary paths, flags or URLs are not mistaken for commands.

## Works beyond code

The verification primitive is domain-general; the witnesses change, but the contract does not.

| Domain | Material claim | Example witness | Typical unresolved state |
|---|---|---|---|
| Code | “migration is backwards compatible” | old-client regression fixture | legacy client never exercised |
| Policy | “all production identities require MFA” | clause + exception search | legacy bypass refutes the universal claim |
| Research | “method reduces energy use” | direct measurement | only a token proxy was measured |
| Contract | “all notice periods are 14 days” | clause search across schedules | Schedule B still says 30 days |
| Data | “migration preserves semantics” | invariant + downstream fixture | null behaviour untested |
| Architecture | “single point of failure removed” | dependency/failure probe | shared Redis still exists |

## Runtime and evidence

Eligible verbose Bash `PostToolUse` results can be retained as raw local evidence and represented by smaller deterministic execution digests.

Raw evidence remains the source of truth. Since v4.4.2, destructive replacement is allowed only when the compressor declares its representation complete and the effective runtime mode permits replacement. Incomplete digests may assist inspection, but they cannot silently become the agent's only visible evidence.

Runtime state is stored outside the consumer repository in ShowMeWhy's OS-level state directory, partitioned by project. `SHOWMEWHY_HOME` can override the state root.

Retained evidence and runs receive stable local addresses such as `evidence://...` and `run://...`. Typed provenance remains available for deeper inspection without becoming the default human UI.

More detail is in [`runtime/README.md`](runtime/README.md).

## Evaluation

ShowMeWhy separates **product behaviour** from **claims about effectiveness**.

The deterministic reference suite checks the verification contract across code, policy, research, contracts, data and architecture. Temporal cases test Context Delta behaviour.

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

The V5 evaluation track asks a stricter empirical question:

> **Can ShowMeWhy reduce the amount of evidence a human must inspect while preserving detection of consequential agent errors?**

The current V5 harness includes a machine-readable schema, scorer, a frozen real-world pilot corpus and executable upstream oracle validation.

Primary measurements are material-failure recall and verification-surface reduction. False closure is treated as a safety diagnostic rather than hidden inside an aggregate score.

See [`evals/v5/`](evals/v5/) for the protocol and implementation.

No effectiveness number is claimed in this README until the paired evaluation has produced one.

## Release proof

ShowMeWhy's release path uses executable acceptance gates:

| Claim | CI gate |
|---|---|
| Core contracts still work | Python 3.11, 3.12 and 3.13 |
| Claude accepts the plugin | real `claude plugin validate` |
| Marketplace installation loads | add → install → fresh-process plugin inspection |
| Skill and runtime ship together | installed cache contains both |
| Auto-update is configured | marketplace state inspection |
| Installation is repeatable | installer runs twice on clean runners |
| Desktop install paths work | Ubuntu, macOS and Windows acceptance |

Release history lives in [`CHANGELOG.md`](CHANGELOG.md) and [GitHub Releases](https://github.com/vishnu-77/showmewhy/releases).

## Advanced references

<details>
<summary><strong>Deterministic verifier</strong></summary>

The reference implementation is [`skills/showmewhy/scripts/verification_surface.py`](skills/showmewhy/scripts/verification_surface.py).

The machine contract is [`skills/showmewhy/references/verification-surface.schema.json`](skills/showmewhy/references/verification-surface.schema.json).

A material claim becomes `VERIFIED` only when its required witness kinds are present and no current witness refutes it. Missing, conflicting, stale, inconclusive or human-only evidence leaves the claim `OPEN`.

</details>

<details>
<summary><strong>Context Delta</strong></summary>

[`skills/showmewhy/scripts/context_delta.py`](skills/showmewhy/scripts/context_delta.py) compares previous and current verification states and emits only decision-relevant changes.

Its machine contract is [`skills/showmewhy/references/context-delta.schema.json`](skills/showmewhy/references/context-delta.schema.json).

</details>

<details>
<summary><strong>Impact accounting</strong></summary>

ShowMeWhy distinguishes presentation reduction from context actually avoided. Shortening already-generated text does not undo inference cost. Operational CO₂e estimates are available only through explicit `impact` use when the baseline is defensible.

See [`skills/showmewhy/references/impact-methodology.md`](skills/showmewhy/references/impact-methodology.md).

</details>

## Brand

The Socratic thinker represents scrutiny before acceptance. Brand construction and usage live in [`brand/`](brand/README.md).

## License

[MIT](LICENSE).

---

<div align="center">

**Local-first · fail-open · inspectable**

Star the repo if ShowMeWhy removed one thing you no longer had to review.

</div>
