<div align="center">

<img src="brand/showmewhy-philosopher-lockup.svg" alt="ShowMeWhy" width="420">

**Review only what the AI couldn't prove.**

Turn agent output into the smallest remaining verification surface.

**Most tools show you more. ShowMeWhy removes what you no longer need to review.**

<p>
  <img src="https://img.shields.io/github/v/release/vishnu-77/showmewhy?style=flat&label=release" alt="Latest release">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/vishnu-77/showmewhy?style=flat" alt="License"></a>
  <a href="https://github.com/vishnu-77/showmewhy/actions/workflows/test.yml"><img src="https://github.com/vishnu-77/showmewhy/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
</p>

<img src="brand/showmewhy-arrange.svg" alt="ShowMeWhy turns agent claims into a small verification surface" width="720">

</div>

## Install

~~~text
/plugin marketplace add vishnu-77/showmewhy
/plugin install showmewhy@showmewhy
/reload-plugins

/showmewhy
~~~

<details>
<summary><strong>Other install options</strong></summary>

~~~bash
claude plugin marketplace add vishnu-77/showmewhy
claude plugin install showmewhy@showmewhy
~~~

macOS / Linux / WSL:

~~~bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
~~~

Windows PowerShell:

~~~powershell
irm https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.ps1 | iex
~~~

</details>

**Agent claim → /showmewhy → only the unresolved gap.**

<details>
<summary><strong>▶ What's inside? Click to inspect</strong></summary>

- **Verification surface** — only material unresolved claims
- **Witness closure** — `VERIFIED · REFUTED · OPEN`
- **Context Delta** — surfaces when new evidence changes an earlier answer
- **Evidence retention** — raw evidence remains inspectable
- **Safe compression** — incomplete digests never silently replace source evidence
- **Provenance** — stable `evidence://...` and `run://...` references
- **Views** — `short`, `why`, `compare`, `deep`, `json`
- **Composition** — e.g. `/monitor → /verify → /focus`
- **Lifecycle** — `/showmewhy status` and `/showmewhy update`
- **V5 evaluation** — empirical validation in progress

</details>

## How it works

~~~text
CLAIM → OBLIGATION → WITNESS → SCRUTINY → VERIFIED | REFUTED | OPEN → SURFACE
~~~

Agent assertions are not evidence. “Tests pass” proves the tests passed; it does not automatically prove the broader claim.

Full contract: [`skills/showmewhy/SKILL.md`](skills/showmewhy/SKILL.md).

## When the answer changes

~~~text
SHOWMEWHY · DELTA

CHANGED
The rollout is blocked.

BROKEN ASSUMPTION
The consumed dependency already contained the required fix.

NEW EVIDENCE
The project still pins the older version.

DO NEXT
Update the pin, then rerun the check.
~~~

## Works beyond code

The same contract works for code, security, policy, research, data and architecture. Only the witness changes.

## Under the hood

Runtime state lives **outside the consumer repository**. Raw evidence remains the source of truth; incomplete compression cannot silently replace it.

Runtime details: [`runtime/README.md`](runtime/README.md).

<details>
<summary><strong>Evaluation</strong></summary>

ShowMeWhy does not treat a good demo as proof of effectiveness.

V5 asks:

> **Can ShowMeWhy reduce the evidence a human must inspect while preserving detection of consequential agent errors?**

The repository includes the scorer, schema, real-world pilot corpus and executable oracle validation.

See [`evals/v5/`](evals/v5/).

**No effectiveness number is claimed until the paired evaluation produces one.**

~~~bash
python -m unittest discover -s evals -p 'test_*.py'
~~~

</details>

Release history belongs in [`CHANGELOG.md`](CHANGELOG.md) and [GitHub Releases](https://github.com/vishnu-77/showmewhy/releases).

## License

[MIT](LICENSE).

---

<div align="center">

**Local-first · fail-open · inspectable**

</div>
