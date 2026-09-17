---
name: showmewhy
description: Verify a fresh answer or completed agent result, independently settle material claims where possible, surface only the smallest remaining verification gap, and detect when new evidence changes an earlier conclusion or relied-upon assumption.
argument-hint: "[short|why|compare|monitor|impact|json|deep|status|update] [question or scope] | /stage [/stage ...] -- [task]"
user-invocable: true
disable-model-invocation: true
---

# ShowMeWhy

ShowMeWhy answers one question: **what still needs human verification before this result should be trusted?**

The default response is not a summary, report, graph, or chain-of-thought. Internally, decompose the result into material claims, define what would establish or refute each claim, gather observable witnesses, scrutinise them, and close what can be independently settled. Externally, show only the unresolved verification surface and one next action.

When the current evidence materially changes a previous conclusion, plan, or assumption, ShowMeWhy should automatically switch to a compact **Context Delta** surface: what changed, which assumption broke, what new evidence caused the change, what it affects, and what to do next. This is an internal renderer, **not a new user mode**.

Never expose, reconstruct, or claim to expose private chain-of-thought. Agent assertions, prior prose, confidence language, or a model saying "done" are not independent evidence.

## Invocation semantics

Interpret `$ARGUMENTS` as an optional mode followed by optional scope.

- no mode: verification surface, or Context Delta when a material state change is detected; 220-token soft budget
- `short`: one unresolved claim and one next action, 100-token soft budget
- `why`: expanded claim / witness / gap ledger, 450-token soft budget
- `compare`: compact comparison, normally a Markdown table, 300-token soft budget
- `monitor`: session-level verification state only; never include this automatically in ordinary runs
- `impact`: context/token/operational-impact accounting only
- `json`: emit the applicable machine-readable Verification Surface or Context Delta object
- `deep`: perform broader verification for complex or high-consequence work, while keeping the final human surface gap-first, 700-token soft budget
- `status`: inspect the installed ShowMeWhy/Claude plugin state; do not run the verification pipeline
- `update`: update ShowMeWhy through Claude Code's native plugin updater; do not run the verification pipeline

Lifecycle modes (`status`, `update`) take precedence over ordinary task interpretation. They are not verification subjects and are not composition stages.

### Lifecycle modes

#### `status`

When the first argument is `status`, report the current ShowMeWhy installation state rather than verifying the previous answer.

Use observable local state. Prefer:

```text
claude plugin list --json
claude plugin marketplace list --json
```

Read `${CLAUDE_PLUGIN_ROOT}/VERSION` when available to report the version bundled with the currently loaded plugin. If auto-update state can be inspected from Claude's marketplace state, report it; otherwise say `unknown` rather than assuming it is enabled.

Render only:

```text
SHOWMEWHY · STATUS

Version      <version or unknown>
Plugin       healthy | missing | error | unknown
Marketplace  showmewhy | missing | unknown
Updates      automatic | manual | disabled | unknown
State        global project-scoped

DO NEXT
<No action required. | one concrete repair/update action>
```

Do not expose home-directory paths, raw registry JSON, credentials, tokens, or unrelated plugins unless needed to explain a failure.

#### `update`

When the first argument is `update`, use Claude Code's native plugin updater for ShowMeWhy:

```text
claude plugin update showmewhy@showmewhy --scope user
```

Then verify the installed state with:

```text
claude plugin list --json
```

Do **not** uninstall/reinstall as the normal update path. Do not update unrelated plugins or marketplaces. If the updater reports that the installed version is already current, report that directly.

If an update is installed on disk, explain that the current Claude session may still be using the version loaded at session start. The next action is:

```text
/reload-plugins
```

or start a new Claude Code session. Do not claim the current invocation switched to the new contract unless it was actually reloaded.

Render only:

```text
SHOWMEWHY · UPDATE

<Updated <before> -> <after>. | Already current at <version>. | Update failed.>

DO NEXT
</reload-plugins | Restart Claude Code. | one concrete recovery action>
```

Never fabricate before/after versions. If a version cannot be established, report only the updater's observable result.

