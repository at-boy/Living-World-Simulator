# Living World Simulator – Project Journal

## Task 20a implementation

Engine-authored work offers now give one eligible NPC a narrow qualitative
choice while retaining all category, target, requirement, priority, and labor
policy inside the simulation. Construction, validation, and application each
recheck active settlement-goal authority and current manager preflights. The
gateway creates no proposal event or durable offer state; Task 20b still owns
automatic selection, charging, progress, and effects.

## Task 20 implementation

Work intent and non-deducting aggregate locks are now manager-owned durable
truth. Proposal translation and deterministic effects remain Tasks 20a/20b.

## Task 19a implementation

Added the manager-owned atomic consequence phase, schema-8 persistence,
privileged inspection, qualitative NPC projection, tests, and example 033.

## Task 19 handoff checkpoint

Recorded the clean, pushed Task 19 milestone merge, schema-v7 and 655-test
baseline, and Task 19a as the next authorized dependency. The Task 19a draft is
intentionally flagged for contract reconciliation before delegation so a fresh
orchestrator does not infer arithmetic, persistence, event, or NPC-boundary
semantics from a high-level outline.

## Task 19 — settlement needs

Introduced authoritative settlement need pressure after ordinary systems and
before goals. NPC projection remains qualitative, while all action authority
continues through the existing gateway.

This document records the evolution of the project.

Unlike the CHANGELOG, this journal focuses on architectural decisions,
engineering milestones and lessons learned.

---

# 2026-08-19

## NPC-safe spatial perception

Task 15d completes the v0.6 local-space information path without weakening the
engine boundary. `SpatialPerceptionEngine` reads only a caller-selected live
observer, subject, placements, and optional direct road, then returns stable
containment and compass prose as an unpersisted observation. Callers still own
recording, and holder-scoped context assembly still controls which NPC can see
the result.

Exact coordinates remain privileged inspection data. Both perception-time and
final context validation reject geometry values, IDs, coordinate notation, and
privileged spatial vocabulary, including unsafe observations inserted through
older or manual recording paths. Direct-road prose reports an already-known
connection; it does not add visibility, distance, travel, or pathfinding.

# 2026-08-18

## Deterministic External Dispatch

Task 17a builds a durable exchange lifecycle on partial external references.
Manager-owned reservations and immutable events make failure atomic; a
SHA-256-derived seed decision makes arrival/loss stable across replay and
resume. NPC proposals choose only an offered qualitative label and cannot set
IDs, quantities, timing, reliability, outcomes, or resources.

## Partial External-World References

Task 17 adds deliberately partial off-map references as frozen, manager-owned
engine records. Exact capacity, delay, cost, reliability, goods policy, IDs,
and privileged inspection remain outside NPC context; the only reusable
NPC-facing form is fixed qualitative name/role/contact prose. Schema 4 preserves
these anchors while legacy snapshots default them to empty. Dispatch, remote
simulation, and trade transfer remain deferred to their documented tasks.

## Spatial Domain, Persistence, and Inspection

Task 15b implements ADR-0016 as dedicated spatial state rather than coordinate
attributes. `SpatialManager` validates live entities, explicit containment,
descendant-safe replacement, mutual overlap permission, and leaf-first removal
before committing a frozen placement plus one immutable lifecycle event. A
narrow entity-removal guard prevents stale placement references without giving
`EntityManager` authority over spatial mutation.

SQLite schema version 3 persists placed and explicitly unplaced records while
loading older worlds as spatially unknown. Exact geometry is available only as
detached, canonically ordered privileged inspection. NPC context remains
unchanged and receives no coordinates or inspection payload.

## Canonical Two-Dimensional Spatial Contract

ADR-0016 establishes one deliberately abstract local integer plane before any
spatial runtime or inspector is implemented. Points and positive half-open
bounds are authoritative placement values; explicit containment and mutual
typed overlap permission replace coordinate-like entity attributes or hidden
automatic packing. Canonical ordering and legacy-unplaced migration make the
future Task 15b implementation deterministic.

