# Task 20 subagent prompt — work orders and reservations

Work only on `task/20-work-orders` created from the milestone commit containing
the decision-complete Task 20 plan. Read `AGENTS.md`, the binding Task 20 plan,
Task 19a report, Tasks 20a/20b plans, ADR-0016, ADR-0019, ADR-0020, and directly
relevant current interfaces/tests before editing.

Implement exactly the binding plan: frozen typed work/requirement/reservation
records; one authoritative `WorkManager`; aggregate atomic assignment locks;
typed category targets; exact lifecycle/state/tick/release/event contracts;
settlement/objective/prerequisite and spatial validation; bidirectional
lifecycle/removal guards and explicit historical-reference rules; schema-9 strict
persistence and legacy migration; privileged detached inspection; fixed
qualitative NPC interpretations and final filtering; focused regressions;
example 034; ADR/docs; and the truthful report.

The exact fields, enums, generated IDs, canonical tuple ordering, manager APIs,
transition graph, settlement aggregate availability arithmetic, non-deduction,
cross-kind locks, rollback, events, query order, loaded invariants, inspection shape, safe prose,
hidden fields, tests, and allowed-file list are binding. Do not invent item/tool
identity, alternate reservation stages, automatic recovery, or other semantics.

Do not add proposal/action handlers (Task 20a), systems/scheduler changes,
automatic labor selection/progress, resource charging, or construction,
production, maintenance, external-dispatch, goal/objective/stage/run effects
(Task 20b and later). Do not modify `ResourceSystem`, YAML, prompts, LLM clients,
or automatically inject work prose into NPC context.

Stay inside the exact allowed-file boundary. Create
`docs/subagent_execution_plan/v0_6/20_work_orders_reservations-report.md` with
actual files, behavior, invariants, tests, review corrections, and limitations.
Run focused tests, then `make`, separate `make examples`, and
`git diff --check`. Report exact results. Do not commit, merge, push, or change
branches. Stop and report any contract conflict or required out-of-scope file.
