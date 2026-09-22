# V5 pilot corpus

This directory freezes the **selection** for the first V5 real-world pilot. It does not contain ShowMeWhy benchmark results.

The pilot contains six accepted upstream fixes chosen for six different verification shapes: state restoration, schema/runtime semantics, provenance attribution, protocol parsing, runtime/generated-spec consistency, and static-analysis boundary logic.

## Why six first

The full V5 target remains a frozen 30–50 task corpus spanning code, security, infrastructure/configuration, research claims, architecture decisions, and migrations/compatibility. Before scaling, this six-task pilot tests whether the execution protocol itself is reproducible: exact checkout, task prompt identity, baseline/ShowMeWhy pairing, oracle construction, independent labelling, and scorer ingestion.

The pilot is therefore **not representative coverage of the final domains**. In particular, it must not be presented as the final security/infrastructure/research benchmark.

## Selection requirements

A task is admitted only when:

1. the upstream fix was merged into the canonical repository;
2. the pre-fix revision is pinned to the PR base SHA;
3. the accepted fix supplies a narrow regression witness or deterministic equivalent;
4. expected pre-fix and post-fix behaviour can be stated without relying on ShowMeWhy output;
5. material boundaries and out-of-scope behaviour are recorded explicitly.

Closed-but-unmerged or superseded patches are excluded, even when their proposed fix looks plausible.

## Current state

Every task in `manifest.json` is intentionally marked:

```text
selection_status = selected_unexecuted
execution_status = not_run
```

This means we have inspected upstream evidence and frozen candidate tasks, but **we have not yet executed the paired baseline and ShowMeWhy benchmark runs**. The manifest must never be converted into a scored V5 corpus by filling in guessed outcomes.

## Execution sequence

For each task:

1. checkout `pre_fix_revision` in an isolated worktree/container;
2. verify that the recorded reproducer fails for the expected reason;
3. verify the upstream accepted fix/oracle independently at `accepted_fix_revision`;
4. freeze the task prompt and verify its SHA-256;
5. execute the coding agent **once** from the frozen oracle-free spec in `pairs/<task-id>.json` with `pair_runner.py`;
6. clone the exact completed workspace and baseline result, then run ShowMeWhy post-hoc without `Edit`/`Write`; reject the pair if the verifier changes the workspace;
7. retain the raw Claude JSON, final result, workspace diff/status and adapter metadata for the task result and verification phase;
8. create ground truth with `record_builder.py ground-truth-template` **before inspecting either captured output**;
9. label material claims, failures, human-review obligations and counterexamples independently, then adjudicate disagreements;
10. generate an assessment packet from the captured outputs, map them to the frozen claim/counterexample IDs, and record every evidence artifact the reviewer actually inspected;
11. assemble a record conforming to `evals/v5/schema.json` and run `scorer.py`.

If step 2 or step 3 is not reproducible in our environment, the task is rejected or repaired before any paired run is counted.

## Publication boundary

Upstream merged PRs are **oracle sources**, not evidence that ShowMeWhy performs well. No verification-reduction, failure-recall, false-closure, or counterexample metric may be computed from this selection manifest.

## Frozen execution packet

Each selected task now has an oracle-free pair spec under `pairs/`. The six specs pin:

- the pre-fix revision;
- exact prompt bytes and SHA-256;
- `claude-sonnet-5`;
- `claude-code-cli@2.1.278`;
- `v5-posthoc-bare-v2`;
- repeat index 0;
- the portable V5 Claude adapter command.

The pair specs intentionally contain **no** accepted-fix revision, oracle references, expected failure description or ground-truth labels. `pair_runner.py` rejects those fields recursively if they are introduced.

The ShowMeWhy treatment uses the current repository's canonical `SKILL.md` contract and records its SHA-256. The optional context-compression runtime is excluded from the treatment variable.

## Execution status

The presence of pair specs and a runnable workflow does not change the selection manifest's status. Keep `selection_status=selected_unexecuted` and `execution_status=not_run` until a valid raw pair actually exists for that task. Do not commit guessed measurements back into `manifest.json`.
