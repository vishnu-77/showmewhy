# ShowMeWhy embedded composition

ShowMeWhy supports multi-stage behaviour without creating another Claude Code command and without attempting command-to-command invocation.

## Public command invariant

There is one public command:

```text
/showmewhy
```

Composition tokens after it are **ShowMeWhy DSL tokens**, not Claude Code slash-command invocations.

```text
/showmewhy /monitor /showmewhy /i-have-adhd -- investigate why auth tests fail
```

The real command is the first `/showmewhy`. The arguments are parsed as:

```text
/monitor       -> monitor
/showmewhy     -> verify
/i-have-adhd   -> focus
--             -> end of composition stages
<remaining>    -> task text
```

The resulting execution plan is:

```text
monitor -> verify -> focus
```

No nested slash command is invoked.

## Grammar

```text
/showmewhy <stage> [<stage> ...] -- [task]
```

A stage is a slash-prefixed token owned by ShowMeWhy. `--` is mandatory when task text follows the stages. This prevents paths, URLs and ordinary slash-prefixed text in the task from being mistaken for composition stages.

Legacy forms remain valid and unchanged:

```text
/showmewhy
/showmewhy why
/showmewhy why investigate auth failures
/showmewhy deep is this migration safe?
```

Composition is opt-in only when the first argument after `/showmewhy` is slash-prefixed.

## Stages

| Token | Canonical stage | Contract |
|---|---|---|
| `/monitor` | `monitor` | Gather session-level observable verification state and risk signals. Must be first when composed. |
| `/showmewhy`, `/verify` | `verify` | Run the ordinary claim -> obligation -> witness -> scrutiny -> closure verifier. |
| `/deep` | `deep` | Broaden verification obligations for complex or high-consequence work. |
| `/compare` | `compare` | Compare alternatives or earlier/current states using equivalent evidence obligations. |
| `/why` | `why` | Render the expanded claim/witness/gap ledger. Presentation stage. |
| `/short` | `short` | Render the shortest gap-first verification surface. Presentation stage. |
| `/focus`, `/concise`, `/i-have-adhd` | `focus` | Render a highly scannable result: one result, decisive evidence/gap, one next action. This is a ShowMeWhy presentation alias; it does not invoke an external skill. |
| `/impact` | `impact` | Add context/token/operational-impact accounting. Must be terminal, except `/json` may follow. |
| `/json` | `json` | Emit machine-readable output. Must be final. |

## Internal handoff state

Stages operate on one in-memory task state rather than passing natural-language command output to another slash command.

```text
TASK
  task
  observations[]
  evidence_refs[]
  claims[]
  closure{verified, open, refuted}
  delta?
  risk?
  next_action?
  presentation?
```

Each stage may enrich this state but must not silently discard evidence, caveats or refuted claims produced by an earlier stage.

## Execution rules

1. `monitor` may gather observable state but does not replace verification.
2. A presentation stage without an explicit verification stage automatically receives `verify` before it.
3. `monitor` must be first when present.
4. Only one presentation stage may be selected: `why`, `short`, `focus`, or `json`.
5. `json` must be final.
6. `impact` must be final, or immediately before `json`.
7. Unknown stage tokens fail closed with a supported-stage error; they are never treated as external commands.
8. Repeated adjacent aliases that normalise to the same stage are collapsed.
9. Composition must never expose or reconstruct private chain-of-thought.
10. Existing Context Delta behaviour remains automatic inside verification; `/delta` is not introduced as a stage.

## Examples

```text
/showmewhy /monitor /showmewhy -- why did the release fail?
```

```text
/showmewhy /monitor /deep /focus -- can this auth migration ship safely?
```

```text
/showmewhy /compare /why -- compare the old and new token verifier
```

```text
/showmewhy /showmewhy /json -- verify the migration result
```

The deterministic parser is `scripts/compose.py`.
