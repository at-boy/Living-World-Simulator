# 15d — NPC-safe spatial perception translation

## Status and dependencies

Authorized after reviewed Tasks 15b and 18a. Execute next, before Task 19, on
`task/15d-npc-spatial-perception`. Task 19 depends on its reviewed merge.

## Task description

Add an engine-side perception translation layer that converts explicitly
selected authoritative placements and direct roads into qualitative prose in
an immutable `Observation`. Exact coordinates, dimensions, placement records,
internal IDs, and privileged inspection payloads remain outside NPC context.

## Binding translation contract

- Add a strictly typed `SpatialPerceptionEngine` implementing the existing
  `PerceptionEngine` protocol. It consumes one caller-authorized
  `PerceptionContext` and returns one unpersisted `Observation`; callers retain
  responsibility for recording through `ObservationManager`.
- Resolve only the context observer and subject. Never enumerate placements,
  relationships, or nearby entities into the result. Both entities must match
  live authoritative state and have placed geometry; otherwise fail closed
  with a typed spatial-perception error and no mutation.
- Describe subject containment, a shared immediate container, equal centers,
  and the subject's qualitative compass direction relative to the observer.
  Positive x is east and positive y is north. Compare point coordinates or
  doubled bounds centers, producing the eight compass directions without
  exposing magnitude, distance, or coordinates.
- A direct active `road` relationship may add qualitative path prose only when
  it is present in `PerceptionContext.relationships` and connects the observer
  and subject. Ignore unrelated, duplicate, future, or destroyed roads.
- Compose applicable facts in the stable order containment/shared container,
  relative direction/co-location, then direct road. Use public entity names;
  evidence/metadata may contain only detached primitive relation codes and
  provenance required for audit, never raw placement snapshots.
- Strengthen perception-time and final NPC-context validation so exact
  placement coordinates/dimensions, internal IDs, privileged spatial terms,
  or raw coordinate notation fail closed. Stored observations are revalidated
  by `NPCContextAssembler`, including observations not produced by the new
  translator.
- Do not add automatic visibility, line of sight, proximity/distance bands,
  pathfinding, navigation, movement, terrain, travel cost/time, work behavior,
  persistence schema changes, inspection endpoints, or UI.

## Allowed-file boundary

- `src/living_world/spatial/perception.py` and
  `src/living_world/spatial/__init__.py`
- `src/living_world/perception/npc_perception_boundary.py`
- `src/living_world/cognition/information_boundary.py`
- `src/living_world/__init__.py` only for intentional public exports
- `tests/test_spatial_perception.py`, `tests/test_spatial_domain.py`,
  `tests/test_npc_perception_boundary.py`, and `tests/test_npc_context.py`
- `examples/031_npc_spatial_perception.py`
- `CHANGELOG.md`, `docs/adr/ADR-0016-canonical-two-dimensional-spatial-contract.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/npc_information_boundary.md`, and `docs/project_journal.md`
- This plan, its saved `-prombt.md`, and the Task 15d `-report.md`

No other file may change without first amending this plan and its saved prompt.

## Tests and validation

- Regress the currently reproducible leak in which a stored observation such
  as `The well is at 47, 83.` enters NPC context despite matching placement
  coordinates.
- Cover point/bounds centers, every direction, co-location, containment,
  shared containers, direct roads, deterministic composition, insertion-order
  independence, and safe detached evidence.
- Cover unknown, mismatched, destroyed, and unplaced entities; unrelated,
  duplicate, future, and destroyed roads; internal IDs; coordinate/dimension
  prose; holder isolation; and unchanged privileged inspection.
- Run focused tests, `make`, separate `make examples`, and `git diff --check`.

## Report

Create
`docs/subagent_execution_plan/v0_6/15d_npc_safe_spatial_perception-report.md`
with implementation, boundary, test, example, and validation evidence.
