# ADR-0019: Engine-owned goals and objective graphs

## Status

Accepted.

## Context

Founding mandates need durable, inspectable structure without allowing an NPC
or LLM to declare authoritative progress.

## Decision

Goals and objectives are frozen definitions with a closed criterion vocabulary.
Separate frozen records hold manager-owned status and evidence. The graph is
validated atomically and persisted as schema v6. Privileged inspection may see
the complete graph; NPC pathways receive only an explicit prose interpretation
whose label and description reject internal ID forms.
Task 18 does not evaluate criteria or execute work.

## Consequences

The engine has stable goal truth suitable for later deterministic evaluation.
Callers must use the manager for creation and transitions, and later systems
must translate world events into evidence without weakening the NPC boundary.
