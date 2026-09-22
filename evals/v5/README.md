# V5 verification benchmark

V5 is an empirical evaluation track, not a feature release. The benchmark asks one question:

> Can ShowMeWhy reduce the amount of evidence a human must inspect while preserving detection of consequential agent errors?

## Primary metrics

1. **Material-failure recall** — fraction of ground-truth material failures detected by ShowMeWhy.
2. **Verification-surface reduction** — reduction in claims a human must inspect versus the paired baseline.

The benchmark must never optimise surface reduction independently of failure recall. Baseline material-failure recall is scored from the paired run, and the scorer reports the ShowMeWhy-minus-baseline recall delta rather than assuming the baseline is perfect.

## Safety diagnostics

- **False-closure rate**: a claim is falsely closed when ShowMeWhy marks it `VERIFIED` even though ground truth says it is failing or still requires human verification.
- **Material-failure miss rate**: complement of ShowMeWhy material-failure recall.
- **Material-failure precision**: distinguishes true detections from false failure alarms.
- **Claim-classification coverage**: fraction of ground-truth material claims that receive `VERIFIED`, `REFUTED`, or `OPEN`.
- **Verification-surface recall**: fraction of claims that truly require human review which are actually surfaced.
- **Verification-surface precision**: fraction of surfaced claims that truly require human review.
- **Counterexample recall/precision**: known decisive counterexamples detected versus spurious counterexample reports.

## Efficiency diagnostics

- inspection-token reduction;
- inspection-line reduction;
- verification-time reduction.

These are measured against the same completed task result: the baseline is the coding agent's original answer, while ShowMeWhy is a post-hoc verification surface over that exact answer and workspace.

## Corpus protocol

The final V5 corpus should contain 30–50 real tasks across at least:

- code changes;
- security fixes;
- infrastructure/configuration;
- research claims;
- architecture decisions;
- migrations/compatibility changes.

Each task must be independently labelled before scoring. Ground truth must identify material claims, known material failures, claims that genuinely require human review, and known decisive counterexamples. Ground truth must not be derived from ShowMeWhy's own output.

Ground-truth records carry oracle references, labeler count, adjudication state, and `blinded_to_showmewhy=true`. Publication-quality corpora should use independent labelers and adjudication for disagreements.

## Pairing contract

Every task records a `pairing` object containing:

- unique `pair_id`;
- repository and exact revision;
- SHA-256 of the task prompt;
- model;
- agent runtime;
- tool-permission profile;
- repeat index.

The baseline and ShowMeWhy runs must share this pairing context. Any intentional difference beyond ShowMeWhy itself must be recorded as a separate pair rather than silently mixed into the comparison.

## Record contract

Each task record contains:

- `ground_truth.material_claim_ids`
- `ground_truth.failing_claim_ids`
- `ground_truth.human_review_claim_ids`
- `ground_truth.counterexample_ids`
- `ground_truth.oracle_refs`
- paired baseline inspection/detection results and cost
- ShowMeWhy closure sets, detected failures/counterexamples and inspection cost

For the default V5 surface, `showmewhy.surfaced_claim_ids` must equal `showmewhy.open_claim_ids`. `VERIFIED`, `REFUTED`, and `OPEN` sets must be pairwise disjoint.

## Pilot corpus

`evals/v5/pilot/` freezes the first six real-world upstream tasks used to validate the execution protocol before scaling to the full corpus. Those records are **selection metadata only**: they contain pinned pre-fix/fix revisions, prompts, reproducers, oracles and boundary notes, but no baseline/ShowMeWhy measurements.

A pilot task becomes scoreable only after its pre-fix reproducer and accepted-fix oracle have been independently reproduced in our environment, paired runs have been captured under the same execution context, and blinded ground truth has been labelled/adjudicated.

## Running the scorer

```bash
python evals/v5/scorer.py evals/v5/fixtures/smoke.json --pretty
```

The smoke fixture proves arithmetic and schema behaviour only. It is **not** evidence of product effectiveness and must never be reported as a benchmark result.

## Publication rule

Do not publish a claim such as “ShowMeWhy reduces verification by X%” until the real corpus has been frozen, independently labelled, executed, and scored. Report baseline and ShowMeWhy material-failure recall, false closures, failure precision, and verification-surface recall beside any verification-reduction number.


## Paired execution

The pilot now has a complete raw-execution path:

