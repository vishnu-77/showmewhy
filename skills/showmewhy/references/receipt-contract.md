# ShowMeWhy Verification Surface

A ShowMeWhy response is a **verification surface**, not a summary report. Its job is to remove claims that can be independently settled and expose only what still requires human judgement.

## Default human contract

When material gaps remain:

```text
SHOWMEWHY

<one-line result>

NEEDS YOU
1  <unresolved or refuted material claim>
   <why it remains open / what refuted it>

DO NEXT
<one concrete action that would close the highest-value gap>
```

Optional compact tally when it adds value:

```text
12 verified · 2 need you
```

Default output shows at most 3 unresolved items. Additional items are available through `why` mode.

When all material claims are settled:

```text
SHOWMEWHY

<one-line result>

VERIFIED
<compact settlement statement>

DO NEXT
No material verification gap found.
```

## Internal states

Every material claim must end in exactly one state:

- `VERIFIED` — required witnesses support it and no material contradictory witness remains
- `REFUTED` — a current relevant witness directly contradicts it
- `OPEN` — evidence is missing, incomplete, conflicting, stale, unavailable, or requires human judgement

`REFUTED` is settled epistemically but still belongs on the human verification surface because it changes the result or requires action.

## Witnesses

A witness must be observable and claim-relevant. Supported kinds are:

- execution
- source
- measurement
- invariant
- counterexample
- boundary
- regression
- comparison

A witness records a source and one outcome: `supports`, `refutes`, or `inconclusive`.

Agent prose, confidence language, or a prior statement that a task is complete is not a witness.

## Invariants

1. The corrected/narrowest defensible result is first.
2. Verification is claim-level, not line-count-level.
3. Broad or high-consequence claims require stronger obligations than narrow factual claims.
4. A passing action does not automatically verify the semantic claim attached to it.
5. Counterexamples and boundary checks are preferred for universal, safety, compatibility, and no-regression claims.
6. The default surface shows unresolved/refuted claims, not a catalogue of everything already checked.
7. `DO NEXT` must close the highest-consequence open obligation; it is not generic advice.
8. Human output contains no proof DAG by default.
9. MONITOR and impact accounting are explicit modes, not automatic footer content.
10. Private chain-of-thought is never exposed or reconstructed.

## Machine-readable contract

The canonical V2 schema is `references/verification-surface.schema.json`.

The older `showmewhy-receipt.schema.json` remains in the repository for V1 compatibility and historical fixtures; new `json` mode output uses the Verification Surface schema.