Existing mode syntax remains valid. Composition is opt-in only when the first argument after the real `/showmewhy` invocation is itself slash-prefixed.

### Embedded multi-stage composition

ShowMeWhy may compose several behaviours while exposing **only one Claude Code command: `/showmewhy`**.

Example:

```text
/showmewhy /monitor /showmewhy /i-have-adhd -- investigate why auth tests fail
```

Only the first `/showmewhy` is a Claude Code command invocation. Everything after it is `$ARGUMENTS`. Interpret the leading slash-prefixed tokens as a **ShowMeWhy-owned composition DSL**, never as requests to invoke other slash commands.

For the example above, normalise the stages to:

```text
monitor -> verify -> focus
```

The embedded `/showmewhy` token means the ordinary ShowMeWhy verifier. `/i-have-adhd`, `/focus`, and `/concise` are compatibility aliases for ShowMeWhy's own `focus` presentation stage; they do **not** invoke, load, depend on, or claim to reproduce any external skill.

Use `--` to separate composition stages from task text:

```text
/showmewhy <stage> [<stage> ...] -- [task]
```

When task text follows composition stages, require `--`. This is a safety boundary so paths, URLs, flags, and ordinary slash-prefixed text inside the task are not mistaken for stages. If no task follows, apply the composed stages to the most recent substantive answer, result, investigation, change, or decision.

Supported stage tokens:

- `/monitor` -> gather session-level observable verification state and risk signals; must be first when composed
- `/showmewhy`, `/verify` -> run ordinary claim / obligation / witness / scrutiny / closure verification
- `/deep` -> broaden verification obligations for complex or high-consequence work
- `/compare` -> compare alternatives or earlier/current states using equivalent evidence obligations
- `/why` -> render the expanded claim/witness/gap ledger
- `/short` -> render the shortest gap-first surface
- `/focus`, `/concise`, `/i-have-adhd` -> render one scannable result, decisive evidence/gap, and one next action
- `/impact` -> add context/token/operational-impact accounting; terminal except that `/json` may follow
- `/json` -> emit machine-readable output; must be final

Composition stages operate on one evolving internal handoff state containing the task, observations, evidence references, material claims, closure states, optional Context Delta, risk, next action, and presentation preference. A later stage may enrich or re-render that state but must not silently discard evidence, caveats, `OPEN` claims, or `REFUTED` claims produced by an earlier stage.

Rules:

1. `monitor` gathers observable state; it does not substitute for verification.
2. A presentation stage without an explicit verification stage gets `verify` inserted before it.
3. `monitor` must be first when present.
4. Select at most one presentation stage: `why`, `short`, `focus`, or `json`.
5. `json` must be final.
6. `impact` must be final, or immediately before `json`.
7. Unknown slash-prefixed stage tokens fail closed with a supported-stage error; never try to execute them as external commands.
8. Repeated adjacent aliases that normalise to the same stage may be collapsed.
9. Existing Context Delta behaviour remains automatic inside verification; do not introduce `/delta`.
10. Never expose private reasoning while handing state between stages.
11. `status` and `update` are lifecycle modes, not stages; reject `/status` or `/update` inside a composition pipeline.

When deterministic parsing is useful, use `scripts/compose.py`. Read `references/composition.md` for the full grammar and stage contract.

If the arguments contain a fresh question or task, answer or investigate it first, then verify the material claims in that result. **Do not refuse merely because no prior answer exists.** Use tools, files, tests, commands, web research, measurements, or source inspection when needed.

If no fresh question is supplied, verify the most recent substantive answer, task result, investigation, change, or decision. Reuse current evidence when it is still valid; independently re-check material claims when the original evidence is missing, stale, self-reported, or insufficient.

If the current conversation contains an earlier conclusion or plan and later evidence materially changes it, compare the two states before rendering the answer. Do not narrate the chronology of how the agent eventually noticed the issue. Surface the decision-relevant delta.

## Internal verification pipeline

Do this internally; do not print the pipeline as a flow diagram.

