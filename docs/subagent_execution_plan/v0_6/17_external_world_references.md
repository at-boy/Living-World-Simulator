# 17 — External-world references

## Status and dependencies

Authorized after reviewed Task 15b. Execute on
`task/17-external-world-references`; Task 17a depends on its merge.

## Task description

Add deliberately partial, engine-owned off-map anchors. Frozen reference state
contains internal identity, operator name, role, allowed imports/exports,
capacity, deterministic delay/cost/reliability policy, and contact state. A
manager alone owns lifecycle mutation and immutable events.

## Contracts and boundary

- Extend `WorldState`, engine composition, current SQLite schema/migration,
  deterministic privileged inspection, public exports, tests/example, ADR/docs,
  changelog, journal, backlog, and Task 17 report.
- Provide a separate filtered NPC-visible interpretation containing qualitative
  name/role/contact information only. Hide IDs, exact probabilities/capacity,
  configuration, and future outcomes. Do not simulate remote population,
  politics, buildings, inventories, or geography.
- Validate unique names, goods/capacity/cost/delay types, policy ranges, contact
  transitions, persistence round trips, legacy defaults, ordering, DTO
  detachment, event immutability, and NPC isolation.
- Do not implement dispatch/trade lifecycle, goals, work, or UI. Run `make`,
  `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/17_external_world_references-report.md`.
