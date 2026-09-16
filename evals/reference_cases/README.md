# Verification reference cases

These fixtures battle-test the domain-general ShowMeWhy verification surface without relying on a model to grade itself.

Each case contains:

- a result to verify
- material claims
- explicit verification obligations
- observable witnesses
- expected closure (`verified`, `open`, `refuted`)
- the expected highest-value next claim

Current domains:

| Fixture | Domain | Expected stress |
|---|---|---|
| `code-auth.json` | code / identity | compatibility witness missing |
| `policy-mfa.json` | policy / access control | universal claim refuted by exception |
| `research-energy.json` | research | measured token claim vs estimated energy claim |
| `contract-notice.json` | legal / contract text | cross-document contradiction |
| `data-migration.json` | data | row-count success vs downstream semantic gap |
| `architecture-spof.json` | architecture | positive redundancy evidence defeated by shared dependency |

Run all deterministic tests:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

Render one reference surface directly:

```bash
python skills/showmewhy/scripts/verification_surface.py evals/reference_cases/code-auth.json
python skills/showmewhy/scripts/verification_surface.py evals/reference_cases/code-auth.json --mode why
```

The scale test in `evals/test_verification_surface.py` also creates a synthetic 500-claim result with 497 verified claims and 3 open claims. The default human output must surface only the three unresolved claims and must not replay the 497 settled claims.

These are behavioural reference fixtures, not claims that every domain can be fully verified automatically. When a valid oracle or witness cannot be established, the correct state is `OPEN`.