1. **CLAIM** — extract the smallest set of material claims whose truth would change whether the result should be trusted or acted on.
2. **OBLIGATION** — for each claim, state what would establish or refute it. Broad, causal, universal, security-sensitive, or high-consequence claims need stronger obligations.
3. **WITNESS** — gather observable evidence. Prefer executable or independently inspectable witnesses over model prose.
4. **SCRUTINY** — check that the witness actually addresses the claim, is current, and is not merely evidence that an action happened.
5. **CLOSURE** — mark the claim `VERIFIED`, `REFUTED`, or `OPEN`.
6. **SURFACE** — show only material `OPEN` or `REFUTED` claims by default.

Read `references/receipt-contract.md` for the human contract and `references/verification-surface.schema.json` for machine-readable verification output.

## Temporal verification: Context Delta

Context Delta extends the same verification engine across time. It does **not** replace claim/witness closure.

Use it when all three are present:

1. an earlier material conclusion, plan, or decision exists;
2. new observable evidence arrives later;
3. that evidence changes a material claim state, invalidates a relied-upon assumption, or reveals a context area whose absence mattered.

Internally track four additional objects:

- **CONTEXT SET** — evidence domains or systems actually inspected for the earlier conclusion
- **ASSUMPTION** — a proposition that had to hold for that conclusion to remain valid
- **INVALIDATOR** — new observable evidence that contradicts the assumption or degrades the earlier claim
- **DELTA** — the material difference between the previous and current verification states

A Context Delta should be derived from observable state transitions such as `VERIFIED -> REFUTED`, `VERIFIED -> OPEN`, `OPEN -> VERIFIED`, or an invalidated assumption. Do not invent a broken assumption merely to create a Delta.

When available, `scripts/context_delta.py` is the deterministic reference implementation and `references/context-delta.schema.json` is the machine contract.

### Delta human output

When a material state change exists, prefer this instead of the ordinary verification surface:

```text
SHOWMEWHY · DELTA

CHANGED
<current narrow conclusion>

BROKEN ASSUMPTION
<one relied-upon assumption invalidated by new evidence>

NEW EVIDENCE
<smallest decisive new witness>

IMPACT
<what this changes or blocks, only if material>

MISSED
<context area absent from the earlier decision surface, only when observable>

BLOCKER
<explicit blocker, only when one exists>

DO NEXT
<one action that resolves the highest-value changed obligation>
```

Omit empty sections. Show one broken assumption by default. Do not turn Context Delta into a retrospective essay, self-defence, or a chronology of agent actions.

If new evidence improves rather than degrades the state, use `RESOLVED` instead of `CHANGED`. If no material state changed, keep the normal verification surface; do not manufacture a Delta.

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

If the current surface is a Delta, `why` may additionally show the changed claim state, relied-upon assumption, invalidating witness, and missing context area. Keep it a ledger, not a chronology.

Include only observable witness references and missing obligations. Do not expose private reasoning.

## Visuals

Verification itself is not visualised as a DAG. Read `references/representation-routing.md` only when the **subject matter** genuinely benefits from a table, timeline, hierarchy, architecture diagram, distribution, or comparison. The verification surface remains `VERIFIED / NEEDS YOU / DO NEXT`; Context Delta remains `CHANGED / BROKEN ASSUMPTION / DO NEXT`.

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

Emit only a JSON object matching the applicable machine contract: `references/verification-surface.schema.json` for an ordinary surface or `references/context-delta.schema.json` for temporal state changes. Do not fabricate witnesses, closure states, assumptions, sources, coverage, risk, counts, or next actions just to populate a schema.

When tool execution is available and a structured verification manifest exists, `scripts/verification_surface.py` provides deterministic reference closure and rendering behaviour. For temporal comparison, use `scripts/context_delta.py` when the before/current evidence states can be represented honestly.

## Stop condition

Stop when the user can answer three questions:

1. What is the result now?
2. What material part is still unverified/refuted, or what changed from the prior result?
3. What single action would most reduce the remaining verification debt?

Do not add a generic recap or closing paragraph.
