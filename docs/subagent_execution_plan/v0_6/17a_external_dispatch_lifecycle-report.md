# Task 17a — External dispatch lifecycle report

## Delivered contract

Task 17a adds frozen direction/status/dispatch records, a manager-owned resource
reservation and transition lifecycle, a seed-stable scheduler system, an
offered-label action handler, schema-v5 persistence, detached inspection, and a
fixed qualitative NPC-safe result perception. ADR-0018 records the exact policy.

Pending creation validates live source, contactable anchor, directional goods,
capacity, quantity, and local goods/coin without mutation. Commit reserves
resources and records an immutable event atomically. Rejection restores the
reservation; arrival adds inbound goods; loss consumes it. Partial event
failures restore resources, state, history, and the dispatch identifier.
Terminal dispatches are idempotent.

The action handler accepts only its engine-authored label. It rejects model
arguments, unknown labels, unauthorized actors, and invalid current state.
Exact IDs, quantity, cost, delay, reliability, seed calculation, and outcome
never enter the action option or safe result perception.

## Exact files and interfaces

Runtime/API:

- `src/living_world/external_world/dispatch.py`
- `src/living_world/external_world/dispatch_manager.py`
- `src/living_world/external_world/dispatch_system.py`
- `src/living_world/external_world/dispatch_action.py`
- `src/living_world/external_world/__init__.py`
- `src/living_world/state/world_state.py`
- `src/living_world/managers/entity_manager.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/api/inspection.py`
- `src/living_world/api/server.py`

Public interfaces include `DispatchDirection`, `DispatchStatus`,
`ExternalDispatch`, `NPCDispatchPerception`, `ExternalDispatchManager`,
`ExternalDispatchSystem`, `DispatchOffer`, `ExternalDispatchActionHandler`,
`SimulationEngine.external_dispatches`, `WorldState.external_dispatches`,
`WorldInspector.external_dispatches`, and `GET /world/external-dispatches`.

Tests/example and integration expectations:

- `tests/test_external_dispatch.py`
- `tests/test_sqlite_repository.py`
- `tests/test_scenario_run_contract.py`
- `tests/test_spatial_domain.py`
- `tests/test_inspection_api.py`
- `examples/028_external_dispatch.py`

Documentation/delivery:

- `CHANGELOG.md`
- `docs/adr/ADR-0018-deterministic-external-dispatch.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/http_inspection_api.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/v0_6/17a_external_dispatch_lifecycle-report.md`

No goal, work-order, UI, remote-place simulation, cognition-provider,
perception-engine, or generic trade-system file changed.

## Validation and blockers

- Focused domain/integration suite: 106 tests passed.
- `make`: passed Ruff, Black, 498 tests, and examples 001–028.
- Separate `make examples`: passed all 28 numbered examples.
- `git diff --check`: passed.

No blockers remain.
