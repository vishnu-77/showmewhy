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
6. after the coding process exits, run ShowMeWhy as a fresh `--bare` process in that exact completed workspace using the captured baseline result and no `Edit`/`Write`; reject the pair if the Git-visible workspace fingerprint changes;
7. retain the raw Claude JSON, final result, workspace diff/status and adapter metadata for the task result and verification phase;
8. create ground truth with `record_builder.py ground-truth-template` **before inspecting either captured output**;
9. label material claims, failures, human-review obligations and counterexamples independently, then adjudicate disagreements;
10. generate an assessment packet from the captured outputs, map them to the frozen claim/counterexample IDs, and record every evidence artifact the reviewer actually inspected;
11. assemble a record conforming to `evals/v5/schema.json` and run `scorer.py`.

If step 2 or step 3 is not reproducible in our environment, the task is rejected or repaired before any paired run is counted.

## Publication boundary

Upstream merged PRs are **oracle sources**, not evidence that ShowMeWhy performs well. No verification-reduction, failure-recall, false-closure, or counterexample metric may be computed from this selection manifest.

## Frozen execution packet

Each selected task has an oracle-free pair spec under `pairs/`. The six specs pin:

- the pre-fix revision;
- exact prompt bytes and SHA-256;
- repeat index 0;
- runtime placeholders only.

They deliberately do **not** pin a model vendor, model name, agent CLI, provider credential or adapter executable. Those execution details are supplied explicitly at run time and recorded into the resulting pair evidence.

The pair specs intentionally contain **no** accepted-fix revision, oracle references, expected failure description or ground-truth labels. `pair_runner.py` rejects those fields recursively if they are introduced.

The ShowMeWhy treatment must use the repository's canonical `SKILL.md` contract. The optional context-compression runtime is excluded from the treatment variable.

See [`../ADAPTER_PROTOCOL.md`](../ADAPTER_PROTOCOL.md) for the provider-neutral execution boundary.

## Execution status

Keep `selection_status=selected_unexecuted` and `execution_status=not_run` until a valid raw pair actually exists for that task. Do not commit guessed measurements back into `manifest.json`.

The September 2026 Anthropic/Claude execution attempt was cancelled during harness validation and produced **no scoreable V5 benchmark result**. Its artifacts may be retained only as infrastructure-debugging evidence and must not be included in effectiveness metrics.
