# Claude Code

Use the supported installer so ShowMeWhy is registered as one marketplace-managed plugin containing both the Skill and runtime.

```text
/showmewhy:showmewhy
```

The plugin contains `skills/showmewhy/`, hooks, local evidence retention, context compression, provenance and adaptive policy. Keeping these components in one plugin ensures they share the same update key and cannot drift into different local versions.

The installer enables marketplace auto-update for ShowMeWhy and removes the older copied personal Skill from `~/.claude/skills/showmewhy/` if present.

See the root README for macOS/Linux/WSL and Windows installation commands.
