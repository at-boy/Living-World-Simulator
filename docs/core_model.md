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