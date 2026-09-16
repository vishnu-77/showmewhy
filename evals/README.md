# ShowMeWhy evals

The suite combines the original deterministic contracts/108-case routing matrix with V2 verification-surface reference cases.

Run everything:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

## What the deterministic tests enforce

- impact arithmetic and terminology;
- legacy monitor bounds and compatibility;
- Skill output/verification invariants;
- ShowMeWhy Receipt V1 compatibility;
- V2 claim → obligation → witness → closure behaviour;
- refuting evidence outranking supporting evidence;
- missing required witness kinds keeping a claim `OPEN`;
- agent assertions not counting as supported witness types;
- default human output exposing no more than three unresolved material claims;
- 500-claim scale behaviour: 497 settled claims are not replayed when only 3 remain open;
- plugin/marketplace packaging and cross-platform installer acceptance.

## Domain reference cases

`evals/reference_cases/` contains deterministic fixtures for code, policy, research, contracts, data and architecture. These are intentionally different verification shapes: compatibility gaps, universal-claim counterexamples, measurement gaps, contradictions, semantic data boundaries and shared-dependency failures.

They are reference behaviour, not evidence that every real-world claim can be verified automatically. When no valid oracle or witness can be established, the required output state is `OPEN`.

The older behavioural benchmark cases remain prompts/expectations for cross-agent evaluation. Static unit tests do not prove human preference or semantic correctness; those require recorded model runs and independent scoring.
