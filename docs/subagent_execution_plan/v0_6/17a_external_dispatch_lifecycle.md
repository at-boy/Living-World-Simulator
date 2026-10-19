# 17a — External dispatch lifecycle

## Status and dependency

Authorized after reviewed Task 17. Execute on
`task/17a-external-dispatch-lifecycle`.

## Task description

Add durable dispatches with validated `pending`, `in_transit`, `arrived`,
`rejected`, and `lost` transitions. Dispatches reserve/consume local resources
through managers, advance deterministically from the scenario seed and anchor
policy, and record immutable transition events.

## Contracts and boundary

- Add frozen dispatch records, manager and simulation system, action handler
  for offered contact/trade/dispatch proposals, SQLite migration, detached
  inspection, tests/example/docs, changelog, journal, backlog, and report.
- Resolve only offered labels through the existing action gateway. Cognition
  cannot select outcome, delay, hidden probability, internal target, or direct
  resource mutation.
- Cover invalid transitions, capacity/goods/cost checks, reservation rollback,
  deterministic outcomes/order, save/resume, event idempotence, malformed and
  unauthorized requests, DTO detachment, and NPC-safe result perceptions.
- Do not implement goals, generic work orders, UI, or on-map remote places. Run
  `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/17a_external_dispatch_lifecycle-report.md`.
