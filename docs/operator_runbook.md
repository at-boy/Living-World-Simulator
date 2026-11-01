# Scenario runner

The supported headless command creates or resumes one scenario-backed SQLite
world:

```console
living-world run scenarios/founders.yaml --database runs/founders.sqlite3
```

The scenario's `run.max_ticks` is the default bound. Override the number of
ticks for one invocation with `--max-ticks N`, or explicitly remove the bound
with `--continuous`. Those flags are mutually exclusive. `--save-every N`
controls the positive checkpoint cadence and defaults to every tick.

The runner saves after each checkpoint cadence, on normal or terminal exit,
and after a cooperative SIGINT stop. SIGINT is handled between ticks. A failed
tick is never saved over the last valid checkpoint. Continuous runs therefore
remain safely stoppable with Ctrl-C.

Successful output is one stable operator summary, for example:

```text
scenario=founders status=resumed start_tick=24 end_tick=48 stop_reason=tick_limit
```

Exit codes are `0` for success, `2` for invalid configuration or scenario,
`3` for an incompatible saved run, `4` for persistence failure, and `5` for a
simulation failure. Error output does not include provider secrets or raw
world state. Definitions and the scenario fingerprint are revalidated before
any resumed tick executes.

### Opt-in founding-action request contract

For a fresh live founding run or paused server, add
`--request-contract founders_empty_arguments_v1` to the existing
`run --preset founders --driver ollama --model MODEL` or
`serve --preset founders --driver llama.cpp --model MODEL --model-file /absolute/model.gguf`
command. Both providers then receive instructions and a response schema requiring
`arguments: {}` for offered founding actions; the chosen target belongs only in
`target_label`. This selector is supported only for live `canonical_founders_v1`.
It does not change action offers, response parsing, gateway validation, or engine
authority. A provider ignoring the schema can still propose nonempty arguments;
the ordinary gateway rejects those proposals without stripping their arguments.

Omitting the flag preserves the legacy request bytes and archive fingerprints.
Explicit `--request-contract legacy_v1` selects the same legacy behavior and is
stored as absence of the provider key. Only `founders_empty_arguments_v1` is a
valid persisted selector; manually inserting an explicit legacy key into raw
archive configuration is rejected as noncanonical. On resume or fork, omission
inherits the source selection. Resume accepts the same selection and rejects a
change before provider preflight or allocation. Fork permits a change and uses
new request fingerprints, so incompatible parent responses are not reused.
Sealed offline replay and its descendants use the source's selected contract;
they do not require the provider to be available. Recorded runs, inspection,
analysis, and replay commands reject the selector flag, including explicit legacy.

The schema is a request constraint, not proof of provider compatibility or action
success. Native backend verification and normal retained request/response traces
remain necessary when evaluating actual model behavior.
