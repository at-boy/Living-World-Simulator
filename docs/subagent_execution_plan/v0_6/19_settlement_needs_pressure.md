# 19 — Settlement needs and resource pressure

## Status and dependencies

Authorized after reviewed Task 18a. Execute on `task/19-settlement-needs`.
Task 19a depends on its reviewed merge.

## Task description

Add configured food, water, shelter, and storage needs for settlements and
households. Frozen definitions describe thresholds and assessment windows;
managed state records hold current qualitative level, deficit/surplus, and
satisfaction history derived deterministically from authoritative resources,
population, housing, and capacity.

## Contract and boundary

- Managers own definitions/state and a system assesses needs in stable order.
- Provide typed need kinds and levels, immutable transition events, SQLite
  migration, deterministic detached inspection, and filtered qualitative NPC
  perceptions. Hide exact engine thresholds/quantities unless translated by an
  authorized perception.
- Validate owner/type/threshold/window configuration, missing capability,
  zero population, destroyed owners, idempotence, legacy saves, and detachment.
- Update engine/state/repository/API, tests/example, ADR/docs, changelog,
  journal, backlog, and report. Do not consume resources, add maintenance,
  select actions, create work, or implement stage progression.
- Run `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/19_settlement_needs_pressure-report.md`.
