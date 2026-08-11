# Living World Simulator – Project Journal

This document records the evolution of the project.

Unlike the CHANGELOG, this journal focuses on architectural decisions,
engineering milestones and lessons learned.

---

# 2026-08-10

## Perception-Boundary Enforcement

Perception now has an executable translation boundary rather than relying on
provider instructions alone. Both deterministic and LLM-backed engines validate
the NPC-readable observation description with their private
`PerceptionContext`; protected nested values and identifiers cannot be repeated
as visible prose. Unsafe LLM output falls back deterministically, while an
unsafe fallback fails closed. Later NPC-context assembly repeats only the
description validation and has no engine context, evidence, or metadata access.
The curated request sent to a perception provider remains simulation machinery,
not an NPC cognition request.

## Cognitive Records and Sleep Consolidation

The v0.4 cognitive model now distinguishes immutable, holder-scoped memories,
experiences, beliefs, and NPC relationship interpretations from authoritative
graph relationships and simulator state. Each record uses explicit salience;
important and core remain separate policy states. Observation IDs are retained
only for internal provenance.

`CognitiveConsolidationSystem` executes after schedules, and only while an
entity's engine-owned activity is `sleeping`. The first completed day ends at
tick 24, using a fixed 24-tick day; its visible observation descriptions may
be retained as memories, while repeated observations may produce an experience
and a candidate belief. It never consumes observation evidence, entity
attributes, resource quantities, event internals, or raw IDs as visible prose.
Persisted provenance makes rerunning the same consolidation idempotent after
SQLite reload.

## NPC Identity, Schedules, and Occupations

NPC identity, occupation, and schedules are now validated domain values stored
as JSON-compatible attributes on ordinary entities. This preserves the generic
property-graph runtime: there is no NPC entity subclass, separate NPC store, or
special persistence path. `ScheduleSystem` uses the managers already owned by
the engine to derive the current activity at each tick and records only
material transitions as immutable events. Presentation capabilities remain
prose descriptions; numerical skill values remain authoritative engine data
and do not enter the identity model or NPC cognition context.

## Settlement Economy

The v0.3 settlement milestone remains a composition of generic graph and
attribute mechanisms. Construction uses existing bounded progress plus
entity-held material requirements, while housing derives allocation from
`housed_in` edges only after construction. Production and road-gated trade use
the shared `ResourceSystem`; it now protects non-negative quantities and makes
an insufficient transfer atomic from the callers' perspective. Roads, trades,
and dwellings remain ordinary relationships and entities, not specialized
runtime models. Every material outcome records an immutable event in stable
system and identifier order.

## Immutable Event Attributes

Events now freeze their entire attribute tree at construction time. Nested
mappings, sequences, and sets become read-only mappings, tuples, and
frozensets respectively, and SQLite serialization converts that frozen tree to
JSON-safe data before reconstructing the same immutable event contract on load.

## Organization and Settlement Foundations

Organizations and settlements are ordinary property-graph entities rather
than bespoke runtime types. `member_of`, `owns`, and `located_in` document the
direction of their graph edges. Deterministic systems summarize only valid,
unambiguous graph structure through `EntityManager` and record material
changes through immutable events, leaving construction and economy to later
systems.

## Deterministic World Simulation Foundations

Weather and population are now deterministic systems over ordinary entities
rather than new region, terrain, weather, or population runtime types.
Definitions opt in through `systems`; a weather participant supplies a cycle,
while a population participant supplies bounded integer attributes. Regions
and terrain use normal `contains` or `adjacent` relationships, preserving the
property-graph model. Material changes are retained as immutable events, and
the scheduler invokes every system as `step(state)` in registration order.

## Repository Layer

The runtime now persists generic `WorldState` snapshots through the
`GraphRepository` boundary. `SQLiteRepository` uses a versioned JSON payload
inside an atomic SQLite transaction, preserving all core records and immutable
history without adding domain-specific tables. `SimulationEngine` optionally
loads this snapshot at composition time and exposes explicit saving while its
default in-memory construction remains unchanged.

---

# 2026-08-09

## v0.2.3 Baseline Audit and Executable Documentation

The v0.2.3 baseline audit confirmed that locations are ordinary entities,
created through `EntityManager`, with no `Location` runtime class or
location-specific collection. It also confirmed that `RelationshipManager` is
the sole production mutation boundary for relationships, and that immutable
history is recorded through `EventManager`.

`make examples` now discovers numbered top-level examples automatically in
lexical order. Each execution reports PASS or FAIL, and the command stops at
the first failed example. This keeps every example usable as executable
documentation during the standard validation workflow.

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

## Commit 0026 — YAML Definition Vocabulary Loading

The engine now loads a strictly validated YAML definition vocabulary before
runtime entities are created. The document accepts only an ordered
`definitions` list containing definition keys, initial attributes, and system
names; it is explicitly not a serialized `WorldState` format.

The loader rejects duplicate YAML keys, invalid attribute shapes, unknown
schema fields, and definition-key collisions before the registry changes.
`SimulationEngine.load_definitions()` stages the validated tuple and commits it
through `DefinitionManager.register_many()`, preserving atomic registration.
Runtime instances continue to be created only by `EntityManager.create()`.

## Commit 0027 — Privileged HTTP World Inspection

The engine now has a deliberately narrow HTTP observability boundary for
privileged external operators. `create_app(engine)` serves GET-only snapshots
of authoritative state, including raw entity attributes and resource values,
without adding mutation, action, or simulation-step routes.

The inspection view returns detached JSON-safe values in deterministic record
identifier order. It remains explicitly separate from `NPCContextAssembler`
and every NPC-facing cognition boundary: authoritative data may be inspected
by an operator, but it does not become NPC knowledge.

## NPC Knowledge

`Knowledge` now records a distinct NPC-held claim with human-readable source
attribution. It is neither retained perception (`Memory`), learned experience
(`Experience`), nor an inference (`Belief`), and it is never authoritative
world truth. Observation, memory, and experience record identifiers remain
internal provenance rather than visible NPC text. This keeps later retrieval
and context assembly constrained to NPC-valid cognitive records.

## NPC Retrieval and Context Boundary

NPC context assembly is now an explicit boundary rather than a convenience
view over `WorldState`. The assembler uses an internal holder ID only while
looking up holder-scoped cognition, then returns a context without internal
entity identity or raw capability data.

The initial retrieval policy is deterministic: it selects up to ten core
memories, beliefs, and experiences by salience, tick, and record ID. Relevant
relationships and knowledge claims are query-only, so a general context does
not become an unrestricted dump of every cognitive record. All results are
small prose projections with no provenance, metadata, confidence, or raw
attributes.

`NPCInformationBoundary` validates the complete result before handoff. It
keeps engine objects, mappings, internal identifiers, and exact values copied
from entity attributes out of future LLM input while retaining ordinary
qualitative NPC language. Perception engines remain separate translators;
their mandatory description filtering is the next dedicated boundary task.
