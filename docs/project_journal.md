# Living World Simulator – Project Journal

This document records the evolution of the project.

Unlike the CHANGELOG, this journal focuses on architectural decisions,
engineering milestones and lessons learned.

---

# 2026-08-05

## Commit 0027 — Local LLM Perception Clients

The provider-neutral LLM perception boundary now has concrete local HTTP
adapters for Ollama and llama.cpp. Both are deliberately loopback-only and use
structured JSON responses, so the model may contribute only a description and
confidence. No cloud endpoint or API-key path was added.

Qwen3-4B Q4_K_M is documented as the development default. Manual examples use
real local servers, while automated tests use injected fake transports. This
keeps normal validation deterministic, fast and independent of a downloaded
model.

## Commit 0026 — LLM Perception Boundary

This commit adds the first LLM-facing perception infrastructure without making
a language model part of the authoritative simulation.

`LLMPerceptionEngine` works through a small provider-neutral client protocol.
The client receives a curated request and may return only a human-readable
description and confidence. The engine retains ownership of observation
identity, tick, observer, subject, evidence and metadata. This prevents a
model response from becoming a source of simulation authority.

Unavailable providers, malformed responses and output that exposes internal
identifiers or exact numeric engine values automatically use the existing
deterministic perception engine. If that fallback also fails, the engine raises
an explicit error rather than inventing an observation.

The project is committed to locally hosted model servers. Setup guidance now
documents the expected Ollama and llama.cpp HTTP-server workflows, while
concrete HTTP adapters remain a later, separately testable capability.

## Commit 0010

### Property Graph

The runtime model was simplified into a property graph consisting of
Definitions, Entities and Relationships.

The vocabulary of the engine was aligned around:

- Definition
- Entity
- Relationship
- attributes
- definition_key
- initial_attributes

This established a common language for future development.

---

## Commit 0011

### Entity Lifecycle

Entity creation became the responsibility of `EntityManager`.

Runtime entities now have a single creation path, allowing validation,
identifier generation and initial attribute application to be
centralized.

This was the first major lifecycle manager implemented in the engine.

---

## Commit 0012

### Relationship Lifecycle

Relationship creation became the responsibility of
`RelationshipManager`.

Managers are now the exclusive mutation boundary of `WorldState`.

This completed the core lifecycle architecture of the runtime.

The next milestone is recording world history through an
`EventManager`.

## Commit 0013

### World History

The engine gained immutable world history through `Event` and
`EventManager`.

Unlike entities and relationships, events are append-only records.

This completed the four fundamental runtime concepts:

- Definition
- Entity
- Relationship
- Event

The next milestone is executing simulation systems on top of this
runtime.

## Commit 0014

### The World Begins to Evolve

This commit introduced deterministic execution of simulation systems.

The first production system, `ProgressSystem`, demonstrates state
changing over time.

A scheduler now executes registered systems and advances the simulation
tick.

This marks the transition from a static runtime to an evolving
simulation.

## Commit 0015

### Public Engine API

This commit introduced `SimulationEngine`, the primary entry point for
applications using the Living World engine.

The engine composes the runtime and exposes a simplified API while
keeping simulation behavior inside simulation systems.

With this commit the core runtime architecture reached its first stable
public interface.

## Commit 0016

### Engineering the Engine

This commit documents how the Living World engine is developed.

The development workflow, architectural decision process and engineering
principles are now documented alongside the codebase.

Existing ADRs were standardized into a consistent format and naming
scheme.

This establishes the project's long-term engineering conventions before
continuing implementation of new simulation capabilities.

## Commit 0017

### Improving the Developer Experience

This commit focused on the project's development workflow rather than the
simulation engine itself.

The default `make` target now performs the complete validation pipeline,
including formatting, static analysis, unit tests and execution of all
examples.

Examples are now treated as executable documentation, ensuring the
public API remains validated alongside the implementation.

Developer tooling was expanded with a snapshot helper to simplify
sharing repository snapshots during architectural reviews.

## Commit 0018

### Generic Bounded Progress

The generic ProgressSystem now supports optional inclusive lower and
upper bounds.

This allows a single reusable mechanism to represent many different
processes including construction, growth, decay and healing without
introducing domain-specific systems.

Dedicated tests verify progression with and without bounds, while the
examples now demonstrate bounded progression through the public
SimulationEngine API.

## Commit 0019

### Resource Definitions

The engine now maintains a registry of resource definitions.

Resources are introduced as part of the simulation vocabulary rather
than as standalone runtime objects. Runtime entities will later reference
registered resource definitions through namespaced attributes such as
`resource.water` and `resource.wood`.

