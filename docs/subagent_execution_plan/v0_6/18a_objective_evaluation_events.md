# 18a — Objective evaluation and events

## Status and dependency

Authorized after reviewed Task 18. Execute on
`task/18a-objective-evaluation-events`.

## Task description

Add a deterministic evaluation system that derives objective activation,
progress evidence, blockage, completion, and failure from authoritative state
after domain systems run. Record one immutable event per actual transition.

## Contract and tests

- Add typed criterion evaluators behind a protocol/registry; reject unknown
  criteria at configuration time. Evaluation reads world state and mutates only
  through the Task 18 manager.
- Dependencies activate in stable graph order; alternatives complete their
  parent when policy is satisfied; deadlines fail only from engine tick.
- Evidence is detached, normalized, deterministic, and persisted without
  copying arbitrary runtime objects. Repeated unchanged evaluation is
  idempotent.
- Extend scheduler/engine composition, focused inspection where needed,
  tests/example/docs, changelog, journal, backlog, and report. Do not add needs,
  work, stage implementations, UI, or NPC access to exact evidence.
- Cover all criterion kinds available at this point, dependency/alternative
  order, blocked and deadline paths, idempotence, save/resume, and events. Run
  `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/18a_objective_evaluation_events-report.md`.
