# Changelog

## 3.0.0 - 2026-09-15

### Added

- Typed provenance graphs generated from V2 execution digests and retained raw evidence.
- Stable `evidence://` and `run://` addresses for inspectable evidence paths.
- Typed provenance nodes and relationships for observations, evidence, conclusions, caveats, artefacts and changes.
- Qualitative provenance confidence derived from parser confidence and completeness.
- Deterministic run comparison for status, findings and compression deltas.
- Local static provenance viewer with HTML escaping.
- CLI commands for provenance inspection, run comparison and viewer generation.

### Safety

- `CAUSED_BY` edges require an explicit `causal_basis`; unsupported causal claims are rejected.
- Provenance failure never destroys retained raw evidence or blocks the V2 fail-open compression path.

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

- Formal ShowMeWhy Receipt V1 contract and JSON Schema.
- `/showmewhy json` machine-readable receipt mode.
- Zero-dependency receipt validator.
- Explicit representation-routing grammar.
- 108-case behavioural benchmark matrix across nine task categories.
- Platform notes for Claude Code, Codex, and Cowork/knowledge-work usage.

## 0.1.1 — Repository hygiene

- Added MIT licence, contribution/branch policy, security guidance, PR template, and CI matrix.

## 0.1.0 — V0

- Added explicit `/showmewhy` Agent Skill invocation, visual/evidence contract, risk/reward monitor, token/CO2e receipt, examples, and evals.
