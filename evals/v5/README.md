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

These are paired against the same task executed without ShowMeWhy.

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

## Running the scorer

```bash
python evals/v5/scorer.py evals/v5/fixtures/smoke.json --pretty
```

The smoke fixture proves arithmetic and schema behaviour only. It is **not** evidence of product effectiveness and must never be reported as a benchmark result.

## Publication rule

Do not publish a claim such as “ShowMeWhy reduces verification by X%” until the real corpus has been frozen, independently labelled, executed, and scored. Report baseline and ShowMeWhy material-failure recall, false closures, failure precision, and verification-surface recall beside any verification-reduction number.
