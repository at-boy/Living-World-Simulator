# ADR-0016 — Canonical Two-Dimensional Spatial Contract

## Status

Accepted. Implemented by Tasks 15b and 15d.

## Context

The founding-settlement slice needs one authoritative spatial vocabulary before
structures, external dispatches, work, and inspection can depend on location.
Generic entity attributes are unsuitable: they have no lifecycle owner,
containment invariant, overlap rule, persistence contract, or safe separation
between privileged coordinates and NPC perception.

This decision covers an abstract local plane. It does not claim geographic
scale, terrain, navigation, travel time, line of sight, or a complete regional
world.

## Decision

### Geometry and placement

The engine owns an integer-coordinate Cartesian plane. Frozen, slotted value
records define:

- `Point(x, y)` for mobile or spatially small entities;
- `Bounds(x, y, width, height)` for areas, settlements, and structures, with
  positive integer width and height; and
- `Placement(entity_id, geometry, containing_entity_id, bounds_kind,
  overlap_policy)` as the one authoritative placement record for an entity.

Coordinates, dimensions, and identifiers reject booleans used as integers.
`bounds_kind` is required for bounds and is either `AREA` or `STRUCTURE`; it is
absent for points and unplaced records. Settlements and other open spatial
extents use `AREA`; a building or other constructed footprint uses `STRUCTURE`.
This is chosen explicitly by the placing domain and is never inferred from an
entity name or definition. Points must use `REJECT`. `geometry=None`, no
container, no bounds kind, and `REJECT` is the only valid explicit unplaced
state. `ALLOW_SIBLING_OVERLAP` on a point or unplaced record is invalid.
Placement state is never inferred from entity attributes.

Bounds use half-open cells: `[x, x + width) × [y, y + height)`. A point is
inside when both coordinates lie in those intervals. A child bound is inside a
parent when every child cell is inside it. Touching edges do not overlap;
sharing any cell does.

### Containment

`containing_entity_id` is optional. When present, it must name a different,
live, placed entity with bounds. Containment cycles are invalid. A parent area
may contain points, areas, or structures. A parent structure may contain points
or structures, but not areas. Points and unplaced entities cannot contain
anything. A child's geometry must be fully inside its parent's bounds.

Parent lifecycle never cascades. Replacing a bounded parent validates every
existing direct child against the proposed parent and thereby preserves the
already-valid descendant tree; a move, shrink, or kind change that would break
containment or the type matrix is rejected atomically. Removing or unplacing a
parent named by any direct child's `containing_entity_id` is rejected. Callers
must relocate, unplace, or remove descendants leaf-first, explicitly; unplacing
a child clears its own container link.

Task 15b introduces a narrow typed entity-removal guard implemented by the
spatial manager and consulted by `EntityManager.remove`. Removal is rejected
while the entity has any placement record or is named as a container. The
caller must remove spatial state leaf-first before removing the entity. There
is no silent cascade or stale-placement state. Placement creation/replacement
also rejects missing entities and entities whose persisted `destroyed_tick` is
not `None`. This preserves the live-entity invariant across both lifecycle
owners without giving the entity manager authority to mutate placements.

### Sibling overlap

Overlap is evaluated only between placed bounds with the same immediate
container, including `None` for top-level siblings. Points may coincide with
points and may lie within sibling bounds; containment is asserted only by the
explicit container link.

The default `REJECT` policy rejects any sibling-bounds overlap when either
record is a structure. Two sibling areas also reject overlap by default. The
only exception is the typed `ALLOW_SIBLING_OVERLAP` policy, which must be
present on both overlapping records. Mutual opt-in prevents a newly placed
record from unilaterally weakening an existing sibling's invariant. Parent and
child intersection is containment, not sibling overlap.

### Lifecycle and deterministic queries

A spatial manager alone creates, replaces, explicitly unplaces, and removes
placements. Replacement is validated against the world with the prior record
excluded and against every child before commit. Failed validation changes
neither state nor history.

Each successful call commits its placement change and exactly one immutable
event as one manager operation. If event construction or recording fails, the
placement remains unchanged and no event from that call remains. Event
`subject_id` is always the placed entity ID. The stable taxonomy and minimum
attributes are:

- `spatial_placement_created`: `current` placement snapshot;
- `spatial_placement_replaced`: `previous` and `current` snapshots;
- `spatial_placement_unplaced`: `previous` and the null-geometry `current`
  snapshot; and
- `spatial_placement_removed`: `previous` snapshot.

