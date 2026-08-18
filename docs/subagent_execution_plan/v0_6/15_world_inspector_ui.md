# 15 — FastAPI-hosted read-only World Inspector

## Status and dependencies

Authorized after Tasks 17–22 and 21 have supplied their inspection endpoints.
Execute on `task/15-world-inspector-ui` from the current milestone branch.
Task 15c depends on its reviewed merge.

## Task description

Serve a same-origin, dependency-light HTML/CSS/JavaScript inspector from
FastAPI. It is an operator observability client, never a simulation,
administration, NPC, or LLM API. No Node toolchain or frontend framework is
introduced.

## Interface and behavior

- Serve static assets and one documented inspector route from the existing app.
- Consume only documented `GET`, `HEAD`, and `OPTIONS` inspection endpoints.
- Show world/tick, entities, relationships, resources, events/history, needs,
  goals/objectives, work, external dispatches, and settlement stage.
- Provide deterministic ordering, accessible navigation, entity drill-down,
  and explicit loading, empty, malformed-response, 404, and unavailable states.
- Keep spatial rendering out of this task; Task 15c owns the map.

## Allowed files and tests

- FastAPI server/inspection integration, new packaged static assets/templates,
  focused UI/API contract tests, operator docs, packaging metadata if required,
  changelog, journal, backlog, and Task 15 report.
- Tests must prove the browser client contains no mutating request, inspection
  DTOs are detached, static assets package correctly, and no inspector payload
  reaches retrieval, `NPCContext`, cognition, or action resolution.
- Do not add write routes, WebSockets, runtime managers in browser code, Node
  dependencies, spatial-domain changes, or inferred world facts.
- Run `make`, `make examples`, and `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/15_world_inspector_ui-report.md` with
routes/assets, views, read-only evidence, tests, validation, and deferred work.
