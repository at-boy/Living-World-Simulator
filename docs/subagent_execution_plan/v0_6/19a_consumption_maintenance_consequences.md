# 19a — Consumption, maintenance, and consequences

## Status and dependency

Authorized after reviewed Task 19. Execute on
`task/19a-consumption-maintenance`.

## Task description

Add deterministic tick-based food/water consumption, configured storage
capacity and spoilage, and upkeep/deterioration for constructed capabilities.
Consequences update resources/entities through their owning managers and feed
Task 19 assessment; they never directly choose cognition or mark goals complete.

## Contract and tests

- Add typed consumption/maintenance policies and systems with stable order,
  bounded integer arithmetic, explicit shortage/recovery/deterioration events,
  and idempotent terminal effects.
- Reserve failure/terminal-run decisions for later criteria; this task records
  authoritative evidence only.
- Extend configuration/persistence/inspection as required, tests/example/docs,
  changelog, journal, backlog, and report. Cover insufficient stock, capacity,
  spoilage, upkeep paid/unpaid, deterioration/recovery, destroyed entities,
  save/resume equivalence, ordering, and NPC-safe perceptions.
- Do not implement work assignment, stages, UI, or LLM-selected consequences.
  Run `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/19a_consumption_maintenance_consequences-report.md`.