Exact geometry remains operator-only engine truth. NPC-facing spatial meaning
must later be perceived as qualitative, holder-scoped relative prose rather
than copied from inspection DTOs or raw coordinates.

## Bounded Runner, Checkpointing, and Resume

The v0.6 operator path now runs a scenario through a typed service behind the
`living-world run` command. Bounded execution remains the safe default;
continuous execution is explicit and cooperatively stoppable. Successful ticks
checkpoint complete snapshots at a configured cadence and at every clean exit,
while a failed tick never replaces the last valid snapshot. Resume reuses the
Task 16 identity and definition checks before advancing.

The command prints only stable run identity/status/tick/stop fields and maps
configuration, compatibility, persistence, and simulation failures to distinct
exit codes. It does not expose raw state or connect operator configuration to
NPC context.

## Scenario and Deterministic Run Contract

The first v0.6 capability separates reproducible scenario configuration from
authoritative runtime state. A strict YAML document names definitions and an
initial graph with public local labels; managers still generate every runtime
identity. Persisted run metadata binds the world to the scenario key, seed, and
full configuration fingerprint, so resume reloads the same definitions and
fails before stepping if configuration changed. Legacy v0.5 snapshots remain
loadable but are not silently assigned a scenario history they never had.

Run metadata is exposed only through privileged inspection. It has no route to
perception, retrieval, `NPCContext`, cognition, or action resolution.

---

# 2026-08-12

## v0.5 Release Closeout

The v0.5 capability audit traced every AI-layer backlog claim to production
interfaces, tests, and examples. It confirmed loopback-only local LLM clients,
filtered NPC context, proposal-only cognition, the action gateway, bounded
conversations and meetings, council coordination, and three distinct manual
council scenarios. A targeted boundary review found no route from privileged
inspection or raw world state into NPC cognition.

The first closeout pass correctly stopped on inconsistent hard-coded release
versions. Task 14b then unified the runtime and HTTP version and added a
four-surface regression test before closeout resumed. Completed v0.4 and v0.5
items have now left the active backlog, satisfied technical-debt entries have
been removed, and deferred retrieval, governance, settlement evolution, and UI
work remain explicitly future scope.

## Release Version Consistency

The v0.5 release correction makes `living_world.__version__` the single runtime
version export consumed by the HTTP health endpoint. Release metadata remains
explicit in `VERSION` and `pyproject.toml`; a regression test now proves those
two files, the runtime export, and `/health` all agree on `0.5.0`. This removes
the version-consistency blocker without performing the remaining release
closeout or changing simulation behavior.

# 2026-08-11

## Manual Council Scenario and Safe Request Trace

The Ollama and llama.cpp council demonstrations now use opaque engine IDs and
offer five differentiated NPCs three qualitative approaches to a risky
journey. A longer bounded discussion begins at a nonzero deterministic turn
offset. Its manual-only action handler demonstrates an accepted proposal
through the ordinary gateway while deliberately performing no state mutation;
it is not a production world primitive.

An opt-in recording decorator captures only the already-filtered `NPCContext`
and offered `ActionOption` tuple before each provider call. The manual
`--show-context` output passes those values through the production serializer.
Provider responses, exceptions, transports, world state, internal IDs, hidden
records, and secrets are neither retained nor rendered. This gives operators a
useful boundary trace without widening what reaches the model or what survives
afterward.

# 2026-08-10

## Local Cognition Response Shape Guidance

The shared local cognition instruction now gives models an exact bare-JSON
checklist and generic response templates. It requires both response fields and
all four fields of an object-valued action request, including explicit `null`
and empty-object cases. This is guidance only: the existing strict parser still
rejects malformed, incomplete, Markdown-wrapped, and unoffered proposals
without inferring a missing choice.

## Council Explicit-Decline Fallback

The temporary v0.5 council policy permits the caller to make one ordinary
agenda proposal only after every invitee explicitly selects `decline_council`.
The caller sees a safe aggregate fact, never invitation identities, reasons,
IDs, scores, or raw replies. That proposal has no authority until the existing
action gateway accepts it. Unavailable, malformed, no-selection, mixed, and
caller-only calls do not delegate; future organization-specific governance must
replace this narrow policy.

