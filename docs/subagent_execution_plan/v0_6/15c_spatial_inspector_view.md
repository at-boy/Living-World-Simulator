# 15c — Spatial Inspector view

## Status and dependencies

Authorized after reviewed Tasks 15 and 15b. Execute on
`task/15c-spatial-inspector-view`.

## Task description

Render Task 15b's detached spatial DTO in the FastAPI-hosted inspector. Show
points/bounds with deterministic scaling, labels, overlap/unplaced states, and
click-through to existing entity detail. Rendering never creates placement or
mutates world state.

## Boundary and tests

- Edit only Task 15 static assets/server packaging, focused UI tests, operator
  docs, changelog, journal, backlog, and Task 15c report.
- Cover areas, settlements, structures, point entities, empty/unplaced data,
  permitted overlap, deterministic render order, resize behavior, click-through,
  and API/error states without issuing mutations.
- Do not edit spatial domain/persistence, add administration, infer coordinates,
  or expose map data to NPC code. Run `make`, `make examples`, and
  `git diff --check`.

## Report

Create `docs/subagent_execution_plan/v0_6/15c_spatial_inspector_view-report.md`.
