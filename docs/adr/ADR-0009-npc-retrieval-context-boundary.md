# ADR-0009: NPC Retrieval and Context Boundary

## Status

Accepted

## Context

The engine retains authoritative entities, attributes, observations, cognitive
provenance, and record identifiers. NPC reasoning needs useful context, but an
LLM must not obtain those engine-side values merely because they are retained
in `WorldState`.

## Decision

Introduce a read-only `CognitiveRetriever` abstraction and use
`DeterministicCognitiveRetriever` as the initial implementation. It projects
only holder-scoped `Memory`, `Belief`, and `Experience` records selected by
core salience policy. The default selection contains at most ten records,
ordered by descending importance, descending tick, then ascending record ID.

Relationships and source-attributed knowledge are available only through a
non-empty, case-insensitive topic query. They never expose provenance,
metadata, confidence, or raw entity attributes; knowledge source attribution
is retained only as NPC-readable prose.

`NPCContextAssembler` accepts an internal holder only to perform the lookup,
then returns a context with no holder or entity ID. It exposes display-name
identity, prose self-knowledge, holder-scoped observation descriptions, core
cognition, and optional retrieval results. `NPCInformationBoundary` validates
the completed projection before it is returned, rejecting mappings, engine
objects, known internal IDs, and numeric values copied from entity attributes.

## Information Boundary

1. The engine knows the complete `WorldState`, raw entity attributes,
   observation evidence, metadata, confidence, provenance, and internal IDs.
2. An NPC can perceive only its own observation descriptions and receive only
   prose capability descriptions supplied by the caller.
3. Retrieval transforms cognitive records into `RetrievedCognition`, removing
   IDs, provenance, metadata, confidence, and raw attributes.
4. Raw mappings, engine objects, internal identifiers, and authoritative
   numeric attribute values are hidden.
5. NPCs can remember holder-scoped memory, belief, and experience prose.
6. NPCs can infer from those interpretations, while beliefs and knowledge do
   not become simulation truth.
7. The future LLM receives only `NPCContext` after boundary validation.
8. Authoritative records remain engine-only for simulation, inspection,
   debugging, and audit.

## Consequences

Advantages:

- NPC cognition has deterministic, testable retrieval semantics.
- The context interface cannot accidentally carry a holder ID or raw capability
  mapping.
- A future vector/RAG retriever can implement `CognitiveRetriever` without
  changing the NPC-facing context contract.

Trade-offs:

- Topic matching is intentionally simple case-insensitive substring matching.
- Observation-description filtering is further strengthened by Task 09a;
  this decision does not modify perception engines.
