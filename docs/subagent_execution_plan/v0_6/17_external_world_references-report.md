# Task 17 — External-world references report

## Delivery

Added frozen `ExternalWorldReference`, `ContactState`, and filtered
`NPCExternalReference` under `src/living_world/external_world/`, including the
sole lifecycle manager and lazy public exports. `WorldState` stores the
authoritative collection and `SimulationEngine.external_world_references`
composes its manager.

Creation validates visible text, tuple goods, unique case-folded names, integer
capacity/delay/cost, finite bounded reliability, typed state, and ticks. Contact
changes enforce ADR-0017's graph. Successful operations record immutable
creation and contact-state events.

SQLite snapshots advance to schema 4 and deterministically round-trip exact
records; schema 1–3 snapshots default to empty. Privileged inspection adds
`WorldInspector.external_world_references`, a summary count, and
`GET /world/external-references`, returning detached JSON-safe policy data.

The distinct NPC DTO contains qualitative name, role, and fixed contact prose
only. Tests confirm raw IDs and exact policy do not cross that boundary and
that adding a reference does not alter assembled `NPCContext`. No cognition,
perception, dispatch, trade lifecycle, remote-world simulation, goals, work, or
UI was added.

Tests are in `tests/test_external_world_references.py`; integration expectations
cover schema and inspection. `examples/027_external_world_references.py`
demonstrates lifecycle, persistence, inspection, and filtered interpretation.

- Focused domain/integration validation: 80 tests passed; example 027 passed.
- `make`: passed Ruff, Black, 472 tests, and examples 001–027.
- `make examples`: passed all 27 numbered examples.
- `git diff --check`: passed.

## Exact files, public interfaces, boundary, and blockers

Domain/runtime and public API:

- `src/living_world/external_world/__init__.py`
- `src/living_world/external_world/model.py`
- `src/living_world/external_world/manager.py`
- `src/living_world/state/world_state.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py`
- `src/living_world/api/server.py`

The public interfaces are `ContactState`, `ExternalWorldReference`,
`NPCExternalReference`, `ExternalWorldReferenceManager`,
`WorldState.external_world_references`,
`SimulationEngine.external_world_references`,
`WorldInspector.external_world_references`, and the privileged
`GET /world/external-references` route.

Tests and executable documentation:

- `tests/test_external_world_references.py`
- `tests/test_sqlite_repository.py`
- `tests/test_scenario_run_contract.py`
- `tests/test_spatial_domain.py`
- `tests/test_inspection_api.py`
- `examples/027_external_world_references.py`

The four existing test files contain only schema-v4 migration/current-version,
world-summary/empty-route, and inspector-protocol integration expectation
updates required by the new collection.

Documentation and delivery record:

- `CHANGELOG.md`
- `docs/adr/ADR-0017-partial-external-world-references.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/http_inspection_api.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/v0_6/17_external_world_references-report.md`

All files are within Task 17's allowed domain/runtime, persistence, privileged
inspection, integration-test, example, ADR/documentation, and report surfaces.
No perception, cognition, action gateway, dispatch, trade lifecycle, work,
goal, or UI file changed. No blockers remain.
