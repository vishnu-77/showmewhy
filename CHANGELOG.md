# Changelog

## 4.0.0 - 2026-09-15

### Added

- Local adaptive context policy driven by verified operational feedback rather than task content.
- Feedback signals for raw-evidence reopen events, parser completeness, achieved compression and material information loss.
- Adaptive 500 / 700 / 1,100 token context targets based on observed outcomes.
- Sticky safety lock: any reported material loss forces shadow mode with a 1,200-token threshold until manually cleared.
- `feedback`, `policy`, and `policy-unlock` runtime commands.
- Policy metadata attached to execution digests so each adaptive decision is inspectable.

### Privacy and safety

- Policy feedback stores metrics only; it does not persist prompts, summaries, findings, code or raw tool output.
- Environment or explicit CLI settings can override adaptive mode/target settings.
- Raw evidence remains the source of truth and V2 fail-open behaviour is preserved.

## 3.0.0 - 2026-09-15

- Added typed provenance graphs grounded in V2 digests and raw evidence.
- Added stable `evidence://` and `run://` addresses, causal-edge validation, run comparison and a local static viewer.

## 2.0.0 - 2026-09-15

- Added optional Claude Code Bash `PostToolUse` context compression.
- Added content-addressed raw evidence, deterministic parsers, execution digests, shadow mode and real context-token accounting.

## 1.0.1 - 2026-09-15

- Added Claude plugin and marketplace manifests, deterministic packaging validation and install guide.

## 1.0.0 - 2026-09-15

- Formalised the ShowMeWhy Receipt, JSON schema, representation grammar, 108-case benchmark and platform notes.

## 0.1.1 — Repository hygiene

- Added MIT licence, contribution/branch policy, security guidance, PR template, and CI matrix.

## 0.1.0 — V0

- Added `/showmewhy`, visual/evidence contract, risk/reward monitor, token/CO2e receipt, examples, and evals.
