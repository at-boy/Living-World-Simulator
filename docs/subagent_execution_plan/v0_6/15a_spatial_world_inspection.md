# 15a — Spatial world-layout inspection contract and visualization

## Status

Deferred post-v0.5 candidate. It depends on Task 15 and on an agreed canonical
engine-owned placement model.

## Task Description

Establish a canonical spatial layout projection for areas, settlements,
buildings, and later world elements, then render it in the read-only World
Inspector UI with click-through inspection.

## Context Needed

- Know the completed generic entity/relationship world model, settlement and
  location conventions, HTTP inspection API, and Task 15 UI contract.
- Before implementation, write an ADR defining whether placement uses
  coordinates, regions/bounds, topology/adjacency, or a combination; define
  units, validation, persistence, migrations, and deterministic rendering
  order.
- The owning domain/repository/API/UI tasks must be split after that ADR; do
  not overload a UI task with unapproved spatial-domain changes.

## Interface Contract

- The engine owns one canonical spatial placement/layout representation.
  Renderers consume a detached, read-only inspection DTO; they never infer
  placement from arbitrary entity attributes, names, relationship iteration
  order, or CSS coordinates.
- The layout DTO includes stable display identifiers/labels, kind, placement
  geometry or topology, and explicit links to existing inspection resources.
  It contains no mutable runtime object or NPC-facing cognitive data.
- The UI supports deterministic placement rendering, empty/unplaced states,
  and selecting an element to navigate to its existing read-only detail view.

## Test Criteria

- Domain tests cover valid/invalid placements, deterministic ordering, and
  repository round trips if placement is persisted.
- API tests prove DTO detachment and read-only access.
- UI tests cover areas, towns, buildings, overlap/unplaced behavior, and
  click-through without issuing mutations.

## Boundary

- Spatial layout is authoritative engine state only when an approved domain
  task owns it; the map remains an inspection projection.
- No UI-derived placement may mutate the world, and map data must never enter
  NPC perception/cognition/LLM context without a dedicated perception task.

## Orchestrator Report

Create `docs/subagent_execution_plan/v0_6/15a_spatial_world_inspection-report.md`
when activated. Include the ADR decision, schema, persistence/API/UI evidence,
boundary audit, validation, and remaining mapping limitations.
