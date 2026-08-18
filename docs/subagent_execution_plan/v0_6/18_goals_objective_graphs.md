# 18 — Engine-owned goals and objective graphs

## Status and dependencies

Authorized after reviewed Task 17a. Execute on `task/18-goals-objectives`.
Task 18a depends on its reviewed merge.

## Task description

Add durable engine-owned goals and objective graphs. Frozen definitions record
owner kind/identity, operator purpose, filtered NPC-visible interpretation,
priority, deadlines, authorized action categories, typed completion/failure
criteria, dependencies, and alternatives. Separate managed state records hold
status and progress evidence.

## Public contract and boundary

- Support NPC, organization, expedition, and settlement owners; statuses are
  inactive, active, blocked, completed, and failed.
- Criteria use a closed typed vocabulary: resource minimum, constructed
  capability/count, capacity, external connection state, sustained need
  threshold, and settlement stage. No expressions, callbacks, prompt text, or
  LLM declarations may complete a goal.
- Managers alone create goals/objectives and change lifecycle state. Validate
  missing owners, cycles, impossible dependency/alternative shapes, duplicate
  labels, deadlines, and action categories atomically.
- Extend `WorldState`, engine composition, SQLite migration/round trips,
  detached deterministic inspection, public exports, tests/example, ADR/docs,
  changelog, journal, backlog, and Task 18 report.
- NPC context may receive only the visible interpretation through an explicit
  filtered record; hide IDs, exact criteria, evidence, and engine status unless
  legitimately perceived. Do not implement automatic evaluation or work.

## Tests and validation

Cover graph validation/cycles, owner scopes, state transitions, immutability,
legacy saves, ordering, DTO detachment, and NPC isolation. Run `make`,
`make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/18_goals_objective_graphs-report.md`.
