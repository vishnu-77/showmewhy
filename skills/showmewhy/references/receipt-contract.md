# ShowMeWhy Receipt V1

A ShowMeWhy Receipt is a compact explanation contract. Human-facing output does not need to expose JSON, but it must preserve the same semantic fields when they apply.

## Canonical order

```text
CONCLUSION
<answer first>

SIGNAL
<only material facts>

WHY
<shortest evidence path>

CAVEAT
<only if decision-changing>

CONFIDENCE
<only when defensible>

MONITOR
Evidence  <verifiable source-backed line>
Guard     <recurrence-detection check>
Risk      LOW | MEDIUM | HIGH
Budget    <next-task token recommendation>

────────────────────────────────
ShowMeWhy · <used> / <budget> tokens · <reduction>
<impact line when defensible>
```

## Invariants

1. The conclusion is first.
2. Signal contains facts, not narration.
3. WHY is provenance, never hidden chain-of-thought.
4. `CAUSED_BY` requires causal support; otherwise use a weaker relation.
5. Evidence names a source another person could inspect.
6. A guard names the check that detects recurrence; it never promises recurrence is impossible.
7. Confidence and risk are independent.
8. Token and carbon claims distinguish presentation-equivalent reduction from realised runtime avoidance.
9. A simple answer may omit visual, WHY, monitor or impact fields when they add no value.
10. The default human answer should remain understandable without surrounding transcript context.

## Machine-readable contract

The canonical schema is `references/showmewhy-receipt.schema.json`. Future runtimes may emit or consume that representation, but V1 remains human-first.
