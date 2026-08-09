# ADR-0007: Repository Layer

## Status

Accepted

## Context

The runtime state existed only in memory. Applications needed persistence
without allowing storage details or mutable database objects to leak into
managers and domain records.

## Decision

Introduce `GraphRepository` with `load_world()` and `save_world(WorldState)`.
`SQLiteRepository` implements it with one versioned, JSON-serialized complete
world snapshot stored in SQLite. Saving uses a single transaction and an
upsert, while loading validates the schema version and reconstructs fresh
domain dataclasses.

`SimulationEngine` accepts an optional repository. It loads during engine
composition and persists explicitly through `save_world()`. Managers retain
their existing lifecycle APIs and continue to own runtime mutation only.

## Consequences

Advantages:

- persistence is independent of manager lifecycle behavior
- generic records avoid premature domain-specific storage tables
- immutable record constructors re-establish their immutable collections on load
- no-argument engine construction remains in-memory and backward compatible

Trade-offs:

- snapshots rewrite the complete world rather than independently querying records
- persisted JSON values must be JSON serializable
- future incompatible storage changes require a schema migration
