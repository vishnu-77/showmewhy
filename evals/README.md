# Evals

V0 evals focus on five behaviours:

1. conclusion-first concision
2. retention of material facts and caveats
3. appropriate visual selection
4. evidence/inference separation and causal integrity
5. correct token/impact arithmetic

Run the deterministic impact tests with:

```bash
python3 -m unittest evals/test_impact.py -v
```

The cases in `cases.json` are fixtures for agent-level behavioural evaluation. They intentionally avoid prescribing exact wording; the invariant is information quality per token, not template matching.

## Risk / reward monitor

`test_monitor.py` validates the V0 deterministic budget policy:

- verified evidence + recurrence guard -> REWARDED band (1,200–2,000)
- missing verification or guard -> CONSTRAINED band (800–1,800)
- risk chooses the recommendation within the active band

The monitor is advisory in Skill-only V0; it must not claim host-level enforcement.
