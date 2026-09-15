# Debugging

## Source situation

A test run contains hundreds of passing cases, five authentication failures, a recent middleware change, and a status-code regression from 401 to 200.

## `/showmewhy`

```text
AUTH REGRESSION

5 / 428 tests failed. All failures cross the modified session-validation path.

WHY

middleware changed
      ↓
expiry validation skipped
      ↓
expired session accepted
      ↓
401 became 200
      ↓
5 auth tests fail

Confidence: HIGH

────────────────────────────────
ShowMeWhy · ~118 / 300 tokens · ↓ 70%
Est. operational CO₂e equivalent · reference estimate*
```
