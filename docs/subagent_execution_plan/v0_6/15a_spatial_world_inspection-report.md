# Task 15a — Canonical spatial contract ADR report

## Decision delivered

ADR-0016 defines the binding Task 15b contract for an abstract engine-owned
integer plane. Frozen points represent mobile or spatially small entities;
positive, half-open axis-aligned bounds represent areas, settlements, and
structures. Placement is a dedicated record with an optional bounded parent,
an area/structure kind for bounds, a typed overlap policy, and a persisted
explicit unplaced state. Coordinates are never inferred from entity attributes.

Containment has an explicit type matrix and rejects missing, destroyed,
point/unplaced, self, cyclic, or geometrically invalid parents. Sibling bounds
reject overlap by default. Overlap is permitted only when both records opt into
`ALLOW_SIBLING_OVERLAP`; touching edges are not overlap. Points may coincide,
and a point lying inside a sibling bound does not invent containment.

Parent changes never cascade: invalidating replacement and removal/unplacement
with children are rejected, and descendants must be handled leaf-first. A
typed spatial guard prevents `EntityManager.remove` from creating missing-
entity or orphaned placement state. Point/unplaced records require `REJECT`;
settlement extents are explicitly AREA rather than inferred from definitions.

Canonical query ordering has a complete tuple key with `None` container first,
lexical IDs, placed before unplaced, coordinates, Point/AREA/STRUCTURE/unplaced
rank, dimensions, then entity ID. A manager alone
owns create, atomic replace, explicit unplace, and removal, with exactly one
immutable event per successful mutation and no mutation on failure.
The ADR fixes four event kinds (`spatial_placement_created`, `replaced`,
`unplaced`, and `removed`), subject semantics, detached previous/current
payload shapes, and rollback behavior if event recording fails.

## Persistence, inspection, and boundary

Task 15b advances SQLite snapshots to schema version 3. Version 1 and 2 worlds
load with no placement records; legacy entities are spatially unknown rather
than placed at an invented origin. Explicit unplaced records persist with null
geometry. Privileged inspection returns detached JSON-compatible placements in
canonical order and may include exact coordinates and internal IDs.

No placement, coordinate, dimension, policy, inspection DTO, or internal ID is
NPC context. A later perception task may derive qualitative holder-scoped
relative prose from verified geometry, but it may not reuse operator payloads
or expose exact coordinates by default.

## Alternatives

The ADR rejects coordinate entity attributes, floats, relationship-inferred
geometry, automatic packing/correction, dropping unplaced records, and direct
coordinate exposure to cognition. These alternatives either bypass lifecycle
ownership, weaken determinism, hide invalid proposals, lose resume truth, or
violate the NPC information boundary.

## Task 15b implementation constraints

Task 15b must implement the exact records/enums, half-open rules, containment
matrix, mutual overlap opt-in, canonical ordering, manager-owned lifecycle and
events, schema-v3 migration, public exports, and detached inspection. Tests
must cover invalid geometry/types and policy combinations, missing/destroyed
entities, guarded leaf-first entity/parent removal, cycles, containment edges,
sibling combinations, atomic replacement/event recording, explicit
unplacement, persistence/migration, exact ordering, detachment, immutable
event payloads, and unchanged NPC context.

It must not implement pathfinding, distance or travel cost, motion, terrain,
work, UI, attribute inference, regional geography, or NPC coordinate exposure.
Future pathfinding consumes this contract; a v0.9 regional model requires its
own explicit migration and cannot reinterpret local integers as global space.

## Exact files and validation

Changed only the allowed documentation surfaces: ADR-0016,
`docs/architectural_direction.md`, `docs/core_model.md`,
`docs/engine_glossary.md`, `CHANGELOG.md`, `docs/project_journal.md`,
`docs/backlog.md`, and this report. No source, test, example, persistence, API,
UI, or entity-attribute file changed.

- `git diff --check`: passed.
- Repository Markdown/link checker: unavailable; the Makefile and project
  metadata define no Markdown or link-check command.

No blockers remain.
