# ADR-0021 — Work orders and aggregate reservations

## Status

Accepted for Task 20.

## Decision

Work definitions, lifecycle state, and reservation history are frozen engine
records mutated only by `WorkManager`. Assignment creates one aggregate lock
over labor and settlement-held tool/consumable quantities without deducting
stock. Blocking and terminal transitions release the lock atomically before
recording their lifecycle event. Work selection, charging, progress scheduling,
and domain effects remain Task 20b responsibilities.

Work locations and labor use the canonical spatial containment tree. SQLite
schema 9 stores exact work records. Privileged inspection exposes detached
engine truth; NPCs receive only explicitly selected fixed qualitative prose.

## Consequences

Reservations prevent work-to-work double allocation but do not override other
authoritative resource consumers. Later undercollateralization is valid state
for the execution layer to block deterministically.