Each nested snapshot omits the subject entity ID and contains detached,
JSON-compatible `geometry`, `containing_entity_id`, `bounds_kind`, and
`overlap_policy`. Geometry is either `null`, `{kind: point, x, y}`, or
`{kind: bounds, x, y, width, height}`. Enum values serialize as their stable
lowercase strings. Existing recursive event freezing makes the committed
payload immutable.

Queries return frozen placement records using this exact ascending tuple key:

```text
(
  container_rank, container_id_or_empty,
  unplaced_rank, x_or_zero, y_or_zero,
  geometry_rank, width_or_zero, height_or_zero,
  entity_id,
)
```

`container_rank` is 0 for `None` and 1 otherwise; IDs compare lexically by
Python string/Unicode code-point order. `unplaced_rank` is 0 for placed and 1
for unplaced. Geometry ranks are Point 0, AREA Bounds 1, STRUCTURE Bounds 2,
and unplaced 3. Point and unplaced dimensions normalize to zero only in the
key; unplaced coordinates also normalize to zero. This is a total order and is
independent of insertion order.

### Persistence and privileged inspection

Task 15b advances SQLite snapshots to schema version 3 and stores placements as
a dedicated collection. Schema versions 1 and 2 load with an empty placement
collection: all legacy entities are spatially unknown, not implicitly at an
origin. Saving rewrites the current schema. Explicit unplaced records persist
as records with null geometry rather than disappearing.

Privileged inspection returns fresh, JSON-compatible DTOs in canonical query
order. A placed point exposes its exact `x` and `y`; bounds additionally expose
width, height, and kind. The DTO may contain internal entity/container IDs
because it is operator-only, but callers cannot mutate live state through it.

### NPC information boundary

Coordinates, dimensions, placement records, inspection DTOs, overlap policy,
and internal IDs are engine truth and do not enter `NPCContext`. Positive x is
east and positive y is north only for deterministic qualitative translation;
the integers still have no declared geographic scale.

Task 15d adds a `SpatialPerceptionEngine` behind the existing perception
protocol. It resolves only the caller-selected live observer and subject and
their authoritative placements. Point coordinates and doubled bounds centers
produce co-location or one of eight compass directions without magnitude.
Explicit containment may name a public container. An active direct `road` may
be described only when the caller includes that authoritative relationship in
the perception context; spatial perception never enumerates the world.

The result is one unpersisted immutable `Observation`. Its visible description
contains public names and qualitative prose. Detached evidence contains only
relation codes; it contains no geometry or IDs. Perception-time validation
rejects exact spatial numbers, internal identifiers, coordinate notation, and
privileged spatial vocabulary. Final context validation repeats those checks
against stored observations and all other NPC prose. The ordinary observation
manager remains the only recording path and holder-scoped context assembly
remains the only route into NPC cognition.

## Alternatives rejected

- Entity attributes such as `x` and `y` were rejected because they bypass a
  manager and cannot enforce cross-entity invariants.
- Floating-point coordinates were rejected because the founding slice needs a
  reproducible discrete contract, not precision or unit ambiguity.
- Geometry inferred from relationships was rejected because relationship
  meaning is domain-specific and cannot establish containment atomically.
- Automatic packing or overlap correction was rejected because it hides an
  invalid proposal instead of making the engine decision explicit.
- Persisting only placed entities was rejected because explicit unplaced state
  must survive resume.
- Feeding coordinates to NPC cognition was rejected because privileged engine
  precision is not equivalent to NPC knowledge.

## Consequences and implementation constraints

Task 15b must implement these exact frozen records, enum values, validation
rules, ordering, manager-owned lifecycle/events, schema-v3 migration, public
exports, and detached inspection. It must test missing/destroyed entities,
cycles, containment boundaries, parent replacement and leaf-first removal,
entity-removal guarding, mixed sibling geometry, valid policy combinations,
mutual overlap opt-in, replacement/event atomicity and taxonomy, explicit
unplaced persistence, migration defaults, exact ordering, detachment, event
immutability, and unchanged NPC context.

Task 15b must not add pathfinding, distance cost, motion simulation, work
execution, UI rendering, attribute inference, terrain, or NPC coordinate
exposure. Future pathfinding may consume this geometry without redefining it.
The v0.9 regional extension may map local planes into an explicit larger-scale
model, but must preserve local identities and migrate through a documented
contract rather than interpreting these integers as global geography.

Task 15d does not infer visibility, line of sight, proximity, distance bands,
navigation, movement, terrain, travel cost, or pathfinding. Its direct-road
prose reports only an already-authoritative caller-selected connection. These
capabilities remain separate future decisions.
