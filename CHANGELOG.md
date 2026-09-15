# Changelog

## 2.0.0 - 2026-09-15

### Added

- Optional Claude Code `PostToolUse` runtime for verbose Bash output.
- Content-addressed raw evidence retained before any output replacement.
- Deterministic compression for pytest, Jest/Vitest, TypeScript, lint, git diff, and bounded generic logs.
- Per-run execution digests with raw/digest token accounting and compression percentage.
- Shadow mode for evaluating compression without modifying agent context.
- Local evidence inspection and retention cleanup commands.

### Safety

- Only Bash is intercepted by default.
- Unsupported and short output passes through unchanged.
- Bash response shape and stderr are preserved.
- Generic low-confidence digests are marked incomplete.
- Any storage/replacement failure fails open.

## 1.0.1 - 2026-09-15

- Added Claude plugin and marketplace manifests.
- Added deterministic plugin packaging validation and install guide.

## 1.0.0 - 2026-09-15

### Added

- Formal ShowMeWhy Receipt V1 contract and JSON Schema.
- `/showmewhy json` machine-readable receipt mode.
- Zero-dependency receipt validator.
- Explicit representation-routing grammar.
- 108-case behavioural benchmark matrix across nine task categories.
- Deterministic V1 schema and benchmark integrity tests.
- Platform notes for Claude Code, Codex, and Cowork/knowledge-work usage.

### Changed

- Standardised conclusion, signal, WHY, caveat/confidence, monitor, and impact semantics.
- Clarified that V1 remains a user-invoked skill; runtime context interception is not part of this release.

## 0.1.1 — Repository hygiene

- Added MIT licence, contribution/branch policy, security guidance, PR template, and CI matrix.

## 0.1.0 — V0

- Added explicit `/showmewhy` Agent Skill invocation, visual/evidence contract, risk/reward monitor, token/CO2e receipt, examples, and evals.
