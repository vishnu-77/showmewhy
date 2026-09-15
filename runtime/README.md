# ShowMeWhy runtime

The runtime is optional. `/showmewhy` remains useful without it.

## V2: context compression

V2 can compress verbose Claude Code `Bash` tool results before they enter agent context. It stores raw evidence first, preserves the Bash result shape and fails open on unsupported output.

```bash
SHOWMEWHY_MODE=shadow
SHOWMEWHY_CONTEXT_BUDGET_TOKENS=700
```

Runtime state is local under `.showmewhy/` and is Git-ignored.

Inspect raw evidence:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli inspect evidence://sha256/<digest>
```

## V3: provenance

Each compressed run also receives a typed provenance graph grounded in its execution digest and retained raw evidence.

Inspect a graph:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli provenance run-012345abcdef
```

Compare two runs:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli compare run-before run-after
```

Create a local static viewer:

```bash
PYTHONPATH=runtime python3 -m showmewhy_runtime.cli view run-012345abcdef --out provenance.html
```

Addresses are stable within retained local runtime data:

```text
evidence://sha256/<digest>#tool_response
run://<run-id>#summary
run://<run-id>#findings/<n>
run://<run-id>#status
```

`CAUSED_BY` relationships are rejected unless an explicit causal basis is attached. Correlation is never silently upgraded to causation.
