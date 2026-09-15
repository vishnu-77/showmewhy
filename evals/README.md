# ShowMeWhy evals

The V1 suite contains deterministic contract tests plus a 108-case behavioural benchmark matrix spanning debugging, architecture, security, research, comparison, planning, code review, CI/build output and simple answers.

Run:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

## What the deterministic tests enforce

- impact arithmetic and terminology;
- risk/reward monitor bounds;
- skill contract invariants;
- ShowMeWhy Receipt V1 structure;
- benchmark size, category coverage and routing expectations.

The behavioural cases are prompts/expectations for cross-agent evaluation. They do not pretend that static unit tests can prove human preference or semantic correctness. Those metrics require recorded model runs and human/automated scoring.
