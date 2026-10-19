# 15b — Spatial domain, persistence, and inspection

## Status and dependency

Authorized after reviewed Task 15a. Execute on
`task/15b-spatial-domain-persistence`.

## Task description

Implement the approved frozen point/bounds records and a manager that alone
creates, replaces, and removes placements. Add deterministic queries,
validation, SQLite migration/round trips, and detached privileged inspection.

## Boundary and tests

- Extend `WorldState`, engine composition, repository schema, inspection
  protocol/server, public exports, focused tests/example, ADR-linked docs,
  changelog, journal, backlog, and Task 15b report.
- Cover valid/invalid geometry, parent containment, overlap policy, destroyed or
  missing entities, explicit unplaced state, deterministic ordering, legacy
  saves, detachment, and unchanged NPC context.
- Do not infer coordinates from attributes, implement pathfinding/work/UI, or
  expose raw coordinates to NPC cognition. Run `make`, `make examples`, and
  `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/15b_spatial_domain_persistence_inspection-report.md`.
