# 03a — HTTP world-inspection API foundation

## Task Description

Provide a read-only HTTP observability API for privileged external inspection
of the authoritative engine state. This is not an NPC interface and not an
alternative simulation, mutation, or action API.

## Context Needed

- Create: `src/living_world/api/inspection.py`, `tests/test_inspection_api.py`,
  `examples/013_world_inspection.py`, and
  `docs/subagent_execution_plan/03a_http_world_inspection_api-report.md`.
- Edit: `src/living_world/api/server.py`,
  `src/living_world/managers/definition_manager.py`,
  `src/living_world/managers/resource_definition_manager.py`, `Makefile`,
  `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Know: `SimulationEngine`, `WorldState`, every current manager, `Definition`,
  `ResourceDefinition`, and the repository snapshot boundary from Task 02.

## Interface Contract

```python
class WorldInspector(Protocol):
    def world_summary(self) -> Mapping[str, object]: ...
    def tick(self) -> int: ...
    def entities(self) -> tuple[Mapping[str, object], ...]: ...
    def entity(self, entity_id: str) -> Mapping[str, object] | None: ...
```

```python
def create_app(engine: SimulationEngine) -> FastAPI: ...
```

- `DefinitionManager.all() -> tuple[Definition, ...]` and
  `ResourceDefinitionManager.all() -> tuple[ResourceDefinition, ...]` expose
  read-only registry snapshots.
- The API provides GET-only endpoints for:
  - `/health` and `/world/tick`;
  - `/world` summary;
  - `/world/entities` and `/world/entities/{entity_id}` including attributes;
  - `/world/definitions` and `/world/resources`;
  - `/world/relationships`, `/world/events`, `/world/observations`,
    `/world/beliefs`, and `/world/experiences`.
- Unknown entity IDs return HTTP 404. Collection responses have deterministic
  ordering by record ID. Returned response values are JSON-safe snapshots, not
  live mutable state.
- The inspection API may intentionally disclose raw authoritative values to a
  privileged external operator. It must never be called by `NPCContextAssembler`,
  cognitive retrieval, a cognition client, or action handling. No POST, PUT,
  PATCH, DELETE, manager mutation, or simulation stepping endpoint is allowed.
- Retain `app` as a default in-memory application for the existing Uvicorn
  entry point, while tests and integrations use `create_app(engine)`.

## Test Criteria

- FastAPI integration tests verify every listed GET endpoint, response shape,
  deterministic ordering, entity 404 behavior, and absence of mutation routes.
- A returned payload can be mutated by a client without changing `WorldState`.
- Tests prove raw entity/resource data is available through inspection but is
  not added to `NPCContext` or any NPC-facing client contract.
- The example builds an engine, records representative data through managers,
  and inspects it through the HTTP app without direct state mutation.
- `make` passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/03a_http_world_inspection_api-report.md`.
Report endpoint inventory, response/ordering behavior, read-only enforcement,
NPC-boundary separation evidence, example result, and validation results.

## Boundary

- Touch only the listed API, manager, test, example, documentation, and report
  files.
- Ignore authentication, administration UI, write endpoints, action execution,
  and web-server deployment configuration; those require a separately agreed
  security/deployment capability.
- The external inspection boundary must remain explicit: it is privileged
  engine observability, never NPC knowledge.
