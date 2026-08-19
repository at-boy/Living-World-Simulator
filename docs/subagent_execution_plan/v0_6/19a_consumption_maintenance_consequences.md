# 19a — Consumption, maintenance, and consequences

## Status and dependency

Authorized after reviewed Task 19. Execute on
`task/19a-consumption-maintenance`.

## Task description

Add deterministic tick-based food/water consumption, configured storage
capacity and spoilage, and upkeep/deterioration for constructed capabilities.
Consequences update resources/entities through their owning managers and feed
Task 19 assessment; they never directly choose cognition or mark goals complete.

## Contract and tests

- Add typed consumption/maintenance policies and systems with stable order,
  bounded integer arithmetic, explicit shortage/recovery/deterioration events,
  and idempotent terminal effects.
- Reserve failure/terminal-run decisions for later criteria; this task records
  authoritative evidence only.
- Extend configuration/persistence/inspection as required, tests/example/docs,
  changelog, journal, backlog, and report. Cover insufficient stock, capacity,
  spoilage, upkeep paid/unpaid, deterioration/recovery, destroyed entities,
  save/resume equivalence, ordering, and NPC-safe perceptions.
- Do not implement work assignment, stages, UI, or LLM-selected consequences.
  Run `make`, `make examples`, and `git diff --check`.

## Scheduler and goal boundary

Consumption, spoilage, and maintenance systems run before Task 19 needs
assessment, which continues to run before Task 18a goal evaluation. This task
does not call the goal manager or mark criteria complete; it changes only
authoritative domain state that later assessment/evaluation reads.

## Allowed-file boundary

- `src/living_world/needs/`
- `src/living_world/state/world_state.py` and
  `src/living_world/simulation/simulation_engine.py`
- `src/living_world/managers/entity_manager.py` and
  `src/living_world/systems/resource_system.py` only for manager-owned,
  validated consequences required by the policies
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py`, `src/living_world/api/server.py`, and
  `src/living_world/__init__.py`
- `tests/test_consumption_maintenance.py`, `tests/test_settlement_needs.py`,
  `tests/test_goal_evaluation.py`, `tests/test_sqlite_repository.py`, and
  `tests/test_inspection_api.py`, plus schema-version expectation updates in
  `tests/test_scenario_run_contract.py` and `tests/test_spatial_domain.py`
- `examples/033_consumption_maintenance.py`
- `CHANGELOG.md`, `docs/adr/ADR-0020-settlement-needs.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/http_inspection_api.md`, and `docs/project_journal.md`
- This plan, its saved `-prombt.md`, and the Task 19a `-report.md`

No other file may change without first amending this plan and saved prompt.

## Report

Create `docs/subagent_execution_plan/v0_6/19a_consumption_maintenance_consequences-report.md`.