- `pilot/pairs/*.json` — six frozen, oracle-free pair specifications;
- `pair_runner.py` — isolated paired worktrees and append-only evidence capture;
- `claude_adapter.py` — controlled Claude Code invocation;
- `record_builder.py` — blinded ground-truth template, assessment packet and scorer-record assembly;
- `.github/workflows/v5-pilot-pairs.yml` — manual authenticated execution, never an automatic effectiveness claim.

### Controlled treatment

Both conditions use the same frozen prompt, repository revision, `claude-sonnet-5`, **Claude Code 2.1.278**, and `v5-posthoc-bare-v2` tool profile.

The coding agent runs **once** in `--bare` mode so personal/project hooks, plugins, skills, MCP servers, auto-memory and `CLAUDE.md` cannot leak into the task result. After that process exits, ShowMeWhy starts as a fresh `--bare` Claude process in the **same completed workspace**, using the captured baseline answer and no `Edit` or `Write` tools. This preserves the exact repository state plus ignored build/test artifacts produced by the task run. The runner fingerprints all Git-visible workspace content before and after verification and invalidates the pair if it changes. The treatment appends the repository's exact canonical `skills/showmewhy/SKILL.md`; the contract SHA-256 is persisted in `adapter.json`.

This deliberately evaluates the **ShowMeWhy verification contract**, not the optional Bash compression hook. Compression can alter active evidence and is therefore outside the V5 treatment variable.

The task execution and post-hoc verification each persist:

- raw Claude JSON;
- Claude stderr;
- final `result.txt`;
- adapter metadata including Claude version, model, usage/cost metadata and treatment hash;
- workspace status and binary diff captured by the pair runner.

A CLI success code is insufficient: the adapter also rejects malformed JSON, `is_error=true`, and empty final results.

### Run one frozen pilot pair

Use a checkout of the upstream subject containing the pinned revision:

```bash
python evals/v5/pair_runner.py \
  evals/v5/pilot/pairs/pytest-monkeypatch-inherited-state.json \
  --source-checkout /path/to/pytest \
  --output-dir /path/to/v5-runs
```

The command template supports `{python}` and `{showmewhy_repo}` placeholders so committed pair specs stay portable. Claude authentication for this protocol must use `ANTHROPIC_API_KEY`. Claude Code `--bare` deliberately disables OAuth/keychain authentication; the runner also forces `DISABLE_AUTOUPDATER=1` so the pinned CLI cannot drift during a pair. Secret values are never written to the bundle.

For GitHub-hosted execution, run **V5 pilot paired execution** manually after configuring `V5_ANTHROPIC_API_KEY`. The workflow uploads raw pair evidence only.

### Blinded labelling and assessment

A raw pair is not scoreable. First create the ground-truth packet:

```bash
python evals/v5/record_builder.py ground-truth-template \
  --manifest evals/v5/pilot/manifest.json \
  --pair /path/to/pair/pair.json \
  --task-id pytest-monkeypatch-inherited-state \
  --out ground-truth.json
```

This operation does **not** open either condition's `result.txt`, stdout, diff or adapter metadata. The independent labeler fills `claims`, `labeler_count`, adjudication state, and explicitly sets `blinded_to_showmewhy=true` only when that procedure was actually followed.

Then generate an assessment packet:

```bash
python evals/v5/record_builder.py assessment-template \
  --pair /path/to/pair/pair.json \
  --ground-truth ground-truth.json \
  --out assessment.json
```

The assessment maps observed baseline/ShowMeWhy outputs to the already-frozen claim IDs and records human verification time. It also maintains an **inspection ledger**: every text artifact the reviewer actually opens must be listed by relative path and SHA-256. The builder derives inspection tokens/lines only from that hash-anchored ledger. Each captured `result.txt` is included by default; if the reviewer opens a diff, test log, source extract, or other evidence, it must be added before assembly. Changing any recorded artifact after assessment invalidates assembly.

Finally:

```bash
python evals/v5/record_builder.py assemble \
  --pair /path/to/pair/pair.json \
  --ground-truth ground-truth.json \
  --assessment assessment.json \
  --out scoreable-record.json
```

The builder derives inspection tokens/lines from the exact inspection ledger, keeps counterexample IDs in their own namespace, validates closure/surface invariants, and emits the existing `schema.json` record consumed by `scorer.py`.

A `v5-pair-run-2` bundle remains **raw execution evidence, not a benchmark result** until this labelling/assessment path is complete.

