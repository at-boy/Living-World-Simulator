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

## Replace Location with Entity

**Status:** Open

Locations are no longer a special engine concept.

A location should simply be an `Entity` whose definition/archetype
represents a location.

### Resolved when

-   `Location` class is removed.
-   Examples create location entities through `EntityManager`.
-   Systems operate on entities rather than location-specific classes.

------------------------------------------------------------------------

## EventManager

**Status:** Planned

Implement immutable historical event recording.

The EventManager should expose a `record()` API rather than direct list
manipulation.

------------------------------------------------------------------------

## Repository Layer

**Status:** Planned

Managers communicate with repositories instead of directly interacting
with persistence.

SQLite will become the first repository implementation.

------------------------------------------------------------------------

# Medium Priority

------------------------------------------------------------------------

## Relationship lifecycle bypasses RelationshipManager

**Status:** Open

The current example writes relationships directly into
WorldState.

This temporarily violates ADR-0004
(Managers are the only code allowed to mutate WorldState).

This debt will be removed when RelationshipManager owns
relationship creation.

### Resolved when

- Example uses RelationshipManager.
- Systems use RelationshipManager.
- No production code mutates world_state.relationships directly.

------------------------------------------------------------------------

# Low Priority

------------------------------------------------------------------------

## Example runner only executes the first example

**Status:** Open

`make example` currently runs only `examples/001_create_world.py`.

As additional examples are added, the build should execute all examples to ensure they remain runnable.

### Resolved when

- `make examples` (or an equivalent target) executes every example.
- Each example reports PASS/FAIL.
- The build stops if any example fails.

------------------------------------------------------------------------

## Resolved

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

The runtime now records immutable history through `EventManager`.

The engine has a dedicated history mechanism that future systems can
build upon.

------------------------------------------------------------------------

# Notes

Technical debt should decrease over time.

If this document continually grows, it is a sign that architectural
decisions are not being completed before new work begins.

The goal is to keep this document short, current, and actionable.