This mirrors the existing separation between entity definitions and
runtime entities and establishes the foundation for future resource
systems.

## Commit 0020

### Entity Resources

Entities can now hold structured resource quantities through the
`resources` attribute.

Resource definitions establish the simulation vocabulary while entities
store the runtime quantities they currently possess.

This provides the foundation for future systems such as production,
consumption, transfer, decay and trade.

## Commit 0021

### Generic Resource Operations

The engine now provides a reusable `ResourceSystem` responsible for
modifying resource quantities.

Rather than allowing every simulation system to manipulate resource
dictionaries directly, common operations such as adding, removing and
transferring resources are centralized behind a single API.

Future simulation systems such as logging, farming, mining and trading
can build upon these generic operations without duplicating resource
manipulation logic.

## Commit 0022 — Observation and Perception

Commit 0022 introduces Observation as a first-class runtime concept and establishes the first version of the perception layer.

An `Observation` is an immutable record of what an observer perceived about a subject at a particular simulation tick. It is deliberately distinct from an `Event`: an event records something that happened in the world, while an observation records what an observer perceived.

Observations are recorded through `ObservationManager` and retained in `WorldState`. The manager owns observation identity and lifecycle, preserving the same separation of responsibilities used by the other runtime managers.

A new perception layer was introduced through `PerceptionContext` and the `PerceptionEngine` protocol. `PerceptionContext` provides the information available to a perception engine, including the observer, subject, capabilities, relationships, world state, and simulation tick.

The first concrete implementation is `DeterministicPerceptionEngine`. It demonstrates an important principle for the future NPC cognition architecture: perception is not simply reading an entity's attributes.

The same objective world state can produce different observations depending on the capabilities of the observer. For example, an NPC with little knowledge of woodcraft may perceive an oak simply as a tree, while a more experienced observer may perceive it as mature, healthy, and suitable for harvesting.

The resulting observation contains a human-readable description representing the observer's perception. Internal evidence retains the objective information used to produce that perception. This creates an explicit boundary between world truth and NPC-facing perception.

This distinction is important for the future LLM-based perception system. An NPC should not receive raw simulation attributes such as `wood = 120` simply because those values exist in the world. Instead, a future `LLMPerceptionEngine` can use objective world state and the observer's capabilities to produce a perception appropriate to that observer.

Commit 0022 therefore establishes the foundation for the later cognitive architecture involving observations, memories, beliefs, and experiences. Observation is the perception of an encounter; later cognitive systems will determine what, if anything, should be retained and given longer-term significance.

## Commit 0024 — Experience and Cognitive Consolidation

This commit introduces `Experience` as a distinct first-class cognitive concept rather than a synonym for memory or belief.

An experience is an NPC-specific record of learning gained through lived interaction. It can be created manually or generated from repeated observations as part of a future cognitive consolidation flow. The distinction matters: an observation is a perception, a memory is retained information, a belief is an interpretation, and an experience is the accumulated learning that emerges from repeated or significant lived encounters.

The model uses an `ExperienceHistoryEntry` pattern analogous to the existing belief history implementation so that the record remains append-only and traceable over time. Belief records were extended to optionally reference supporting experiences without collapsing the belief into the experience itself.

This design keeps the engine's authority separate from the NPC's knowledge. Raw simulation state remains engine truth, while experience records remain filtered, NPC-facing cognitive content suitable for later retrieval, context assembly and the future NPC Cognition Protocol.

## Commit 0025 — NPC Information Boundary and Cognitive Guardrails

This commit formalizes the architectural rule that the engine owns authoritative world truth while NPCs only receive what they can reasonably perceive, interpret, remember, or retrieve.

The project had already been moving in this direction through the perception and experience models, and the key gap was not in the implementation but in the documentation and roadmap discipline. The architecture and NPC information boundary documents already correctly described the separation, but the project needed the rule recorded as an active engineering commitment for future work.

The important guardrail is that an NPC LLM must never become a second source of truth. It may reason from filtered observations, memories, beliefs and experiences, but it must not receive raw simulation attributes, internal identifiers, hidden engine values, or direct access to `WorldState` as if that were NPC knowledge.

This milestone therefore preserves the intended boundary while also making it explicit for future retrieval, cognition and LLM features. The project now records the need for NPC-only context filtering, boundary enforcement, and retrieval over cognitively valid information rather than engine truth.

This is a documentation and architecture-hardening milestone rather than a broad NPC feature release: it keeps the discipline that the simulation remains authoritative and the NPC remains a participant within a filtered, interpreted model of the world.
