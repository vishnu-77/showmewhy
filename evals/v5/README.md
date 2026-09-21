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

`pair_runner.py` executes the baseline and ShowMeWhy conditions without access to benchmark ground truth.

The execution specification is intentionally separate from the scored V5 record. It may contain the task prompt, pinned repository revision, model/runtime/tool profile and adapter command, but the runner rejects oracle/ground-truth fields such as `failing_claim_ids`, `oracle_refs` and `accepted_fix_revision`.

Each pair:

1. hashes the exact task-prompt bytes;
2. creates two detached Git worktrees at the same pinned revision;
3. executes the **same argv** in each worktree;
4. exposes the treatment only through `SHOWMEWHY_V5_CONDITION=baseline|showmewhy`;
5. counterbalances execution order by repeat index (even: baseline first, odd: ShowMeWhy first);
6. persists stdout, stderr, Git status, a binary diff and adapter-produced artifacts;
7. rejects timed-out/non-zero condition runs as an invalid pair;
8. removes worktrees after capture unless `--keep-worktrees` is explicitly requested.

Pair evidence is append-only: an existing `pair_id` is never overwritten.

Example execution specification:

```json
{
  "version": "v5-pair-spec-1",
  "task_id": "pytest-monkeypatch-inherited-state",
  "domain": "code",
  "repository": "pytest-dev/pytest",
  "revision": "<pinned-pre-fix-sha>",
  "task_prompt": "<exact frozen task prompt>",
  "task_prompt_sha256": "<sha256>",
  "model": "<exact model id>",
  "agent_runtime": "claude-code",
  "tool_profile": "v5-code-default",
  "repeat_index": 0,
  "command": {
    "argv": ["python", "/absolute/path/to/v5-agent-adapter.py"],
    "timeout_seconds": 3600,
    "pass_env": ["ANTHROPIC_API_KEY"]
  }
}
```

Run it against a local checkout that already contains the pinned revision:

```bash
python evals/v5/pair_runner.py pair-spec.json \
  --source-checkout /path/to/upstream/repository \
  --output-dir /path/to/v5-runs
```

The adapter receives the same prompt/model/tool metadata in both conditions through environment variables:

- `SHOWMEWHY_V5_CONDITION`
- `SHOWMEWHY_V5_PAIR_ID`
- `SHOWMEWHY_V5_PROMPT_SHA256`
- `SHOWMEWHY_V5_PROMPT_FILE`
- `SHOWMEWHY_V5_OUTPUT_DIR`
- `SHOWMEWHY_V5_WORKSPACE`
- `SHOWMEWHY_V5_MODEL`
- `SHOWMEWHY_V5_AGENT_RUNTIME`
- `SHOWMEWHY_V5_TOOL_PROFILE`

The adapter is responsible for applying the intended treatment: the baseline path must produce the ordinary agent result without invoking ShowMeWhy; the `showmewhy` path must run the same task and then apply ShowMeWhy to that result. The adapter must not read benchmark oracle/ground-truth data.

A `v5-pair-run-1` bundle is **raw execution evidence, not a benchmark score**. It becomes scoreable only after independent blinded labelling maps the captured evidence into the existing `schema.json` record contract.
