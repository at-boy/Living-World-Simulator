# 19 — Settlement needs and resource pressure

## Status and dependencies

Authorized after reviewed Tasks 18a and 15d. Execute on
`task/19-settlement-needs`.
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

## Task 18a integration

- Implement the concrete `SustainedNeedCriterion` evaluator behind Task 18a's
  existing evaluator protocol; do not special-case needs inside the generic
  goal evaluation system.
- Register needs assessment before goal evaluation in engine scheduler order so
  goals read current authoritative need state from the same tick.
- Keep the criterion result/evidence privileged and normalized. The separate
  NPC need perception remains qualitative and contains no exact thresholds,
  deficit/surplus quantities, windows, internal IDs, or goal evidence.

## Allowed-file boundary

- `src/living_world/needs/`
- `src/living_world/goals/evaluation.py` and
  `src/living_world/goals/__init__.py` only for the concrete sustained-need
  evaluator and registry integration
- `src/living_world/state/world_state.py`,
  `src/living_world/simulation/simulation_engine.py`, and
  `src/living_world/managers/entity_manager.py` for owner lifecycle guarding
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py`, `src/living_world/api/server.py`, and
  `src/living_world/__init__.py`
- `tests/test_settlement_needs.py`, `tests/test_goal_evaluation.py`,
  `tests/test_sqlite_repository.py`, `tests/test_inspection_api.py`, plus
  schema-version expectation updates in `tests/test_scenario_run_contract.py`
  and `tests/test_spatial_domain.py`
- `examples/032_settlement_needs.py`
- `CHANGELOG.md`, `docs/adr/ADR-0020-settlement-needs.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/http_inspection_api.md`, and `docs/project_journal.md`
- This plan, its saved `-prombt.md`, and the Task 19 `-report.md`

No other file may change without first amending this plan and saved prompt.

## Report

Create `docs/subagent_execution_plan/v0_6/19_settlement_needs_pressure-report.md`.
