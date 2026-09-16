# Session monitor

MONITOR is **session-level verification state**, not a footer for every ShowMeWhy response.

Use it only when the user explicitly invokes `monitor` or asks for an end-of-session verification summary.

```text
MONITOR
Verified  <count>
Open      <count>
Refuted   <count>
Risk      LOW | MEDIUM | HIGH
Next      <highest-value unresolved verification action>
```

## Risk derivation

- `HIGH` — one or more unresolved/refuted material claims are explicitly high-risk
- `MEDIUM` — unresolved/refuted material claims remain, but none are marked high-risk
- `LOW` — no material verification gap remains

MONITOR does not contain token reward bands. Context/token/operational-impact accounting belongs to explicit `impact` mode.

The deterministic helper is `scripts/monitor.py`.
