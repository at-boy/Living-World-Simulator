# 15a — Canonical two-dimensional spatial contract ADR

## Status and dependency

Authorized after Task 16a. Execute on `task/15a-spatial-contract-adr`. This is
an architecture/documentation task only; Task 15b implements the contract.

## Decision to document

- The engine owns an abstract integer-coordinate plane.
- Immutable `Point(x, y)` placements represent mobile/small entities;
  immutable axis-aligned `Bounds(x, y, width, height)` represent areas,
  settlements, and structures. Width and height are positive integers.
- Placement records refer to an entity and optional containing entity. Bounds
  must lie inside declared parent bounds; points must lie inside their parent.
- Overlap is rejected for sibling structures unless an explicit typed overlap
  policy permits it. Areas may contain/overlap only as the ADR specifies.
- Ordering is by containing entity, geometry coordinates, then stable entity
  ID. Unplaced is an explicit state.
- Coordinates are engine truth. NPCs receive only later perception-translated
  relative descriptions, never raw coordinates by default.
- Define persistence/migration, detached inspection DTO, future pathfinding and
  v0.9 regional-extension consequences without implementing them.

## Allowed files and validation

- New spatial ADR, architectural/core-model/glossary documentation, changelog,
  journal, backlog, and Task 15a report only.
- Do not edit source, tests, examples, persistence, API, UI, or existing entity
  attributes. Run Markdown/link checks available in the repository and
  `git diff --check`; report unavailable tooling truthfully.

## Report

Create `docs/subagent_execution_plan/v0_6/15a_spatial_world_inspection-report.md`
with the decision, alternatives, boundary audit, validation, and Task 15b
implementation constraints.
