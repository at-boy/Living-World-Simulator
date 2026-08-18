# 20b — Deterministic work execution

## Status and dependencies

Authorized after reviewed Task 20a. Execute on `task/20b-work-execution`.

## Task description

Add deterministic systems that assign eligible labor, activate ready work,
consume reserved time/resources/tools, advance bounded progress, and complete
domain effects through managers and existing construction, production,
resource, maintenance, and external-dispatch contracts.

## Contract and tests

- Stable ordering is priority, creation tick, then work ID. Labor cannot be
  double-booked; inactive/unavailable NPCs do not contribute. Tools remain
  reserved while consumables are charged exactly once.
- Emit start, progress threshold, blockage/recovery, completion, cancellation,
  and failure events once. Resulting state is evaluated later by needs/goals;
  the system never marks objectives or stages directly.
- Extend engine/scheduler and minimal domain adapters, tests/example/docs,
  changelog, journal, backlog, and report. Cover competition, insufficient
  inputs, actor loss, rollback, save/resume equivalence, deterministic ordering,
  each initial work category, and no duplicate effects.
- Do not add new cognition authority, UI, or free-form work behavior. Run
  `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/20b_work_execution-report.md`.
