# Core Runtime Model

The Living World Simulator is a property graph simulation engine.

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