## Council Invitation Action Selection

Council invitations now state the two available attendance actions and direct
an invitee to return exactly one through `action_request`, with a short
NPC-visible reason in its `rationale`. The safe NPC-facing prose names the
caller, agenda topic, and structured response fields, while the action keys
remain in the separately supplied structured vocabulary. This preserves the
internal-identifier boundary. The reason stays only as filtered, transient
operator-debug invitation feedback: it is not state, persistence, an event, or
another NPC's context. This does not change the action gateway: a statement
without an action request remains a non-attending `no_selection` result, and
local model compliance remains probabilistic.

## NPC Meeting Coordination

NPC meeting coordination is deliberately an ephemeral wrapper around the
existing conversation boundary. An engine-side requester may invite known NPCs
and provide a bounded internal call schedule, while each speaker receives only
its own qualitative perspective through holder-scoped context. The service
creates no meeting record, invitation delivery or acceptance, consent,
availability, relationship, event, vote, or policy result. This keeps the
future council and governance designs separate from visible dialogue.

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

## Persisted NPC and Cognitive Inspection Coverage

The privileged inspection contract now includes NPC presentation and all
persisted cognitive collections. Operators can inspect memories, knowledge,
belief and experience history/provenance, observations, and holder-scoped
NPC-relationship interpretations in deterministic ID order. A known holder
with no records receives stable empty categories; an unknown holder remains a
404. Every payload is recursively detached from `WorldState`.

This expansion does not alter the NPC information flow. Inspection responses
are not consumed by retrieval, context assembly, perception, or model clients.
Conversation, meeting, council, invitation-feedback, and action-resolution
values remain ephemeral and deliberately have no inspection endpoint.

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

## Local NPC Cognition Clients

Local Ollama and llama.cpp adapters can now receive a completed `NPCContext`
and a caller-provided action vocabulary. Their JSON prompt contains only the
NPC-readable projections produced by the existing context boundary; no engine
state, raw attributes, evidence, metadata, provenance, internal identifiers,
or numerical capabilities crosses into the model request.

Provider output is an untrusted `NPCDecision`: optional spoken text and an
optional action request. Parsing is strict and permits only offered action keys
and target labels. This is deliberately vocabulary validation, not action
validation or execution. The forthcoming action gateway remains the only owner
of simulation authority.

## NPC Cognition Protocol and Action Gateway

NPC cognition now ends in a proposal boundary. `DecisionEngine` receives only
an already filtered `NPCContext` and offered `ActionOption` vocabulary, then
rejects even directly constructed client decisions that use an unoffered action
or target. It neither receives an actor ID nor applies a result.

`NPCActionResolver` is separately called by the engine with the internal actor
ID. It repeats vocabulary validation and requires a domain handler to accept a
non-mutating validation step before application. The generic gateway has no
default domain behavior and records no generic event; a successful domain
handler owns its manager mutation and one domain event. This preserves the
rule that LLMs reason and propose while simulation validates and applies.

## NPC Conversations

Bounded NPC conversations now use a fresh, holder-scoped context for every
turn. The model receives only a validated topic preamble and earlier visible
utterance prose; it never receives participant identifiers, transcript records,
observation evidence, metadata, private cognition from other participants, raw
state, or action resolutions.

An utterance becomes a recipient observation with empty evidence and metadata,
not an immediate fact or cognitive record. Normal consolidation may later turn
that visible perception into memory. Any proposed action remains an untrusted
proposal sent through the existing engine-owned action gateway, so conversations
add no default domain action, event, relationship, belief, experience, or
council policy.
# Council coordination

Council discussion now composes meeting coordination and the ordinary action
gateway. It is not an authoritative governance system.

The optional local-model council examples label the guaranteed caller apart
from invitees. A caller-only result means no invited NPC joined, without
claiming a reason that the safe result does not provide. Equivalent constrained
requests may produce identical outcomes on successive runs because the
examples use provider/model sampling defaults and do not promise variation.

