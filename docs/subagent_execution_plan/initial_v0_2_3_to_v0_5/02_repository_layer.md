# 02 — Repository layer

## Task Description

Introduce a persistence boundary and SQLite implementation while preserving
manager-owned lifecycle APIs and immutable historical records.

## Context Needed

- Create: `docs/subagent_execution_plan/02_repository_layer-report.md`.
- Create: `src/living_world/repositories/sqlite_repository.py`,
  `tests/test_sqlite_repository.py`.
- Edit: `src/living_world/repositories/graph_repository.py`,
  `src/living_world/state/world_state.py`, all files in
  `src/living_world/managers/`, `src/living_world/simulation/simulation_engine.py`.
- Edit documentation: `docs/technical_debt.md`, `docs/core_model.md`,
  `docs/engine_glossary.md`, `CHANGELOG.md`, `docs/project_journal.md`, and
  create `docs/adr/ADR-0007-repository-layer.md`.
- Know every current manager and immutable records: `Entity`, `Relationship`,
  `Event`, `Observation`, `Belief`, `Experience`, and `WorldState`.

## Interface Contract

```python
class GraphRepository(Protocol):
    def load_world(self) -> WorldState: ...
    def save_world(self, state: WorldState) -> None: ...

class SQLiteRepository:
    def __init__(self, database_path: str) -> None: ...
    def load_world(self) -> WorldState: ...
    def save_world(self, state: WorldState) -> None: ...
```

- Managers retain their public lifecycle APIs but receive a repository through
  engine composition rather than owning persistence details.
- Repository serialization preserves records and immutable history without
  exposing mutable database objects to callers.
- `SimulationEngine` accepts an optional `GraphRepository`; its no-argument
  in-memory behavior remains backward compatible.

## Test Criteria

- An in-memory world round-trips through SQLite with entities, relationships,
  events, observations, beliefs, and experiences intact.
- Event, observation, belief, and experience history remain immutable after
  reload.
- Existing manager tests pass without needing direct database access.
- Invalid paths and malformed persisted data fail with explicit repository
  errors, never partial world mutation.

## Orchestrator Report

Create `docs/subagent_execution_plan/02_repository_layer-report.md`. Report
the persistence schema/serialization decision, migration compatibility,
round-trip evidence, changed public interfaces, and validation results.

## Boundary

- Touch only repository, state, manager, engine, stated tests, and stated
  docs, plus the approved report artifact.
- Do not add domain-specific tables for regions, settlements, or NPCs; they
  are represented through generic records and later task-owned data.
- Adhere to manager-owned mutation and immutable-history rules.
