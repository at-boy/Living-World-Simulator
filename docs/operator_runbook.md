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
