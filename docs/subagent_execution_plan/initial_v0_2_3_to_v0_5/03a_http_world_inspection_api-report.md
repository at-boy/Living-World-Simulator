# 03a HTTP World Inspection API Report

## Endpoint Inventory

`create_app(engine)` provides GET-only `/health`, `/world/tick`, `/world`,
`/world/entities`, `/world/entities/{entity_id}`, `/world/definitions`,
`/world/resources`, `/world/relationships`, `/world/events`,
`/world/observations`, `/world/beliefs`, and `/world/experiences` routes. The
existing Uvicorn entry point retains an in-memory default application.

## Response and Ordering Behavior

All endpoint values are detached JSON-safe snapshots. Record collections are
sorted by identifier; definition and resource registries are sorted by key.
Unknown entity identifiers return HTTP 404.

## Read-Only Enforcement

The route inventory contains no POST, PUT, PATCH, or DELETE handlers. The API
does not call managers to mutate state and exposes no simulation stepping
operation.

## NPC-Boundary Separation

Inspection uses a dedicated `EngineWorldInspector`, not `NPCContextAssembler`
or an NPC-facing client contract. Tests show an operator can inspect raw wood
and health values while assembled NPC context does not contain them.

## Example Result

`examples/013_world_inspection.py` composes an engine, records entities and
representative manager-owned records, then reads the summary, entity, and
event snapshots through the HTTP app without direct state mutation.

## Validation

The inspection integration tests cover every route, response ordering, entity
404 behavior, detached payloads, GET-only routes, and the NPC boundary. Ruff,
Black, the focused test suite (3 tests), the complete pytest suite (141 tests),
the executable example, and `make` all pass successfully.

## Exact Files Changed

- `src/living_world/api/inspection.py`
- `src/living_world/api/server.py`
- `src/living_world/managers/definition_manager.py`
- `src/living_world/managers/resource_definition_manager.py`
- `tests/test_inspection_api.py`
- `examples/013_world_inspection.py`
- `Makefile`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/03a_http_world_inspection_api-report.md`

## Boundary Compliance

Only the API, manager, test, example, documentation, changelog, Makefile, and
report files authorized by the task were changed. The inspection surface is
explicitly privileged observability: it has no write, action, administration,
or simulation-stepping endpoint, and it is not used by NPC context assembly,
cognitive retrieval, cognition clients, or action handling.

## Blockers and Deferred Work

None.
