# ADR-0017 — Partial External-World References

## Status

Accepted for Task 17 implementation.

## Context

The founding settlement needs named off-map trade and communication anchors
without pretending that a complete distant world is simulated.

## Decision

The engine owns frozen, slotted `ExternalWorldReference` records containing an
internal ID, operator name, role, allowed import/export goods, integer capacity,
delay and unit cost, a finite reliability in `[0, 1]`, contact state, and
creation tick. They contain no remote population, politics, buildings,
inventories, coordinates, or geography.

`ExternalWorldReferenceManager` alone creates references and changes contact
state. Names are unique after trim/case-fold comparison. IDs and queries use
lexical deterministic order. Contact follows UNKNOWN to KNOWN, KNOWN to
CONTACTABLE or UNAVAILABLE, and CONTACTABLE/UNAVAILABLE between one another.
Each successful mutation records one immutable event.

SQLite schema version 4 stores the collection. Versions 1–3 load it as empty
even if a stray future field exists. Privileged inspection exposes detached
exact policy values and IDs.

NPC code receives only a separate frozen `NPCExternalReference`: name, role,
and fixed qualitative contact prose. It never receives the ID, goods policy,
capacity, delay, cost, reliability, inspection DTO, or predicted outcome. Task
17 does not automatically inject even this filtered record into `NPCContext`;
a later holder-scoped perception path must establish knowledge.

## Consequences

Task 17a may consume these anchors for dispatch proposals and lifecycle, but it
may not reinterpret them as fully simulated places. Future promotion on-map
requires an explicit migration contract preserving identity. Task 17 adds no
dispatch, trade transfer, travel simulation, goals, work, or UI.