Council results also expose a transient invitation-feedback trace in invitee
order. It distinguishes accepted attendance, accepted decline, no selection,
and unavailable output while showing only prose that passes the NPC conversation
boundary. Existing council validation makes a resolver-rejected invitation
unreachable, so the trace does not invent a new rejection rule. It creates no
governance, cognition, event, or persistence record.

Unavailable invitation feedback now adds exactly one fixed operator-safe
diagnostic: provider unavailable, invalid structured response, or invalid
decision. The category contains neither provider data nor internal engine data,
and it does not retry, infer attendance, or remedy a non-compliant model.

Automatic council discussion can now rotate its confirmed-attendee round robin
by a non-negative engine-owned offset. Zero retains caller-first order, larger
values wrap by attendee count, and the resulting schedule remains bounded by
the council's round limit. Explicit engine calls still take precedence. The
offset is ephemeral scheduling input, never NPC context, cognitive state,
authority, or model-selected output; policy for deriving it from deterministic
simulation state remains deferred.

Shared local-cognition guidance now treats a topic or agenda without labelled
prior dialogue as context rather than an utterance to acknowledge. It asks an
NPC to begin with a direct position, then limits any reply to labelled visible
turns once they exist. This changes no context assembly, response schema,
parser acceptance, proposal authority, or generated model text after the fact.

The Ollama and llama.cpp council entry points now share an immutable,
manual-example-only scenario catalog and deterministic `--scenario` names. The
existing journey remains the default. The settlement scenario frames a visible
public-well failure as a shared condition requiring a decision, while explicitly
describing the engine-appointed caller as only the meeting coordinator rather
than the issue's author, a representative of unanimous action support, or a
special authority. Its three alternatives remain untrusted proposals routed to
the accepted no-mutation demonstration gateway. Collective agenda discovery,
institutional governance, persistence, and world mutation remain deferred.

The same manual catalog now includes an `opposing-interests` scenario. Five
independently eligible town-council members receive qualitative self-knowledge
about riverside trade, hillside growing, or cross-cutting and independent
concerns, then consider immediate road repair, harvest priority, or divided
work crews. Affiliation is context rather than engine authority: it supplies no
faction object, attendance rule, voting weight, delegate, predetermined model
choice, reputation effect, or durable political consequence. Any selected
alternative remains an untrusted proposal routed through the existing accepted
no-mutation demonstration gateway.

The manual catalog now also includes `cognition-shaped`. Both provider entry
points use one typed runtime-preparation function for every scenario, replacing
direct world-collection setup with definition, entity, and relationship
managers and manager-generated IDs. Five distinct holder histories contain
current observations plus a memory, experiences, conflicting beliefs, and a
private NPC-relationship interpretation. Safe request serialization contains
only each holder's prose projection; IDs, lineage, evidence, metadata, raw
state, and other holders' cognition remain engine-only. These histories do not
prescribe attendance, speech, a proposal, a majority, or a gateway outcome.
## Task 18 — engine-owned goals and objective graphs

Added frozen personal/collective goal graphs and separate manager-owned state,
with atomic validation and lifecycle events, schema-v6 persistence, detached
inspection, and a deliberately narrow prose-only NPC interpretation. Criterion
evaluation and work execution remain separate follow-up tasks.

## Task 18a — deterministic objective evaluation

Added a final engine system with a closed typed criterion-evaluator registry.
It evaluates objective graphs in deterministic dependency/alternative order,
uses manager-owned lifecycle transitions, and records normalized detached
evidence when status changes or authoritative progress materially changes.
Progress-only evidence emits no lifecycle event, and identical snapshots are
deduplicated across ticks. Resource, construction, capacity, and
external-contact criteria read their defined authoritative sources. Sustained
need and settlement stage remain explicitly unavailable until their planned
domains land. Exact evidence and authority remain engine-only; NPC goal
interpretations are unchanged.
