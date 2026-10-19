# Task 15b — Spatial domain, persistence, and inspection report

## Delivered domain and lifecycle

- `src/living_world/spatial/model.py` defines frozen, slotted `Point`, `Bounds`,
  and `Placement` records plus `BoundsKind` and `OverlapPolicy` enums. Runtime
  validation rejects boolean coordinates/dimensions, nonpositive bounds,
  invalid enum/object types, and illegal point/bounds/unplaced combinations.
- `src/living_world/spatial/manager.py` adds the sole placement lifecycle owner
  with create, atomic replace, explicit unplace, remove, get, container query,
  canonical all-query, persisted-state validation, and the typed entity-removal
  guard required by ADR-0016.
- `src/living_world/spatial/__init__.py` exports the public spatial contract
  without creating a `WorldState` import cycle.
- `WorldState.placements` stores authoritative records and
  `SimulationEngine.spatial` composes one manager. `EntityManager.remove`
  intrinsically rejects placement/container references and also consults the
  narrow `EntityRemovalGuard`, so direct composition cannot create stale state;
  it never mutates spatial state.

The manager validates live targets and parents, half-open containment, cycles,
the AREA/STRUCTURE parent matrix, every child on parent replacement, leaf-first
parent/entity removal, and mutual typed sibling-bounds overlap permission.
Failed validation leaves placement and events unchanged. Successful create,
replace, unplace, and remove calls use the four ADR event kinds with target
entity subjects and recursively immutable detached previous/current payloads.
Event-recording failure rolls back the operation.

Queries implement the exact ADR tuple order: `None` containers first, lexical
container IDs, placed before unplaced, coordinates, Point/AREA/STRUCTURE/
unplaced rank, dimensions, and lexical entity ID.

## Persistence and inspection

`src/living_world/repositories/sqlite_repository.py` advances snapshots to
schema version 3 and serializes placements in canonical order. Schema versions
1 and 2 load with an empty placement collection—even if a stray future field
is present—and rewrite as version 3.
Placed and explicitly unplaced records round-trip exactly. Cross-record spatial
invariants are revalidated on load, so missing/destroyed targets, invalid
parents, containment, cycles, and overlap cannot enter a returned world.

`WorldInspector.placements`, `EngineWorldInspector.placements`,
`GET /world/placements`, and `placement_count` expose detached JSON-compatible
operator geometry in canonical order. Mutation of a returned nested geometry
mapping does not affect `WorldState`.

## Tests, example, and information boundary

`tests/test_spatial_domain.py` covers strict geometry/state types, half-open
edges, containment and cycles, missing/destroyed entities, kind rules,
descendant-safe replacement, leaf-first guarded removal, mutual overlap,
canonical order, all lifecycle events and immutable payloads, SQLite v3
round-trip/v2 migration/malformed-reference rejection, detached inspection,
event failure, and unchanged NPC context. Inspection, SQLite, and Task 16
migration tests were updated for the new collection/schema.

`examples/026_spatial_domain.py` places an area and contained point through the
manager, persists them, reloads a new engine, and prints privileged detached
inspection.

No coordinate, dimension, placement, policy, internal ID, or inspection DTO is
added to perception, retrieval, `NPCContext`, cognition, or action proposals.
No cognition/perception/action, pathfinding, work, UI, terrain, motion, or
coordinate-like entity attribute was changed or added.

## Exact documentation and validation

Updated `CHANGELOG.md`, `docs/backlog.md`, `docs/core_model.md`,
`docs/engine_glossary.md`, `docs/http_inspection_api.md`, and
`docs/project_journal.md`, plus this report. The implementation follows
ADR-0016 without amending it.

- Focused spatial/integration tests: 44 passed.
- `make`: passed Ruff, Black, 435 tests, and examples 001–026.
- `make examples`: passed all 26 numbered examples.
- `git diff --check`: passed.

No blockers remain.
