# 16a — Runner, checkpointing, and resume

## Status and dependency

Authorized after reviewed Task 16 merges into `milestone/v0.6`. Execute on
`task/16a-runner-checkpoint-resume` created from that updated milestone branch.

## Task description

Add the supported operator command that runs a scenario for bounded or
continuous ticks, checkpoints atomically, resumes compatible saves, and exits
with an inspectable reason. This task orchestrates existing engine behavior; it
does not add later v0.6 simulation domains or cognition tapes.

## Public CLI and behavior

- Register `living-world run SCENARIO` as the console entry point.
- Support `--database PATH`, `--max-ticks N`, and `--save-every N`.
  `max-ticks` defaults from the scenario and remains bounded unless
  `--continuous` is explicit. Non-negative integer validation must reject bools
  and contradictory flags.
- A new database instantiates once; an existing database resumes after Task 16
  identity/fingerprint validation. Reload definitions before stepping.
- Save at configured checkpoints, normal completion, terminal-condition exit,
  and graceful SIGINT. Never replace the last valid snapshot with a partial
  failed tick.
- Print stable operator summaries containing scenario label, start/end tick,
  resumed/new status, and stop reason without provider secrets or raw state.
- Return distinct nonzero exit codes for invalid configuration/scenario,
  incompatible save, persistence failure, and simulation failure.

## Run ownership

- Introduce a typed runner protocol/service separate from CLI parsing.
- Terminal conditions are registered engine-owned predicates selected by the
  scenario's validated names. This task may provide tick-limit and explicit
  operator-stop conditions only; domain success/failure conditions arrive in
  later tasks.
- Continuous mode must be testable through injected stop/checkpoint controls;
  tests must not depend on real signals or wall-clock sleeps.

## Allowed files

- New runner/CLI modules, package entry-point metadata, and minimal Task 16
  scenario/run extensions required for the documented run behavior.
- Focused tests, one numbered executable example, operator documentation,
  changelog, project journal, backlog, and the Task 16a report.
- Do not edit cognition/perception, action handlers, simulation domain systems,
  UI assets, or later task artifacts.

## Tests and validation

- Cover bounded default/override, explicit continuous mode, deterministic step
  count, checkpoint cadence, new/resumed worlds, final save, injected graceful
  stop, terminal stop, each failure exit, no duplicate initialization, and
  uninterrupted versus resumed state equivalence for the current engine.
- Run `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/16a_runner_checkpoint_resume-report.md`
with exact interfaces/files, CLI examples, checkpoint/resume evidence,
validation results, boundary compliance, and blockers.
