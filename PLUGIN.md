# ShowMeWhy installation architecture

ShowMeWhy is distributed as one Claude Code marketplace plugin. The user-facing Skill, hooks and runtime are versioned and cached together so they update atomically.

## Recommended installation

### Claude Code marketplace

Inside Claude Code:

```text
/plugin marketplace add vishnu-77/showmewhy
/plugin install showmewhy@showmewhy
/reload-plugins
/showmewhy
```

Equivalent shell commands:

```bash
claude plugin marketplace add vishnu-77/showmewhy
claude plugin install showmewhy@showmewhy
```

### One-line installer

macOS, Linux and WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
```

Windows PowerShell:

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

Claude Code gives plugin skills a qualified `plugin-name:skill-name` identity, but current skill resolution also accepts the bare skill name when it does not collide with another command. ShowMeWhy therefore standardises its public invocation on:

```text
/showmewhy
```

No second orchestration command is installed.

## Update model

ShowMeWhy intentionally omits `version` from `.claude-plugin/plugin.json`. For a Git-hosted marketplace Claude falls back to the source Git commit SHA as the plugin version key. This means each new upstream commit can be detected as a new plugin version without requiring an additional plugin-manifest version bump.

Semantic product releases remain tracked through `VERSION`, `CHANGELOG.md`, Git tags and GitHub Releases. They are release metadata, not the Claude plugin-cache key.

The installer sets `autoUpdate: true` for the `showmewhy` marketplace in Claude's marketplace state. Claude Code can refresh the marketplace and installed plugin in the background after startup. A running session continues using the version it loaded until plugins are reloaded or a new session starts.

ShowMeWhy also exposes explicit lifecycle modes under the same command:

```text
/showmewhy status
/showmewhy update
```

`status` is read-only. `update` uses Claude Code's native updater:

```bash
claude plugin update showmewhy@showmewhy --scope user
```

If the update changes the on-disk plugin while Claude Code is already running, apply it with:

```text
/reload-plugins
```

or start a new Claude Code session.

## Manual marketplace management

Refresh the marketplace catalog:

```bash
claude plugin marketplace update showmewhy
```

Inspect configured marketplaces and installed plugins:

```bash
claude plugin marketplace list --json
claude plugin list --json
```

For manual installs, enable auto-update for the ShowMeWhy marketplace through Claude's `/plugin` marketplace UI if desired. The provided installer enables it automatically.

## Validation

CI validates the plugin with the real stable Claude Code binary, installs it from a marketplace, verifies that the plugin cache contains `skills/showmewhy/SKILL.md`, and rejects plugin load failures. Installer acceptance runs twice on Ubuntu, macOS and Windows, verifies `autoUpdate: true`, verifies the marketplace-managed Skill and runtime, and verifies migration removes the legacy `~/.claude/skills/showmewhy` copy.

The plugin manifest is `.claude-plugin/plugin.json`; the marketplace manifest is `.claude-plugin/marketplace.json`; the Skill source is `skills/showmewhy/`.
