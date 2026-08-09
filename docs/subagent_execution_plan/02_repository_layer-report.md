# Repository Layer Report

## Persistence Design

`GraphRepository` defines complete-world `load_world()` and `save_world()`
operations. `SQLiteRepository` stores a versioned JSON serialization of the
generic `WorldState` collections in one `world_snapshots` SQLite row. The
single-row upsert is transactional. Loading validates the schema version and
reconstructs fresh domain dataclasses, including immutable record mappings and
history tuples; callers never receive SQLite objects.

Schema version 1 is the initial persistence format. Unknown schema versions,
malformed JSON, invalid record data, and unavailable database paths raise
explicit repository errors before a world is returned. No domain-specific
tables were introduced; regions, settlements, and NPCs remain generic records.

## Public Interfaces

- Added `GraphRepository(Protocol)` with `load_world() -> WorldState` and
  `save_world(state: WorldState) -> None`.
- Added `SQLiteRepository(database_path: str)` with the same two methods.
- Added `RepositoryError`, `RepositoryLoadError`, and `RepositorySaveError`.
- Changed `SimulationEngine` to accept an optional `GraphRepository` and added
  `save_world()`. `SimulationEngine()` remains backward-compatible and
  in-memory.
- Manager lifecycle APIs remain unchanged and own runtime mutation rather than
  persistence.

## Files Changed

- `CHANGELOG.md`
- `docs/adr/ADR-0007-repository-layer.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/02_repository_layer-report.md`
- `docs/technical_debt.md`
- `src/living_world/repositories/graph_repository.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/state/world_state.py`
- `tests/test_sqlite_repository.py`

## Test Evidence

`tests/test_sqlite_repository.py` verifies a round trip containing entities,
relationships, events, observations, beliefs, experiences, and belief and
experience history. It also verifies immutability after reload, malformed
snapshots, invalid paths, engine composition, and unsupported persisted schema
version. The unsupported-schema test updates `schema_version` to `2` and
asserts `RepositoryLoadError`, so no partial `WorldState` is returned.

## Validation

- `make` — passed (exit status 0; Ruff, Black, and the full pytest suite).
- `make examples` — passed (11 numbered examples passed).
- `git diff --check` — passed (exit status 0; no whitespace errors).

## Boundary Compliance and Blockers

All implementation changes are limited to the Task 02-approved repository,
state, engine, test, documentation, ADR, and report files. This correction
changed only the approved SQLite implementation, SQLite tests, and report.

Blockers: none. All required validation commands passed.
