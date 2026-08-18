# Task 16 — Scenario and deterministic run contract report

## Delivered surface

- Added immutable `RunMetadata`, `ScenarioEntity`, `ScenarioRelationship`, and
  `LoadedScenario` records, the `ScenarioLoader` protocol, and the strict
  `YAMLScenarioLoader` implementation.
- Added `ScenarioRuntimeManager` as the owner of scenario binding. It validates
  run identity and definition vocabulary, stages initial entities and
  relationships through temporary managers, and commits them only after the
  complete initial world succeeds.
- Added `SimulationEngine.load_scenario(Path)`, durable
  `WorldState.run_metadata`, and public scenario package exports.
- Added detached operator inspection through `EngineWorldInspector.run_metadata`,
  the `/world/run` endpoint, and the `run` field in the world summary.
- Added `examples/024_scenario_run_contract.py` and focused scenario, inspection,
  and persistence coverage.

Scenario documents reject unknown or duplicate YAML fields, duplicate labels,
invalid relationship references, boolean integers, unsupported versions,
absolute or escaping definition paths, non-JSON attributes, and internal
record IDs. Their fingerprint is deterministic over normalized scenario data
and the referenced definition document. Scenario attribute trees are frozen;
runtime managers receive detached mutable copies, preventing later scenario
inspection from mutating authoritative state.

## Persistence and migration

SQLite snapshot schema version 2 stores optional run metadata. The repository
continues to load schema-version-1 snapshots without metadata as legacy,
unbound worlds. Saving such a loaded world rewrites it as schema version 2
without inventing a scenario identity. Schema-version-2 metadata has explicit
round-trip coverage. Resume reloads definitions and rejects any changed
scenario identity, seed, normalized configuration, or definition document.

## Atomicity and information boundary

Fresh instantiation is staged in a separate `WorldState` through
`DefinitionManager`, `EntityManager`, and `RelationshipManager`; a manager
failure leaves the authoritative world, definitions, metadata, and generated
ID state unchanged. Existing matching runs reload definitions without
recreating records.

Run metadata is available only through privileged engine inspection. No raw
`WorldState`, internal IDs, fingerprints, seeds, or scenario configuration are
added to NPC context. A regression test assembles an NPC context after scenario
loading and verifies that the operator-only fingerprint and seed remain absent.
No cognition, perception, action-resolution, existing-system, UI, or later
v0.6 task files were changed.

## Exact files and interfaces

- Domain and runtime: `src/living_world/core/run_metadata.py`,
  `src/living_world/scenarios/__init__.py`,
  `src/living_world/scenarios/scenario.py`, and
  `src/living_world/scenarios/runtime.py`.
- Integration and persistence: `src/living_world/state/world_state.py`,
  `src/living_world/simulation/simulation_engine.py`, and
  `src/living_world/repositories/sqlite_repository.py`.
- Operator inspection: `src/living_world/api/inspection.py` and
  `src/living_world/api/server.py`.
- Tests and example: `tests/test_scenario_run_contract.py`,
  `tests/test_sqlite_repository.py`, `tests/test_inspection_api.py`, and
  `examples/024_scenario_run_contract.py`.
- Documentation: ADR-0015, changelog, backlog, core model, engine glossary,
  HTTP inspection API, project journal, and this report.

## Validation

- `make`: passed Ruff, Black, 407 tests, and examples 001–024.
- `make examples`: passed all 24 numbered examples.
- `git diff --check`: passed.

No blockers remain.
