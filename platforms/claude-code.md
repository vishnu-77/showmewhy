# Claude Code

Use the supported installer so ShowMeWhy is available as the clean personal command:

```text
/showmewhy
```

The user-facing Skill is installed at `~/.claude/skills/showmewhy/`. The separately installed `showmewhy@showmewhy` plugin is runtime-only and provides hooks, local evidence retention, context compression, provenance and adaptive policy. It intentionally does not ship an auto-discovered plugin Skill, avoiding the namespaced `/showmewhy:showmewhy` command surface.

See the root README for macOS/Linux/WSL and Windows installation commands.
