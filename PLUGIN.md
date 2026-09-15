# ShowMeWhy plugin installation

ShowMeWhy can be installed either as an Agent Skill or through Claude Code's plugin marketplace flow.

## Claude Code marketplace

Add this repository as a marketplace:

```text
/plugin marketplace add vishnu-77/showmewhy
```

Then install ShowMeWhy:

```text
/plugin install showmewhy@showmewhy
```

After installation, invoke:

```text
/showmewhy
```

The repository is private during preview, so the local Git/GitHub environment must have permission to access `vishnu-77/showmewhy`.

## Direct Agent Skill install

```bash
npx skills add vishnu-77/showmewhy --skill showmewhy
```

The plugin manifest is `.claude-plugin/plugin.json`; the marketplace manifest is `.claude-plugin/marketplace.json`. CI validates that both manifests parse and that the marketplace resolves the real `skills/showmewhy/SKILL.md` path.
