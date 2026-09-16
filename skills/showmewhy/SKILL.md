---
name: showmewhy
description: Verify a fresh answer or completed agent result, independently settle material claims where possible, and surface only the smallest remaining verification gap. Use when the user explicitly invokes ShowMeWhy or asks what still needs to be checked before trusting a result.
argument-hint: "[short|why|compare|monitor|impact|json|deep] [question or scope]"
user-invocable: true
disable-model-invocation: true
---

# ShowMeWhy

ShowMeWhy answers one question: **what still needs human verification before this result should be trusted?**

The default response is not a summary, report, graph, or chain-of-thought. Internally, decompose the result into material claims, define what would establish or refute each claim, gather observable witnesses, scrutinise them, and close what can be independently settled. Externally, show only the unresolved verification surface and one next action.

Never expose, reconstruct, or claim to expose private chain-of-thought. Agent assertions, prior prose, confidence language, or a model saying "done" are not independent evidence.

## Invocation semantics

Interpret `$ARGUMENTS` as an optional mode followed by optional scope.

- no mode: verification surface, 220-token soft budget
- `short`: one unresolved claim and one next action, 100-token soft budget
- `why`: expanded claim / witness / gap ledger, 450-token soft budget
- `compare`: compact comparison, normally a Markdown table, 300-token soft budget
- `monitor`: session-level verification state only; never include this automatically in ordinary runs
- `impact`: context/token/operational-impact accounting only
- `json`: emit a machine-readable Verification Surface object conforming to `references/verification-surface.schema.json`
- `deep`: perform broader verification for complex or high-consequence work, while keeping the final human surface gap-first, 700-token soft budget

If the arguments contain a fresh question or task, answer or investigate it first, then verify the material claims in that result. **Do not refuse merely because no prior answer exists.** Use tools, files, tests, commands, web research, measurements, or source inspection when needed.

If no fresh question is supplied, verify the most recent substantive answer, task result, investigation, change, or decision. Reuse current evidence when it is still valid; independently re-check material claims when the original evidence is missing, stale, self-reported, or insufficient.

## Internal verification pipeline

Do this internally; do not print the pipeline as a flow diagram.

1. **CLAIM** — extract the smallest set of material claims whose truth would change whether the result should be trusted or acted on.
2. **OBLIGATION** — for each claim, state what would establish or refute it. Broad, causal, universal, security-sensitive, or high-consequence claims need stronger obligations.
3. **WITNESS** — gather observable evidence. Prefer executable or independently inspectable witnesses over model prose.
4. **SCRUTINY** — check that the witness actually addresses the claim, is current, and is not merely evidence that an action happened.
5. **CLOSURE** — mark the claim `VERIFIED`, `REFUTED`, or `OPEN`.
6. **SURFACE** — show only material `OPEN` or `REFUTED` claims by default.

Read `references/receipt-contract.md` for the human contract and `references/verification-surface.schema.json` for machine-readable output.

## Witness grammar

A witness is the smallest observable fact, execution, source, measurement, invariant, boundary check, counterexample, regression check, or comparison that can establish or falsify a material claim.

Useful witness kinds include:

- `execution`: a command, test, query, or operation with an inspectable outcome
- `source`: a file, line, clause, citation, table cell, figure, record, or authoritative statement
- `measurement`: a measured value tied to the claim
- `invariant`: a property that must hold across many cases
- `counterexample`: an attempt to falsify a broad claim
- `boundary`: a check at an API, schema, identity, data, regulatory, or organisational boundary
- `regression`: evidence that behaviour intended to remain unchanged still does
- `comparison`: before/after or alternative outcomes under equivalent conditions

For high-consequence or broad claims, prefer more than one witness type. A passing command proves that command passed; it does not automatically prove a broader semantic claim.

## Closure rules

Use only these human-facing states:

- `VERIFIED`: the required witnesses support the claim and no material contradictory witness remains
- `REFUTED`: a current, relevant witness directly contradicts the claim
- `OPEN`: evidence is missing, incomplete, conflicting, stale, outside available tools, or requires human judgement

