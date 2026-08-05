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

## Replace GraphManager with RelationshipManager

**Status:** Open

The engine architecture now models the world as a property graph.

Travel, ownership, membership, social ties, and all other connections
are represented by `Relationship` objects.

`GraphManager` and its location-specific APIs should be removed and
replaced by `RelationshipManager`.

### Resolved when

-   `GraphManager` no longer exists.
-   World navigation uses travel relationships.
-   All examples use the new model.

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

## EntityManager

**Status:** Planned

Implement the first production manager responsible for the complete
lifecycle of entities.

Responsibilities include:

-   ID generation
-   Entity creation from definitions
-   Lookup
-   Removal
-   Validation
-   WorldState mutation

------------------------------------------------------------------------

## RelationshipManager

**Status:** In Progress

The initial skeleton exists.

The production implementation should:

-   Own relationship lifecycle.
-   Validate endpoints.
-   Generate IDs.
-   Support querying by source, target, and relationship kind.
-   Become the foundation for world navigation.

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

# Notes

Technical debt should decrease over time.

If this document continually grows, it is a sign that architectural
decisions are not being completed before new work begins.

The goal is to keep this document short, current, and actionable.
