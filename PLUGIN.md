# ShowMeWhy installation architecture

The supported user experience is one command inside Claude Code:

```text
/showmewhy
```

ShowMeWhy deliberately separates that command from its runtime plugin. Claude Code namespaces Skills distributed inside plugins, so the plugin is runtime-only and the user-invocable Skill is installed at personal scope.

## Recommended installation

### macOS, Linux and WSL

```bash
curl -fsSL https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/vishnu-77/showmewhy/main/install.ps1 | iex
```

The installers set up both components:

```text
~/.claude/skills/showmewhy/
    └── SKILL.md                 → /showmewhy

Claude plugin: showmewhy@showmewhy
    ├── hooks/
    └── runtime/                 → evidence retention, compression,
                                   provenance and adaptive policy
```

The plugin identifier may appear as `showmewhy@showmewhy` in `claude plugin list`. It is not the user command. The plugin intentionally contains no auto-discovered `skills/showmewhy/` directory, preventing Claude from contributing a namespaced `/showmewhy:showmewhy` Skill.

## Manual installation

For development or debugging, the two layers can be installed manually.

Runtime plugin:

```bash
claude plugin marketplace add https://github.com/vishnu-77/showmewhy.git
claude plugin install showmewhy@showmewhy
```

Personal Skill:

```bash
mkdir -p ~/.claude/skills
cp -R standalone/showmewhy ~/.claude/skills/showmewhy
```

Restart Claude Code after changing personal Skills.

## Validation

CI validates the plugin with the real stable Claude Code binary, installs it from a marketplace, and rejects plugin load failures. Installer acceptance runs the complete installer twice on Ubuntu, macOS and Windows, verifies the personal Skill at the global Claude path, verifies the runtime plugin, and rejects any auto-discovered namespaced ShowMeWhy Skill.

The plugin manifest is `.claude-plugin/plugin.json`; the marketplace manifest is `.claude-plugin/marketplace.json`; the personal Skill source is `standalone/showmewhy/`.
