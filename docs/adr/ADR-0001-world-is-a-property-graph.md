# World as a Property Graph

## Status

Accepted

## Context

The simulation requires a generic representation of the world that is
independent of domain concepts.

Locations, roads, rivers, ownership, family ties, trade routes and other
connections all represent relationships between entities.

A graph-based model provides a consistent foundation for representing
these connections.

## Decision

The world is represented as a property graph.

Entities are connected through relationships.

Navigation is a projection of travel-related relationships rather than a
separate world structure.

## Consequences

Advantages:

- one generic representation for all connections
- reusable relationship model
- extensible world structure
- supports navigation, ownership and social networks equally well

Trade-offs:

- graph traversal may be more complex than specialized structures
- developers must model domains through relationships rather than custom
  hierarchies