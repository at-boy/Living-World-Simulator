# Core Runtime Model

The Living World Simulator is a property graph simulation engine.

Everything that exists is an Entity.

Everything that connects Entities is a Relationship.

Everything that changes the world is a System.

Everything that happens is an Event.

## Runtime Objects

- Entity
- Relationship
- Event
- Observation
- Belief
- System

These are the only concepts understood by the simulation engine.

## Runtime Registries

The simulation distinguishes between runtime objects and registries.

Registries define the vocabulary available to the simulation while runtime
objects represent the current world state.

Current registries include:

- DefinitionManager
- ResourceDefinitionManager

World-definition YAML is an input format for Definition vocabulary, not a
serialized `WorldState`. `SimulationEngine.load_definitions(path)` validates a
strict document containing only ordered definitions, their initial attributes,
and participating systems, then registers the complete set atomically. YAML
cannot introduce runtime entity identifiers, ticks, events, or NPC cognitive
records. Runtime entities remain exclusively owned by `EntityManager.create()`.

Additional registries may be introduced in the future as the simulation
grows.

## Design Principles

- The engine understands structure, not meaning.
- State belongs to the object that changes.
- Relationships are first-class objects with endpoints.
- Systems change the world.
- Events record history.
- Managers own lifecycle.
- Repositories own persistence.
- LLMs interpret truth but never own truth.

`LLMPerceptionEngine` is one such interpretation boundary. It submits only a
curated, provider-neutral perception request to a local model client, then
constructs the authoritative observation identity, tick and evidence itself.
Provider failure or invalid output falls back to deterministic perception.
`OllamaPerceptionClient` and `LlamaCppPerceptionClient` are loopback-only HTTP
adapters for that protocol; neither is allowed to use a cloud endpoint.

## Persistence

`GraphRepository` persists complete `WorldState` snapshots. The built-in
`SQLiteRepository` stores a versioned JSON representation in an atomic SQLite
transaction; its schema contains generic record collections only. Loading
constructs fresh domain records, so database rows and mutable SQLite objects
are never exposed to runtime callers.

`SimulationEngine(repository)` loads through the repository during composition.
Call `save_world()` to persist the current snapshot. Omitting a repository
retains the existing in-memory engine behavior.

## Entity Lifecycle

Runtime entities are created exclusively through `EntityManager.create()`.

The manager is responsible for:

- validating the referenced definition,
- generating a unique identifier,
- copying the definition's `initial_attributes`,
- applying caller-supplied attribute overrides,
- registering the entity in `WorldState`.

Production code should not instantiate runtime entities directly. Tests and migration tooling may do so when appropriate.

### Entity Resources

Entities may optionally contain a structured `resources` attribute.

The attribute maps resource identifiers to quantities owned by the
entity.

Example:

```python
{
    "resources": {
        "wood": 120,
        "water": 35,
    }
}
```

## Relationship Lifecycle

Runtime relationships are created exclusively through
`RelationshipManager.create()`.

The manager is responsible for:

- validating source and target entities,
- generating a unique identifier,
- creating the runtime relationship,
- registering the relationship in `WorldState`.

Together, `EntityManager` and `RelationshipManager` form the mutation
boundary of the simulation runtime.

Simulation systems should mutate the world only through managers or explicitly
provided system APIs. `EntityManager.set_attribute()` owns ordinary entity
attribute mutation; systems must not write to `WorldState` collections.

## World History

The simulation records immutable history through `Event` objects.

Events are created exclusively through `EventManager.record()`.

Unlike entities and relationships, events are append-only and are never
modified or removed. Event attribute trees are recursively immutable: mappings
are read-only, sequences are tuples, and sets are frozensets.

Observations are immutable records of an entity's perception of another
entity or the world. They are not events, although an event may result in
an observation. Observations are recorded through `ObservationManager`.
The observation description represents the perceiver's interpretation,
while internal evidence may retain objective simulator data for debugging
and provenance without exposing that data as the NPC-facing perception.

