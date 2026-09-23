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

V5 is **provider-neutral**. ShowMeWhy does not select, install, authenticate to, or call a model provider as part of the benchmark repository.

The frozen pilot task files contain only the task identity, repository/revision, prompt hash and repeat index. Model identity, agent runtime, tool profile, adapter command, timeout and any provider-specific environment variables are supplied explicitly **at execution time**.

The runner still enforces the experimental invariant:

1. execute the coding task exactly once;
2. freeze that completed workspace and final agent result;
3. run ShowMeWhy post-hoc against the exact same workspace;
4. reject the pair if verification changes any Git-visible workspace state;
5. keep ground truth completely outside both executions.

This evaluates the **ShowMeWhy verification contract**, not a particular model vendor and not the optional Bash compression runtime.

### Adapter contract

The execution command is an external adapter chosen by the evaluator. See [`ADAPTER_PROTOCOL.md`](ADAPTER_PROTOCOL.md).

At run time set:

~~~bash
export SHOWMEWHY_V5_EXECUTION_MODEL='your-model-id'
export SHOWMEWHY_V5_EXECUTION_RUNTIME='your-agent-runtime@version'
export SHOWMEWHY_V5_EXECUTION_TOOL_PROFILE='your-tool-policy'
export SHOWMEWHY_V5_ADAPTER_ARGV_JSON='["python","/absolute/path/to/adapter.py"]'
~~~

If the adapter needs provider credentials or other variables, pass **names only**:

~~~bash
export SHOWMEWHY_V5_ADAPTER_PASS_ENV_JSON='["YOUR_PROVIDER_TOKEN"]'
~~~

The runner inherits no provider credential by default. Secret values are never written to the pair bundle.

Then run one frozen task:

~~~bash
python evals/v5/pair_runner.py \
  evals/v5/pilot/pairs/pytest-monkeypatch-inherited-state.json \
  --source-checkout /path/to/pytest \
  --output-dir /path/to/v5-runs
~~~

The adapter receives the condition, prompt, workspace and output paths through the documented V5 environment contract. It must persist a non-empty `result.txt`. Provider-specific raw traces and usage/cost metadata may be retained as additional adapter artifacts.

There is intentionally **no automatic provider-backed GitHub Actions workflow**. Paid or authenticated model execution must be initiated explicitly outside the repository's default CI.

### Blinded labelling and assessment

A raw pair is not scoreable. First create the ground-truth packet:

~~~bash
python evals/v5/record_builder.py ground-truth-template \
  --manifest evals/v5/pilot/manifest.json \
  --pair /path/to/pair/pair.json \
  --task-id pytest-monkeypatch-inherited-state \
  --out ground-truth.json
~~~

This operation does **not** open either condition's `result.txt`, stdout, diff or adapter metadata. The independent labeler fills `claims`, `labeler_count`, adjudication state, and explicitly sets `blinded_to_showmewhy=true` only when that procedure was actually followed.

Then generate an assessment packet:

~~~bash
python evals/v5/record_builder.py assessment-template \
  --pair /path/to/pair/pair.json \
  --ground-truth ground-truth.json \
  --out assessment.json
~~~

The assessment exposes captured condition outputs but not ground-truth labels during timed review. Every evidence artifact actually inspected must be recorded by relative path and SHA-256. Ground-truth ID mapping happens only after the timer stops.

Finally:

~~~bash
python evals/v5/record_builder.py assemble \
  --pair /path/to/pair/pair.json \
  --ground-truth ground-truth.json \
  --assessment assessment.json \
  --out scoreable-record.json
~~~

A raw pair remains **execution evidence, not a benchmark result** until independent labelling and assessment are complete.
