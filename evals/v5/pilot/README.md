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
5. run the baseline agent and ShowMeWhy condition with the same model, runtime, tools, repository revision and repeat index;
6. capture inspection tokens/lines/time and machine-readable claim state;
7. label ground truth independently, blinded to the ShowMeWhy condition;
8. adjudicate disagreements;
9. only then create a record conforming to `evals/v5/schema.json` and score it.

If step 2 or step 3 is not reproducible in our environment, the task is rejected or repaired before any paired run is counted.

## Publication boundary

Upstream merged PRs are **oracle sources**, not evidence that ShowMeWhy performs well. No verification-reduction, failure-recall, false-closure, or counterexample metric may be computed from this selection manifest.
