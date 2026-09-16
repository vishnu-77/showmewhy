# ShowMeWhy installation architecture

ShowMeWhy is distributed as one Claude Code marketplace plugin. The user-facing Skill, hooks and runtime are versioned and cached together so they update atomically.

## Recommended installation

### macOS, Linux and WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.ps1 | iex
```

The installer:

```text
registers ShowMeWhy marketplace over HTTPS
        ↓
enables marketplace autoUpdate
        ↓
removes legacy copied personal Skill
        ↓
installs showmewhy@showmewhy
        ↓
Skill + hooks + runtime update together
```

Claude namespaces Skills distributed through plugins, so the explicit invocation is:

```text
/showmewhy:showmewhy
```

The namespaced command is accepted as a platform constraint in exchange for a single source of truth and reliable update semantics.

## Update model

ShowMeWhy intentionally omits `version` from `.claude-plugin/plugin.json`. For a Git-hosted marketplace Claude falls back to the source Git commit SHA as the plugin version key. This means each new upstream commit can be detected as a new plugin version without requiring an additional plugin-manifest version bump.

Semantic product releases remain tracked through `VERSION`, `CHANGELOG.md`, Git tags and GitHub Releases. They are release metadata, not the Claude plugin-cache key.

The installer also sets `autoUpdate: true` for the `showmewhy` marketplace in Claude's marketplace state. Claude Code can then refresh the marketplace and installed plugin at startup. If Claude updates a plugin while a session is already open, follow Claude's prompt to reload plugins or start a new session.

## Manual installation

```bash
claude plugin marketplace add https://github.com/vishnu-77/showmewhy.git
claude plugin install showmewhy@showmewhy
```

For manual installs, enable auto-update for the ShowMeWhy marketplace through Claude's `/plugin` marketplace UI. The provided installer does this automatically during installation.

## Validation

CI validates the plugin with the real stable Claude Code binary, installs it from a marketplace, verifies that the plugin cache contains `skills/showmewhy/SKILL.md`, and rejects plugin load failures. Installer acceptance runs twice on Ubuntu, macOS and Windows, verifies `autoUpdate: true`, verifies the marketplace-managed Skill and runtime, and verifies migration removes the legacy `~/.claude/skills/showmewhy` copy.

The plugin manifest is `.claude-plugin/plugin.json`; the marketplace manifest is `.claude-plugin/marketplace.json`; the Skill source is `skills/showmewhy/`.
