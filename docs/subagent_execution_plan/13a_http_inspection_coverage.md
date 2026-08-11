# 13a — HTTP inspection coverage for v0.4–v0.5

## Task Description

Extend the read-only inspection API to cover all v0.4 and v0.5 cognitive and
AI-layer records, while preserving its strict separation from NPC-facing data.

## Context Needed

- Create: `examples/023_http_inspection.py`,
  `docs/subagent_execution_plan/13a_http_inspection_coverage-prombt.md`, and
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
  - existing `/world/observations`, plus NPC-relationship interpretations in
    holder-scoped cognitive history, so all persisted v0.4 cognitive record
    categories are covered.
- Extend `WorldInspector` itself with the complete implemented inspection
  surface; do not rely on methods present only on `EngineWorldInspector`.
- Extend `/world` counts for memories, knowledge, and NPC relationships while
  preserving all existing keys.
- Collection endpoints return `200` with an empty array when no records exist.
  `/world/cognitive-history/{holder_id}` returns `404` when the holder entity is
  unknown and a deterministic empty-category projection for a known holder
  with no cognitive records. All collections and per-holder categories are
  ordered by record ID.
- Conversations, meetings, council calls/results, invitation feedback, and
  action resolutions are deliberately ephemeral return values and are not
  stored in `WorldState`. Do not add `/world/conversations` or `/world/councils`,
  invent empty persistence-like endpoints, or change their lifecycle in this
  task. Document that omission in the report and operator documentation.
- New endpoints remain read-only and return recursively detached copies rather
  than live state.
- “Other world elements” are added through explicit `WorldInspector`
  extensions and tests, not a raw arbitrary-object endpoint.
- None of these endpoints, response DTOs, or raw cognitive provenance values
  may be used as input to NPC retrieval, context assembly, perception, or LLM
  cognition.

## Test Criteria

- Tests cover each endpoint with populated and empty data, 404 behavior,
  stable ordering, and response-copy isolation.
- Tests cover the extended world-summary counts, complete `WorldInspector`
  protocol surface, and omission of ephemeral conversation/council routes.
- Tests prove cognitive history is externally inspectable but holder isolation
  still applies to NPC context/retrieval.
- No non-GET route is introduced by this task.
- The example exercises the completed persisted inspection surface. Existing
  Makefile wildcard discovery must run example 023; edit the Makefile only if
  required to preserve or clarify that generic discovery contract.
- `make`, `make examples`, and `git diff --check` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/13a_http_inspection_coverage-report.md`.
Report endpoint additions, record coverage, response isolation, NPC-boundary
proof, example result, and validation results.

## Boundary

- Touch only the listed API/test/example/documentation/report files.
- The saved `-prombt.md` is an approved task artifact within this boundary.
- Do not add any endpoint that mutates the world or lets an NPC/LLM call the
  inspection API.
- Preserve the Task 03a API factory and its privileged-observability contract.
