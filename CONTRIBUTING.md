# Contributing to ShowMeWhy

ShowMeWhy keeps changes small, reviewable, and evidence-backed.

## Branch model

- `main` — release-ready code only. Tags are cut from `main`.
- `develop` — integration branch for the next release.
- `feature/<short-name>` — normal feature work, branched from `develop` and merged back through a pull request.
- `fix/<short-name>` — non-urgent fixes, branched from `develop`.
- `hotfix/<short-name>` — urgent release fixes, branched from `main`, then merged into both `main` and `develop`.
- `release/<version>` — optional stabilisation branch when a release needs a freeze before `main`.

Do not commit directly to `main` for normal development.

## Typical workflow

```bash
git switch develop
git pull
git switch -c feature/my-change

# make and test the change
python -m unittest discover -s evals -p 'test_*.py'

git push -u origin feature/my-change
```

Open a pull request into `develop`. Keep a pull request focused on one coherent change.

For a release, merge the tested `develop` state into `main`, update `VERSION` and `CHANGELOG.md`, then tag the release from `main`.

## Quality bar

A change should preserve these invariants:

1. Conclusions come before narration.
2. Evidence and inference are distinguishable.
3. The skill never claims to expose private chain-of-thought.
4. Risk and confidence remain separate concepts.
5. Token/CO2e claims use the documented accounting semantics.
6. A recurrence guard is concrete and independently checkable where the monitor is used.
7. Correctness and material caveats take priority over token budgets.

## Tests

Run the full standard-library test suite:

```bash
python -m unittest discover -s evals -p 'test_*.py'
```

New behaviour should include an eval or deterministic unit test where practical.

## Internal material

`internal.md` is intentionally ignored and must never be committed. Product strategy that is not meant for release should remain outside tracked repository history.
