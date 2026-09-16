---
name: showmewhy
description: Answer a fresh question or re-present an existing result as a concise conclusion, useful visual structure, and evidence-backed why graph. Use when the user explicitly invokes ShowMeWhy or asks to show the result and why without verbose narration.
argument-hint: "[short|visual|why|compare|monitor|impact|json|deep] [question or scope]"
user-invocable: true
disable-model-invocation: true
---

# ShowMeWhy

Give the user the shortest justified answer that preserves what matters and why.

Do not expose, reconstruct, or claim to expose private chain-of-thought. The Why view is an evidence/provenance view built from observable facts, cited material, tool results, code, files, measurements, or clearly labelled inference.

## Invocation semantics

Interpret `$ARGUMENTS` as an optional mode followed by optional scope.

- no mode: default response, 300-token soft budget
- `short`: maximum compression, 150-token soft budget
- `visual`: prioritise the most useful visual representation, 350-token soft budget
- `why`: prioritise evidence and provenance, 450-token soft budget
- `compare`: prioritise a compact comparison, normally a Markdown table, 350-token soft budget
- `monitor`: show the one-line evidence, recurrence guard, risk, and deterministic next-task budget
- `impact`: explain the token/CO₂e receipt or calculate it from available counts; do not re-answer the whole topic unless needed
- `json`: emit a machine-readable ShowMeWhy Receipt object conforming to `references/showmewhy-receipt.schema.json`
- `deep`: preserve more detail for complex or high-consequence analysis, 700-token soft budget

If the arguments contain a fresh question or task, answer that question or perform the necessary investigation first, then return the result as a ShowMeWhy Receipt. **Do not refuse merely because no prior answer exists.** Use available tools, files, web research, tests, or measurements when they are needed to answer correctly.

If no fresh question is supplied, apply ShowMeWhy to the most recent substantive answer, investigation, task result, or current topic. Reuse existing evidence rather than repeating expensive work unless the user requests fresh verification or the evidence may be stale.

## Receipt contract

Read `references/receipt-contract.md` before formatting a substantive answer. The human output uses stable semantics: conclusion, signal, optional visual, evidence-backed WHY, caveats/confidence where useful, monitor, and impact. Empty or non-useful sections may be omitted.

For representation choice, read `references/representation-routing.md`. Use the smallest representation that reduces reading.

### `json` mode

When invoked with `json`, emit only a JSON object matching `references/showmewhy-receipt.schema.json`. Use `UNVERIFIED`/`MISSING` strings and `constrained` state when evidence or guard cannot be established. Do not fabricate source references, token counts, carbon estimates, confidence, or causality just to populate the schema.

## Response priority

Spend the token budget in this order:

1. Conclusion
2. Critical evidence or signal
3. Material caveats
4. Why/provenance view
5. Useful visual structure
6. Everything else

Correctness beats compression. Never omit a material security, safety, legal, operational, or decision-changing caveat solely to satisfy the budget.

## Conclusion first

Start with the answer, recommendation, root cause, result, or status. Prefer one to three lines. Do not start by narrating what was inspected, searched, run, considered, or thought about.

Avoid filler such as "I looked through...", "After analysing...", "Here is a detailed breakdown...", or "Based on everything above..." unless that information itself is material evidence.

## Keep only signal

Retain facts that materially support, contradict, constrain, quantify, or qualify the conclusion. Remove repeated tool output, procedural narration, duplicated observations, generic background the user already has, restatements of the question, and decorative commentary.

Prefer concrete numbers, paths, states, deltas, failures, constraints, and named evidence.

### Evidence coverage

Every material quantified claim must be covered by observable evidence. If the conclusion says "4 fixes", "7 failures", or "3 causes", the receipt must either show evidence for each item or explicitly state that only part of the count was independently verified. Do not compress several unsupported claims behind one verified example.

## Choose a visual only when it helps

Read `references/visual-grammar.md` when a visual representation is useful.

Default mapping:

- cause/evidence -> directed Why graph
- comparison -> Markdown table
- ordered sequence -> timeline
- architecture -> component graph
- hierarchy -> tree
- distribution -> compact bars
- dependencies -> dependency graph
- simple result -> no visual

Prefer ASCII or Markdown when sufficient. Use Mermaid only when relationships are too complex for a compact text diagram and the host renders it reliably. Never create a visual merely for decoration.

## Show why with provenance

For substantive conclusions, build the shortest evidence path that justifies the result.

Use these node classes conceptually:

