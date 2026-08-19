# 18 — Engine-owned goals and objective graphs

## Status and dependencies

Authorized after reviewed Task 17a. Execute on `task/18-goals-objectives`.
Task 18a depends on its reviewed merge.

## Task description

Add durable engine-owned goals and objective graphs. Frozen definitions record
owner kind/identity, operator purpose, filtered NPC-visible interpretation,
priority, deadlines, authorized action categories, typed completion/failure
criteria, dependencies, and alternatives. Separate managed state records hold
status and progress evidence.

## Public contract and boundary

- Support NPC, organization, expedition, and settlement owners; statuses are
  inactive, active, blocked, completed, and failed.
- Criteria use a closed typed vocabulary: resource minimum, constructed
  capability/count, capacity, external connection state, sustained need
  threshold, and settlement stage. No expressions, callbacks, prompt text, or
  LLM declarations may complete a goal.
- Managers alone create goals/objectives and change lifecycle state. Validate
  missing owners, cycles, impossible dependency/alternative shapes, duplicate
  labels, deadlines, and action categories atomically.
- Extend `WorldState`, engine composition, SQLite migration/round trips,
  detached deterministic inspection, public exports, tests/example, ADR/docs,
  changelog, journal, backlog, and Task 18 report.
- NPC context may receive only the visible interpretation through an explicit
  filtered record; hide IDs, exact criteria, evidence, and engine status unless
  legitimately perceived. Do not implement automatic evaluation or work.

## Tests and validation

Cover graph validation/cycles, owner scopes, state transitions, immutability,
legacy saves, ordering, DTO detachment, and NPC isolation. Run `make`,
`make examples`, and `git diff --check`.

## Allowed-file boundary

- `src/living_world/goals/` and `src/living_world/state/world_state.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/managers/entity_manager.py` for goal-owner removal guarding
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py` and `src/living_world/api/server.py`
- `src/living_world/__init__.py`
- `tests/test_goals.py`, `tests/test_sqlite_repository.py`, and
  `tests/test_inspection_api.py`, plus schema-version expectation updates in
  `tests/test_scenario_run_contract.py` and `tests/test_spatial_domain.py`
- `examples/029_goals_objectives.py`
- `CHANGELOG.md`, `docs/adr/ADR-0019-engine-owned-goals.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/http_inspection_api.md`, and `docs/project_journal.md`
- This plan, its saved `-prombt.md`, and the Task 18 `-report.md`

No other files may change without first amending this plan and saved prompt.

## Report

Create `docs/subagent_execution_plan/v0_6/18_goals_objective_graphs-report.md`.
