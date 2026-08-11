# Technical Debt

This document tracks known implementation gaps between the current
codebase and the intended architecture.

It is **not** a bug tracker and **not** a feature backlog.

-   **Backlog** contains future capabilities that have not been started.
-   **Technical Debt** contains work that has already been designed or
    partially implemented but has not yet been brought into alignment
    with the architecture.

Each item should include enough context to explain **why** it exists and
**what** will resolve it.

When an item is completed, it should be removed from this document as
part of the same pull request.

------------------------------------------------------------------------

# High Priority

------------------------------------------------------------------------

## Resolved

------------------------------------------------------------------------

### Entity lifecycle

`EntityManager` now owns runtime entity creation, identifier generation, and registration within `WorldState`.

------------------------------------------------------------------------

### Relationship lifecycle

`RelationshipManager` now owns runtime relationship creation,
validation and registration.

Examples and production code no longer mutate
`WorldState.relationships` directly.

------------------------------------------------------------------------

### World history

The runtime now records recursively immutable history through `EventManager`.
Event attributes are detached from callers and recursively frozen, so recorded
history cannot be changed through nested mappings or collections.

The engine has a dedicated history mechanism that future systems can
build upon.

------------------------------------------------------------------------

### Repository layer

`GraphRepository` now defines complete-world persistence and
`SQLiteRepository` provides a versioned, atomic SQLite snapshot implementation.
`SimulationEngine` composes an optional repository without changing manager
lifecycle APIs or its no-argument in-memory behavior.

------------------------------------------------------------------------

### Baseline audit (v0.2.3)

`Location` has been removed; `examples/001_create_world.py` creates its
location entities through `EntityManager`, and no location-specific runtime
collection remains.

`RelationshipManager` is the sole production mutation boundary for
relationship creation and registration in `WorldState.relationships`; the
example uses that manager.

`make examples` automatically discovers top-level files named
`[0-9][0-9][0-9]_*.py`, executes them in lexical order, reports PASS or FAIL
for each file, and stops on the first failure.

------------------------------------------------------------------------

# Notes

Technical debt should decrease over time.

If this document continually grows, it is a sign that architectural
decisions are not being completed before new work begins.

The goal is to keep this document short, current, and actionable.
