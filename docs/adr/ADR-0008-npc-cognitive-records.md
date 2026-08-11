# ADR-0008: NPC Cognitive Records and Sleep Consolidation

## Status

Accepted

## Context

The simulator needs durable NPC cognition while preserving the distinction
between authoritative state, perception, and an NPC's interpretations. Raw
observation evidence and engine state cannot become NPC knowledge merely by
being retained for debugging.

## Decision

Introduce immutable, holder-scoped `Memory`, `Experience`, `Belief`, and
`NPCRelationship` records. They retain only internal provenance IDs and
NPC-visible prose. Use `CognitiveSalience` to express importance and explicit
core status.

Run deterministic consolidation only when an engine-scheduled entity is
sleeping. A completed cognitive day contains 24 ticks. Consolidation uses
prior-day observation descriptions, creates candidate beliefs rather than
facts, and uses persisted provenance to remain idempotent. SQLite snapshots
persist every cognitive collection and provenance link.

## Consequences

Advantages:

- NPC knowledge remains separate from world truth
- beliefs can remain uncertain or wrong
- deterministic provenance supports auditability and safe retries
- reload cannot silently discard cognitive history

Trade-offs:

- a fixed initial day length is an explicit policy to revisit if calendar
  mechanics are introduced
- candidate belief generation intentionally remains conservative and does not
  validate propositions against engine truth
