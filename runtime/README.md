# ShowMeWhy V2 runtime

V2 adds optional **pre-context compression** for verbose Claude Code `Bash` tool results. `/showmewhy` still works without the runtime.

## Contract

1. Receive the `PostToolUse` event on stdin.
2. Ignore non-Bash, short, or unsupported outputs.
3. Persist the complete raw tool response under `.showmewhy/evidence/`.
4. Produce a deterministic digest for recognised test/build/lint/git output.
5. Persist run metrics under `.showmewhy/runs/`.
6. In `replace` mode, return `updatedToolOutput` while preserving the Bash response shape.
7. Fail open if storage, parsing, or replacement is unsafe.

Only Bash is enabled by default. Compressing file reads or arbitrary MCP payloads can remove semantics needed by the agent, so those surfaces are deliberately excluded from V2.

## Modes

Default:

```bash
SHOWMEWHY_MODE=replace
```

Shadow evaluation without replacement:

```bash
SHOWMEWHY_MODE=shadow
```

Context target:

```bash
SHOWMEWHY_CONTEXT_BUDGET_TOKENS=700
```

## Evidence

Raw evidence is content-addressed:

```text
evidence://sha256/<digest>
```

Inspect it locally:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli inspect evidence://sha256/<digest>
```

Runtime state is local and Git-ignored.