History represents objective facts about the world and recorded
perceptions of the world, forming the foundation for future systems such
as:

- NPC memory
- beliefs
- debugging
- simulation replay

A belief is an NPC-specific interpretation derived from observations,
memories, and lived experience. It is intentionally distinct from the
objective simulator truth represented in events and entity state.

## Simulation

Simulation behavior is implemented through `SimulationSystem`
implementations.

Systems execute in deterministic registration order through the
`SimulationScheduler`.

Each system is responsible for a single aspect of simulation behavior.

Some systems provide generic simulation mechanisms rather than
domain-specific behavior.

Current generic systems include:

- `ProgressSystem`, which advances bounded progress values over time.
- `ResourceSystem`, which provides generic operations for manipulating
  resource quantities stored by entities.
- `WeatherSystem`, which cycles the `weather` of definitions opting in with
  `systems: [weather]` using a non-empty `weather_cycle` sequence and optional
  integer `weather_index`.
- `PopulationSystem`, which applies integer `population_change` to integer
  `population` for definitions opting in with `systems: [population]`, then
  clamps it to optional `population_min` and `population_max` bounds.
- `OrganizationSystem`, which derives an opt-in organization's unique
  `member_count` from incoming `member_of` relationships.
- `SettlementSystem`, which derives an opt-in settlement's `is_located` and
  `owner_count` from one outgoing `located_in` relationship and incoming
  `owns` relationships.

Regions and terrain are ordinary entities. A `contains` relationship may link
a region to terrain it contains, while `adjacent` may link peer entities. These
relationship kinds are conventions, not engine primitives. Weather and
population events are recorded as `weather_changed` and `population_changed`
when their user-meaningful values change.

Organizations and settlements are likewise ordinary entities. The
`member_of` convention points from a member to an organization; `owns` points
from an owner to a settlement; and `located_in` points from a settlement to
its location. The organization and settlement systems ignore malformed or
ambiguous graph patterns. Material summary changes are recorded as
`organization_membership_changed`, `settlement_location_changed`, or
`settlement_ownership_changed` events.

The engine assigns no semantic meaning to these mechanisms. Higher-level
systems interpret them according to their own requirements.

For example, the `ProgressSystem` advances a generic `progress` value by
`progress_rate` every simulation tick. Optional inclusive
`progress_min` and `progress_max` attributes constrain progression.

The engine assigns no semantic meaning to progress values. Higher-level
systems interpret progress according to their own requirements.

Systems mutate the world exclusively through managers.

The scheduler is responsible only for calling `step(state)` in registration
order and advancing the simulation tick.

## Simulation Engine

`SimulationEngine` is the primary entry point for applications using the
Living World engine.

## Privileged World Inspection

The HTTP inspection API exposes detached, JSON-safe snapshots of authoritative
engine state for privileged external operators. `create_app(engine)` provides
GET-only `/world` inspection routes for the current tick, entities,
definitions, resources, relationships, events, observations, beliefs, and
experiences. Collection snapshots are ordered by record identifier.

Inspection is observability, not an action or simulation interface: it has no
mutation or stepping endpoints. Its raw values are deliberately outside the
NPC information boundary and must never be supplied to NPC context assembly,
cognitive retrieval, or cognition clients.

The engine composes the runtime by constructing:

- WorldState
- DefinitionManager
- EntityManager
- RelationshipManager
- EventManager
- ObservationManager
- SimulationScheduler

The engine exposes a simplified API for running simulations while
preserving the existing responsibilities of managers and systems.

Simulation behavior remains implemented by simulation systems rather than
the engine itself.

## Executable Documentation

Examples are executable documentation for the public runtime API. `make
examples` discovers numbered top-level files in `examples/`, executes them in
lexical order, reports the outcome for each file, and stops at the first
failure.

Locations are represented by ordinary `Entity` instances whose definitions
describe a location; there is no location-specific runtime type or registry.
