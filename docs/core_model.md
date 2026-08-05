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
- System

These are the only concepts understood by the simulation engine.

## Runtime Registries

The simulation distinguishes between runtime objects and registries.

Registries define the vocabulary available to the simulation while runtime
objects represent the current world state.

Current registries include:

- DefinitionManager
- ResourceDefinitionManager

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

Simulation systems should mutate the world only through managers.

## World History

The simulation records immutable history through `Event` objects.

Events are created exclusively through `EventManager.record()`.

Unlike entities and relationships, events are append-only and are never
modified or removed.

History represents objective facts about the world and forms the
foundation for future systems such as:

- NPC memory
- observations
- beliefs
- debugging
- simulation replay

## Simulation

Simulation behavior is implemented through `SimulationSystem`
implementations.

Systems execute in deterministic registration order through the
`SimulationScheduler`.

Each system is responsible for a single aspect of simulation behavior.

Some systems provide generic simulation mechanisms rather than
domain-specific behavior.

For example, the `ProgressSystem` advances a generic `progress` value by
`progress_rate` every simulation tick. Optional inclusive
`progress_min` and `progress_max` attributes constrain progression.

The engine assigns no semantic meaning to progress values. Higher-level
systems interpret progress according to their own requirements.

Systems mutate the world exclusively through managers.

The scheduler is responsible only for executing systems and advancing
the simulation tick.

## Simulation Engine

`SimulationEngine` is the primary entry point for applications using the
Living World engine.

The engine composes the runtime by constructing:

- WorldState
- DefinitionManager
- EntityManager
- RelationshipManager
- EventManager
- SimulationScheduler

The engine exposes a simplified API for running simulations while
preserving the existing responsibilities of managers and systems.

Simulation behavior remains implemented by simulation systems rather than
the engine itself.