When evidence conflicts, keep the claim `OPEN` unless one source clearly supersedes the other and that precedence is itself observable.

A broad statement such as "all", "safe", "production-ready", "backwards compatible", "no regression", or "consistently" should normally trigger a counterexample, boundary, or regression obligation rather than being accepted from positive evidence alone.

`CAUSED_BY` remains a high bar internally. A missing validator, guard, or test may have allowed a defect to survive undetected; that does not prove it caused the defect.

Every material quantified claim must be covered by observable evidence. If a result says "4 fixes", "7 failures", or "3 causes", verify the stated count or explicitly narrow the claim.

## Default human output

Do not print a provenance graph, arrow chain, MONITOR block, confidence paragraph, or CO₂e receipt by default.

When material gaps remain:

```text
SHOWMEWHY

<one-line result>

NEEDS YOU
1  <material unresolved claim>
   <why it is still open or what refuted it>

DO NEXT
<single action that would close the highest-value gap>
```

When many claims were checked, one compact tally may appear before `NEEDS YOU`, for example:

```text
12 verified · 2 need you
```

Show at most **3** unresolved items in the default response. If more remain, add one line such as `+4 more · use why mode` rather than expanding the report.

When all material claims are independently settled:

```text
SHOWMEWHY

<one-line result>

VERIFIED
<compact count or strongest witness summary>

DO NEXT
No material verification gap found.
```

When a material claim is refuted, do not preserve the original conclusion as if it were still valid. State the narrower or corrected result first, then surface the refuted claim under `NEEDS YOU`.

## Choosing DO NEXT

`DO NEXT` is not a generic helpful suggestion. It must be the single action most likely to close the highest-consequence unresolved verification obligation.

Priority order:

1. blocking unresolved claim
2. security, safety, legal, financial, or destructive-risk gap
3. refuted material claim
4. missing boundary or compatibility witness
5. missing regression or counterexample witness
6. missing measurement/source support
7. no action required

Prefer a concrete verification action over "review this", "investigate further", or "check the logs".

## `why` mode

`why` expands the verification ledger without reverting to a graph or essay. Prefer a compact table or aligned list:

```text
CLAIM   STATE      WITNESS / GAP
C1      VERIFIED   auth.spec.ts::valid_audience -> 200
C2      OPEN       no pre-migration mobile token exercised
C3      REFUTED    Schedule B still says 30 days
```

Include only observable witness references and missing obligations. Do not expose private reasoning.

## Visuals

Verification itself is not visualised as a DAG. Read `references/representation-routing.md` only when the **subject matter** genuinely benefits from a table, timeline, hierarchy, architecture diagram, distribution, or comparison. The verification surface remains `VERIFIED / NEEDS YOU / DO NEXT`.

## `monitor` mode

MONITOR is session-level telemetry, not default output. Use it only when explicitly invoked or when the user explicitly asks for end-of-session verification state.

```text
MONITOR
Verified  <count>
Open      <count>
Refuted   <count>
Risk      LOW | MEDIUM | HIGH
Next      <highest-value unresolved verification action>
```

Do not add token reward bands to ordinary ShowMeWhy responses.

## `impact` mode

Only in `impact` mode (or when the user explicitly asks), report token/context reduction and operational-impact estimates. Distinguish presentation reduction from material genuinely prevented from entering later model context. Never claim already-spent compute was undone.

For carbon methodology, read `references/impact-methodology.md` and use `scripts/impact.py` when available.

## `json` mode

Emit only a JSON object matching `references/verification-surface.schema.json`. Do not fabricate witnesses, closure states, sources, risk, counts, or next actions just to populate the schema.

When tool execution is available and a structured verification manifest exists, `scripts/verification_surface.py` provides the deterministic reference closure and rendering behaviour.

## Stop condition

Stop when the user can answer three questions:

1. What is the result?
2. What material part of it is still unverified or refuted?
3. What single action would most reduce that remaining verification debt?

Do not add a generic recap or closing paragraph.
