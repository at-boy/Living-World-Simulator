# 13a — HTTP inspection coverage for v0.4–v0.5

## Task Description

Extend the read-only inspection API to cover all v0.4 and v0.5 cognitive and
AI-layer records, while preserving its strict separation from NPC-facing data.

## Context Needed

- Create: `examples/023_http_inspection.py` and
  `docs/subagent_execution_plan/13a_http_inspection_coverage-report.md`.
- Edit: `src/living_world/api/inspection.py`, `src/living_world/api/server.py`,
  `tests/test_inspection_api.py`, `Makefile`, `docs/core_model.md`,
  `docs/engine_glossary.md`, `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: all v0.4/v0.5 records and managers delivered by Tasks 07–13,
  especially NPC identity/schedules, memory, knowledge, belief/experience
  histories, retrieval results, conversations, councils, and action outcomes.

## Interface Contract

- Extend the inspector with GET-only, deterministic, JSON-safe endpoints for:
  - `/world/npcs`, including identity, occupation, and schedule presentation;
  - `/world/memories`, `/world/knowledge`, `/world/experiences`, and
    `/world/beliefs` with their recorded history/provenance suitable for a
    privileged inspector;
  - `/world/cognitive-history/{holder_id}` as a holder-scoped inspection
    projection;
  - `/world/conversations` and `/world/councils`, if those services persist
    inspectable immutable records.
- New endpoints return 404 for unknown holder IDs and preserve deterministic
  collection ordering. They remain read-only and return copies rather than
  live state.
- “Other world elements” are added through explicit `WorldInspector`
  extensions and tests, not a raw arbitrary-object endpoint.
- None of these endpoints, response DTOs, or raw cognitive provenance values
  may be used as input to NPC retrieval, context assembly, perception, or LLM
  cognition.

## Test Criteria

- Tests cover each endpoint with populated and empty data, 404 behavior,
  stable ordering, and response-copy isolation.
- Tests prove cognitive history is externally inspectable but holder isolation
  still applies to NPC context/retrieval.
- No non-GET route is introduced by this task.
- The example exercises the completed inspection surface and `make` passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/13a_http_inspection_coverage-report.md`.
Report endpoint additions, record coverage, response isolation, NPC-boundary
proof, example result, and validation results.

## Boundary

- Touch only the listed API/test/example/documentation/report files.
- Do not add any endpoint that mutates the world or lets an NPC/LLM call the
  inspection API.
- Preserve the Task 03a API factory and its privileged-observability contract.
