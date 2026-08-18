# ADR-0015 — Scenario Run Identity

## Status

Accepted

## Context

Unattended and resumable simulations need reproducible initial configuration.
Definitions are registry vocabulary rather than `WorldState`, while an SQLite
snapshot previously contained no evidence of which configuration created it.

## Decision

Versioned YAML scenarios identify a scenario, deterministic seed, definition
document, initial graph, and bounded-run defaults. Scenario-local labels are
resolved through managers and never become runtime IDs in scenario prose.

`WorldState` persists immutable `RunMetadata` containing the scenario key,
schema version, seed, and a SHA-256 configuration fingerprint that includes the
definition document. Resume reloads definitions and requires an exact metadata
match before stepping. Reapplying the same scenario is idempotent. A populated
legacy world cannot be bound implicitly to a scenario.

## Consequences

- New scenario runs are reproducible and incompatible configuration fails
  before simulation advances.
- Definitions remain configuration rather than duplicated snapshot state.
- Schema-v1 snapshots load as unbound legacy worlds and rewrite in the current
  schema on save.
- Run metadata is privileged operator inspection data and never NPC context.