- OBSERVATION: directly observed state, output, measurement, source statement, code, or event
- EVIDENCE: observation relevant to the conclusion
- INFERENCE: a conclusion derived from evidence but not directly observed
- CONCLUSION: the answer being presented
- CAVEAT: evidence or uncertainty limiting the conclusion

Use relationship semantics carefully:

- SUPPORTS
- CONTRADICTS
- DERIVED_FROM
- VERIFIED_BY
- CORRELATED_WITH
- CAUSED_BY

`CAUSED_BY` is a high bar. Use it only when the evidence supports an actual causal relationship through a direct reproduction/intervention, a documented mechanism plus compatible observations, or another explicit causal basis. A missing validator, missing guard, or missing test usually **allowed a defect to pass undetected**; it did not necessarily cause the defect itself. Prefer `SUPPORTS`, `DERIVED_FROM`, or an explicit "allowed to pass undetected" statement when that is what the evidence shows.

A Why graph must never be presented as the model's hidden reasoning trace.

## Risk / reward monitor

For substantive debugging, security, reliability, architecture, or operational conclusions, read `references/risk-reward-monitor.md` and add a compact monitor when it helps the user act on the result.

```text
MONITOR
Evidence  <one independently verifiable line>
Guard     <one concrete recurrence-detection check>
Risk      LOW | MEDIUM | HIGH
Budget    <next-task token recommendation>
```

The **Evidence** line must name an observable source: a test, file/line, command result, measurement, or citation. Generic statements such as `the logs prove it` are not evidence. If no source can be named, mark it `UNVERIFIED`.

The **Guard** line must name the concrete check that would detect recurrence: a regression test, invariant, CI policy, or alert condition. A guard reduces recurrence risk; it does not prove the original defect's cause and does not make recurrence impossible.

Budget state is deterministic:

- direct/verifiable evidence + concrete guard -> `REWARDED`, next-task band **1,200–2,000 tokens**
- unverified evidence or missing guard -> `CONSTRAINED`, next-task band **800–1,800 tokens**

Within the active band, risk selects the recommendation:

- REWARDED: LOW 2,000 · MEDIUM 1,600 · HIGH 1,200
- CONSTRAINED: LOW 1,800 · MEDIUM 1,300 · HIGH 800

Use `scripts/monitor.py` when tool execution is available.

### `monitor` mode

When invoked with `monitor`, return only the current monitor state, evidence line, guard, risk, and next-task budget unless the user asks for more.

## Confidence

Only include confidence when it adds value and can be justified from evidence quality.

- HIGH: multiple direct/independent pieces of evidence or direct verification
- MEDIUM: reasonable inference with incomplete verification
- LOW: limited, indirect, conflicting, or assumption-heavy evidence

Omit confidence rather than manufacture precision. Do not output numeric confidence percentages unless the source or a defined calculation provides them.

## Token budget and receipt

For a substantial transformation, finish with a one- or two-line ShowMeWhy receipt when it does not distract from the answer.

```text
────────────────────────────────
ShowMeWhy · ~184 / 300 tokens · ↓ 72%
Est. operational CO₂e equivalent · ~0.26 g*
```

Rules:

1. Use exact host token counts if available.
2. Otherwise estimate tokens and prefix them with `~`.
3. If estimating from text, use approximately 4 UTF-8/ASCII characters per token only as a rough fallback.
4. `reduction = max(source_tokens - output_tokens, 0)`.
5. `reduction_pct = reduction / source_tokens * 100` when source tokens > 0.
6. The source is the material being re-presented, not the whole conversation unless the whole conversation is actually being compressed.
7. If the source is already-generated text, call the carbon value an **operational CO₂e equivalent**, not realised emissions avoided.
8. Never claim prior compute has been undone.
9. If tokens were genuinely prevented from generation/consumption by a runtime mechanism, `operational CO₂e avoided` is acceptable.

For carbon calculations, read `references/impact-methodology.md`. Use `scripts/impact.py` when tool execution is available and token counts or text are available. If a credible calculation cannot be made, omit the CO₂e number rather than inventing one.

## `impact` mode

When invoked with `impact`:

- report source tokens, output tokens, reduced tokens, reduction percentage and budget usage when available
- report the energy/carbon profile used
- distinguish presentation-equivalent reduction from realised operational avoidance
- show estimate quality
- keep methodology concise

## Stop condition

Stop when the user has enough information to understand:

1. what the answer is,
2. what materially supports it,
3. what important caveat could change it.

Do not add a generic closing paragraph after the answer is complete.
