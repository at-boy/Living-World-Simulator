# Task 16a — Runner, checkpointing, and resume report

## Delivered interfaces and files

- `src/living_world/running/runner.py` adds frozen `RunConfiguration` and
  `RunResult` records; `Runner`, `StopControl`, and `CheckpointControl`
  protocols; the validated `IntervalCheckpointControl`; typed persistence and
  simulation failures; stable stop reasons; and `ScenarioRunner`.
- `src/living_world/running/__init__.py` exports the supported runner surface.
- `src/living_world/cli.py` separates argparse and SIGINT handling from the
  runner service. It implements `living-world run SCENARIO`, stable summaries,
  and exit codes 2–5 for configuration/scenario, compatibility, persistence,
  and simulation failures.
- `src/living_world/simulation/simulation_engine.py` adds the minimal public
  `SimulationEngine.persistence_enabled` capability query. The runner uses it
  to reject a non-persistent composition before scenario binding.
- `pyproject.toml` registers `living-world = living_world.cli:main`.
- `tests/test_runner_cli.py` covers default and overridden bounds, explicit
  continuous mode, injected stop/checkpoint controls, deterministic tick and
  save cadence, final saves, terminal selection, signal control, new/resumed
  status, no duplicate initialization, state equivalence, failed-tick snapshot
  preservation, validation, stable summaries, and every failure category.
- `examples/025_bounded_runner.py` performs a bounded SQLite run and compatible
  resume through public runner interfaces.
- `docs/operator_runbook.md`, `CHANGELOG.md`, `docs/project_journal.md`, and
  `docs/backlog.md` document operator behavior and Task 16a completion.

## CLI examples and behavior

```console
living-world run scenarios/founders.yaml --database runs/founders.sqlite3
living-world run scenarios/founders.yaml --max-ticks 48 --save-every 6
living-world run scenarios/founders.yaml --continuous --save-every 12
```

Bounded execution defaults to the scenario's validated `run.max_ticks`.
`--max-ticks` overrides that invocation and is mutually exclusive with
`--continuous`; checkpoint cadence is always positive. The engine-owned fixed
terminal registry accepts only `tick_limit` and `operator_stop`. Continuous
tests use injected controls and no wall-clock sleep or real signal.

Successful output contains only scenario key, new/resumed status, start/end
ticks, and stop reason. Exit code 2 denotes invalid configuration/scenario, 3
an incompatible save, 4 persistence failure, and 5 simulation failure.

## Checkpoint and resume evidence

The runner checkpoints after each configured number of completed ticks and
saves once more on normal, selected-terminal, or cooperative operator exit
when that state has not already been saved. SIGINT sets an injected-style stop
flag and is observed between ticks. A simulation exception is wrapped without
performing a later save; the regression reloads the real SQLite database and
confirms the last completed tick and its entity state remain authoritative.
An engine without a persistence repository is rejected before scenario loading,
so the supported runner cannot report checkpoint success for a no-op save.

A fresh scenario is instantiated once by Task 16's scenario runtime manager.
Resume constructs a new engine from SQLite, reloads and fingerprint-validates
definitions, reports resumed status, and does not duplicate entities. A four-
tick uninterrupted run and two two-tick invocations compare equal across tick,
entities, relationships, and events.

## Boundary compliance

The runner consumes the engine's public scenario, step, state tick/run identity,
and save interfaces plus the minimal `persistence_enabled` Task 16a extension.
It does not edit or feed cognition,
perception, action handling, simulation domain systems, UI, or later-task
artifacts. Operator summaries contain no raw `WorldState`, entity IDs,
attributes, fingerprints, provider data, or secrets, and no runner data enters
NPC context.

## Validation

- Focused runner/CLI tests: 13 passed.
- `make`: passed Ruff, Black, 420 tests, and examples 001–025.
- `make examples`: passed all 25 numbered examples.
- `git diff --check`: passed.

No blockers remain.
