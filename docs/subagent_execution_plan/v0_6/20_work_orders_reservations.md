# 20 — Work orders and reservations

## Status and dependencies

Authorized after reviewed Task 19a. Execute on `task/20-work-orders`.
Task 20a depends on its reviewed merge.

## Task description

Add durable engine-owned work orders and atomic reservations. Frozen work
definitions/state contain category, public label, owning settlement/objective,
location, prerequisites, required labor/tools/resources, progress, priority,
deadline, and status. Managers alone create, assign, reserve, block, cancel,
complete, or fail work.

## Contract and boundary

- Statuses: proposed, ready, assigned, active, blocked, completed, cancelled,
  failed. Reservations prevent double-allocation and release on every terminal
  or blocked transition according to explicit policy.
- Validate references, compatible locations, nonnegative integer requirements,
  assignment capacity, duplicate reservations, transition legality, and atomic
  rollback.
- Extend state/engine, SQLite migration, deterministic inspection, public
  exports, immutable events, tests/example, ADR/docs, changelog, journal,
  backlog, and report.
- NPCs may see filtered work descriptions/status only; hide IDs, exact hidden
  requirements/reservations, and arbitrary state. Do not add action handlers or
  execute work. Run `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/20_work_orders_reservations-report.md`.
