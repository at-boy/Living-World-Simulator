# Core Runtime Model

## Status

Accepted

## Context

The engine requires a small set of fundamental runtime concepts from
which all higher-level simulation behavior can be constructed.

Keeping the runtime intentionally small improves consistency,
maintainability and extensibility.

## Decision

The runtime is centered around five fundamental concepts:

- Definition
- Entity
- Relationship
- Event
- Simulation System

Everything else is infrastructure built upon those concepts.

Managers provide controlled mutation.

Schedulers execute systems.

The simulation engine composes the runtime but does not extend the core
model.

## Consequences

Advantages:

- small and consistent runtime model
- reusable architecture
- clear separation of responsibilities
- simpler long-term maintenance

Trade-offs:

- higher-level concepts require composition rather than specialized
  runtime objects
- new domains should be expressed using the existing runtime concepts
  whenever possible