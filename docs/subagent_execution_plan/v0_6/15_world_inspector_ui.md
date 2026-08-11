# 15 — Read-only World Inspector UI architecture and vertical slice

## Status

Deferred post-v0.5 candidate. Activate only after v0.5 is released and a
frontend deployment stack is selected by the project owner.

## Task Description

Provide an operator-facing web UI that consumes the existing read-only HTTP
inspection API to make a running world understandable: current-state views,
entity detail, time/tick display, resource/relationship/event history, and
deterministic charts. It is an observability client, not a simulation client.

## Context Needed

- Know `src/living_world/api/inspection.py`, `src/living_world/api/server.py`,
  Task 03a, and Task 13a inspection endpoints.
- Create a dedicated frontend application only after its framework, packaging,
  build, and serving approach are agreed in an ADR.
- Add UI tests appropriate to that selected stack plus API-contract fixtures;
  update operator/API documentation and create a task report.

## Interface Contract

- The UI issues HTTP `GET`, `HEAD`, and `OPTIONS` requests only to the
  inspection API. It has no simulation mutation endpoint, WebSocket command
  channel, local `WorldState`, manager, repository, or LLM integration.
- It renders API response DTOs as detached operator views. It does not reuse
  inspection responses as NPC retrieval, `NPCContext`, perception, or cognition
  input.
- Every chart uses a documented endpoint/schema and displays time/tick plus a
  clear empty/loading/error state. Collection ordering is the API's
  deterministic ordering; the UI does not manufacture world facts.
- Entity, definition, resource, relationship, event/history, observation,
  NPC, memory, belief, experience, knowledge, and cognitive-history views are
  added only when their corresponding explicit inspection endpoint exists.

## Test Criteria

- Contract tests prove the client makes no mutating request and handles empty,
  404, malformed, and unavailable API responses without changing world state.
- UI tests cover current world state, tick/time, entity drill-down, at least
  one deterministic graph, and an event/history view using stable fixtures.
- Tests prove inspection-only payloads have no path into `NPCContext`, LLM
  clients, retrieval, or action resolution.

## Boundary

- Never add a write endpoint or treat the UI as an alternative simulation API.
- Never expose the UI or inspection payloads to NPC/LLM code.
- Any future administration capability is a separately authorized feature with
  its own command/authentication/audit design.

## Orchestrator Report

Create `docs/subagent_execution_plan/v0_6/15_world_inspector_ui-report.md` when
activated. Include selected stack/ADR, endpoints consumed, views/charts,
read-only evidence, boundary evidence, tests, validation, and deferred work.
