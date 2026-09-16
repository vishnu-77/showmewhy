# Risk / Reward Monitor

ShowMeWhy uses a small deterministic monitor to prevent a concise answer from becoming an unsupported assertion.

## Required monitor fields

For substantive debugging, security, architecture, or operational conclusions, include:

```text
MONITOR
Evidence  <one directly verifiable line>
Guard     <one concrete recurrence-detection check>
Risk      LOW | MEDIUM | HIGH
Budget    <recommended next-task token budget>
```

### Evidence line

The evidence line must be independently checkable. Prefer one of these forms:

- `test/file::test_name — failed before fix, passes after fix`
- `path/to/file.ts:84 — expiry check removed in commit 8ab21`
- `command -> observed result`
- `source/citation -> exact relevant finding`

Do not use generic claims such as `the logs confirm it`, `tests look good`, or `the code proves it`.

If the evidence cannot be tied to an observable source, mark it `UNVERIFIED`.

### Guard line

The guard is the concrete check that should detect the same failure class if it returns. Examples:

- named regression test that must remain green
- CI policy/check that must remain enabled
- assertion/invariant and its location
- monitor/alert and trigger condition

A guard reduces recurrence risk; it does not guarantee recurrence is impossible.

## Budget state

Two deterministic bands exist:

| State | Requirement | Next-task budget band |
|---|---|---:|
| REWARDED | direct/verifiable evidence **and** concrete guard | 1,200–2,000 tokens |
| CONSTRAINED | evidence unverified or guard missing | 800–1,800 tokens |

Risk selects the recommendation within the active band:

| State | LOW | MEDIUM | HIGH |
|---|---:|---:|---:|
| REWARDED | 2,000 | 1,600 | 1,200 |
| CONSTRAINED | 1,800 | 1,300 | 800 |

This is a next-task budget recommendation in the Skill-only V0. Hosts that cannot persist or enforce budgets should display it but must not claim runtime enforcement. A later runtime hook may enforce the recommendation automatically.

## Risk classification

- **LOW** — conclusion directly verified; limited blast radius; guard covers the identified failure.
- **MEDIUM** — conclusion has evidence but incomplete coverage, assumptions, or moderate blast radius.
- **HIGH** — security/safety/reliability impact, broad blast radius, conflicting evidence, or important uncertainty remains.

Risk is not a confidence synonym. A conclusion can have HIGH confidence and HIGH operational risk.

## Example

```text
MONITOR
Evidence  tests/auth.spec.ts::rejects_expired_session — FAIL before fix, PASS after fix
Guard     CI must keep `rejects_expired_session` green
Risk      MEDIUM
Budget    1,600 / 2,000 tokens · REWARDED
```
