# Task 20b worker prompt — deterministic work execution

Implement the complete isolated Task 20b contract on the existing
`task/20b-work-execution` branch.

First read only:

1. `AGENTS.md`
2. `docs/subagent_execution_plan/v0_6/20b_work_execution.md`
3. `docs/adr/ADR-0023-deterministic-work-execution.md`
4. directly relevant code/tests named by the plan

Do not read the continuation brief, roadmap, backlog history, historical task
reports, or unrelated ADRs. ADR-0021 and ADR-0022 may be read only when a
specific Task 20/20a lifecycle or proposal-boundary question requires them.

Use test-driven development. Implement stable assignment, exact-once charging,
bounded progress, threshold evidence, blockage/recovery, all six manager-owned
effects, phase rollback, schema-10 persistence, scheduler placement, and
save/resume equivalence exactly as specified. Do not invent cognition
authority, recipes, construction payloads, automatic cancellation, dispatches,
goal/stage mutations, or NPC-visible execution data.

Stay strictly within the allowed-file list. If the contract cannot be
implemented inside it, stop and report the exact blocker rather than expanding
scope. Preserve the pre-existing `.codex/config.toml` modification without
editing, staging, reverting, or reporting it as Task 20b work.

Create the truthful Task 20b report. Run the focused matrices while iterating,
then `make`, `make examples`, and `git diff --check`. Report commands, results,
counts, and meaningful warnings; do not paste successful output. Do not commit,
merge, push, or change branches.
