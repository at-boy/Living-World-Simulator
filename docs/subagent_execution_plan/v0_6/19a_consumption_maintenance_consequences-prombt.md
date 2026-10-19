# Task 19a subagent prompt — consumption and maintenance

Work only on `task/19a-consumption-maintenance` created from the milestone
commit containing the decision-complete Task 19a plan. Read `AGENTS.md`, the
binding plan, Task 19 report, ADR-0020, and all directly relevant existing
interfaces/tests before editing.

Implement exactly the binding plan: frozen typed consumption/storage/
maintenance policies and state; `ConsequenceManager`; one atomic ordered
`ConsequenceSystem`; manager-owned resources, condition, terminal destruction,
and immutable events; scheduler order ordinary systems → consequences → needs
→ goals; schema-8 persistence/load validation; detached privileged consequence
inspection; fixed qualitative NPC interpretations; strengthened final NPC
filtering; focused regressions; example 033; documentation; and the truthful
Task 19a report.

The plan's fields, canonical IDs, uniqueness and cross-reference rules,
consumption equations, all-or-nothing upkeep, bounded condition arithmetic,
owner-funded upkeep, terminal-only capability effect and terminal tick
bookkeeping, bidirectional exclusion from all live-required owner/source roles,
storage capacity source, overflow order, routine spoilage, exact event
subjects/attributes/order, same-tick idempotence, deep whole-phase rollback,
strict schema-v8 record key sets and legacy behavior, inspection shape, fixed
NPC prose, hidden fields, tests, and allowed files are binding. Do not invent
alternatives or broaden scope.

Do not add YAML configuration, work/stage/run-terminal behavior, proportional
capacity degradation, terminal repair, recursive ownership, LLM/model
dependence, direct goal mutation, or automatic NPC-context injection. Never
call `GoalManager` from consequence code. Do not change `ResourceSystem`.

Stay inside the exact allowed-file boundary. Add the required report at
`docs/subagent_execution_plan/v0_6/19a_consumption_maintenance_consequences-report.md`
and state actual files, behavior, invariants, tests, and limitations. Run
focused tests while working, then `make`, separate `make examples`, and
`git diff --check`. Report exact results truthfully. Do not commit, merge,
push, or change branches.
