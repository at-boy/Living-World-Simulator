# Task 18 subagent prompt — goals and objective graphs

Work only on `task/18-goals-objectives` after Task 17a merges. Read required
docs and the binding Task 18 plan. Implement only durable typed goal/objective
definitions and managed lifecycle state, validation, persistence, inspection,
and filtered NPC interpretations. Never let free-form LLM output, hidden
criteria, or internal IDs become authority or NPC context.

Stay inside allowed files, add tests/example/docs and the truthful report, and
run `make`, `make examples`, and `git diff --check`. Do not commit, merge, push,
or change branches; hand the uncommitted delivery to the orchestrator.

The exact allowed files are `src/living_world/goals/`,
`src/living_world/state/world_state.py`,
`src/living_world/simulation/simulation_engine.py`,
`src/living_world/managers/entity_manager.py` (goal-owner removal guarding),
`src/living_world/repositories/sqlite_repository.py`,
`src/living_world/api/inspection.py`, `src/living_world/api/server.py`,
`src/living_world/__init__.py`, `tests/test_goals.py`,
`tests/test_sqlite_repository.py`, `tests/test_inspection_api.py`, and the
schema-version expectation updates in `tests/test_scenario_run_contract.py`
and `tests/test_spatial_domain.py`,
`examples/029_goals_objectives.py`, `CHANGELOG.md`,
`docs/adr/ADR-0019-engine-owned-goals.md`, `docs/backlog.md`,
`docs/core_model.md`, `docs/engine_glossary.md`,
`docs/http_inspection_api.md`, `docs/project_journal.md`, this plan/prompt,
and `docs/subagent_execution_plan/v0_6/18_goals_objective_graphs-report.md`.
Amend both artifacts before changing anything else.
