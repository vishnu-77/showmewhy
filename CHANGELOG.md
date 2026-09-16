# Changelog

## 4.1.1 - 2026-09-16

### Fixed

- ShowMeWhy now ships its Skill and runtime as one marketplace-managed plugin so updates are atomic instead of leaving a copied personal Skill stale.
- The installer removes the legacy `~/.claude/skills/showmewhy` copy and enables marketplace `autoUpdate` for ShowMeWhy.
- `plugin.json` no longer pins an explicit semantic version; Claude can use the Git commit SHA as the plugin update key, so each new upstream commit is distinguishable without a manual plugin-version bump.
- A fresh ShowMeWhy invocation with a question now answers or investigates that question directly instead of requiring an earlier answer in the conversation.
- Causal provenance guidance now treats `CAUSED_BY` as a high-evidence relation and distinguishes a missing guard/validator from the actual cause of a defect.
- Quantified conclusions such as "4 fixes" must have evidence coverage for the stated count or be explicitly qualified.

### Validation

- Installer acceptance verifies `autoUpdate: true`, removes the legacy copied Skill, and confirms the marketplace-managed Skill is present with the runtime on Ubuntu, macOS and Windows.

## 4.1.0 - 2026-09-16

### Changed

- The user-facing Claude Code command is now installed as a personal Skill, so the normal invocation is `/showmewhy` rather than the plugin-namespaced `/showmewhy:showmewhy` form.
- The Claude plugin is runtime-only and no longer contributes an auto-discovered ShowMeWhy Skill.
- The canonical standalone Skill source now lives under `standalone/showmewhy/`.
- Public documentation now presents ShowMeWhy as one product with a clean command surface and a separate local runtime implementation.

### Added

- Idempotent `install.sh` for macOS, Linux and WSL.
- Idempotent `install.ps1` for Windows PowerShell.
- Cross-platform installer acceptance that runs the installer twice on Ubuntu, macOS and Windows and verifies the personal Skill, runtime plugin and absence of a namespaced plugin Skill.
- A redesigned, version-agnostic README organised around the ShowMeWhy Receipt, proof gates, architecture and trust invariants.

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
- Raw evidence remains the source of truth and fail-open behaviour is preserved.

## 3.0.0 - 2026-09-15

- Added typed provenance graphs grounded in execution digests and raw evidence.
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

## 0.1.0 — Initial prototype

- Added `/showmewhy`, visual/evidence contract, risk/reward monitor, token/CO2e receipt, examples, and evals.
