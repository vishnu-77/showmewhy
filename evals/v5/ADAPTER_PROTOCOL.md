# V5 provider-neutral adapter protocol

V5 does not ship a model-provider adapter. The evaluator supplies an executable adapter at run time.

## Why

The benchmark is intended to measure ShowMeWhy's verification behaviour, not lock the experiment to one model vendor, API, CLI or authentication mechanism.

The six pilot task specs are therefore provider-free. Runtime identity is supplied through environment variables immediately before execution and is persisted into the pair record.

## Required runtime identity

Set all of the following before invoking `pair_runner.py`:

- `SHOWMEWHY_V5_EXECUTION_MODEL`
- `SHOWMEWHY_V5_EXECUTION_RUNTIME`
- `SHOWMEWHY_V5_EXECUTION_TOOL_PROFILE`
- `SHOWMEWHY_V5_ADAPTER_ARGV_JSON`

`SHOWMEWHY_V5_ADAPTER_ARGV_JSON` is a JSON array containing the executable and arguments, for example:

~~~bash
export SHOWMEWHY_V5_ADAPTER_ARGV_JSON='["python","/opt/v5/my_adapter.py"]'
~~~

Optional controls:

- `SHOWMEWHY_V5_ADAPTER_PASS_ENV_JSON` — JSON array of environment-variable **names** that the adapter is allowed to inherit.
- `SHOWMEWHY_V5_TIMEOUT_SECONDS` — positive integer timeout per condition.

No provider credential is inherited implicitly.

## Environment passed to the adapter

The runner invokes the same adapter twice, once for each condition, and sets:

- `SHOWMEWHY_V5_CONDITION` — `baseline` or `showmewhy`
- `SHOWMEWHY_V5_PAIR_ID`
- `SHOWMEWHY_V5_PROMPT_SHA256`
- `SHOWMEWHY_V5_PROMPT_FILE`
- `SHOWMEWHY_V5_OUTPUT_DIR`
- `SHOWMEWHY_V5_WORKSPACE`
- `SHOWMEWHY_V5_MODEL`
- `SHOWMEWHY_V5_AGENT_RUNTIME`
- `SHOWMEWHY_V5_TOOL_PROFILE`
- `SHOWMEWHY_V5_BASE_RESULT_FILE` — only for the `showmewhy` condition

The adapter runs with its working directory set to `SHOWMEWHY_V5_WORKSPACE`.

## Adapter obligations

For `baseline`:

1. Execute the frozen task prompt exactly once.
2. The coding agent may modify the task workspace.
3. Persist the agent's final answer as `$SHOWMEWHY_V5_OUTPUT_DIR/result.txt`.
4. Return exit code 0 only for a usable completed agent result.

For `showmewhy`:

1. Start a fresh verification process over the already-completed workspace.
2. Use the original task prompt and captured baseline result.
3. Apply the canonical ShowMeWhy contract from `skills/showmewhy/SKILL.md`.
4. Do not edit, write, commit or otherwise change the task workspace.
5. Persist the final verification surface as `result.txt`.
6. Return exit code 0 only for a usable verification result.

The runner fingerprints Git-visible workspace state before and after verification and invalidates the pair if it changes.

## Evidence

Adapters may additionally persist:

- raw provider response;
- stderr/logs;
- tool transcript;
- token usage;
- cost metadata;
- runtime/version metadata;
- canonical ShowMeWhy skill SHA-256;
- treatment prompt SHA-256.

These artifacts are evidence only. They do not make a pair scoreable by themselves.

## Security boundary

Provider secrets must never be embedded in pair specs, committed files or output artifacts. Supply only the names of required secret variables through `SHOWMEWHY_V5_ADAPTER_PASS_ENV_JSON`.

The runner starts from a minimal environment and passes only essential OS variables plus explicitly named adapter variables.

## Publication boundary

A provider-neutral raw pair is still not evidence of effectiveness until:

1. the pair is valid;
2. workspace equivalence holds;
3. ground truth is labelled independently and blind to ShowMeWhy;
4. timed baseline and ShowMeWhy reviews are completed;
5. a scoreable record is assembled and accepted by `scorer.py`.
