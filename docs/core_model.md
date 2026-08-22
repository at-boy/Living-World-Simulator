# Core Runtime Model

Work orders are immutable definitions paired with immutable lifecycle state and
durable aggregate reservation history. `WorkManager` alone mutates these
collections; reservations lock but do not deduct settlement resources.

Consumption, storage, and maintenance policies configure an authoritative
per-tick consequence phase. `ConsequenceManager` owns policy/state, resource,
condition, lifecycle, and event mutation. Consequences run after ordinary
systems and before needs and goals.

Settlement needs are authoritative `NeedDefinition` and `NeedState` records.
Their bounded assessment history describes availability, requirement, balance,
pressure, and qualitative level without choosing action.

The Living World Simulator is a property graph simulation engine.

Everything that exists is an Entity.

Everything that connects Entities is a Relationship.

Everything that changes the world is a System.

Everything that happens is an Event.

## Runtime Objects

- Entity
- Relationship
- Event
- Observation
- Memory
- Belief
- Experience
- NPCRelationship
- Knowledge
- System

These are the only concepts understood by the simulation engine.

## Runtime Registries

The simulation distinguishes between runtime objects and registries.

Registries define the vocabulary available to the simulation while runtime
objects represent the current world state.

Current registries include:

- DefinitionManager
- ResourceDefinitionManager

`RunMetadata` binds a persisted world to a versioned scenario key, seed, and
configuration fingerprint. `SimulationEngine.load_scenario(path)` reloads the
scenario's definition vocabulary, verifies compatibility on resume, and uses
entity and relationship managers to instantiate a fresh initial graph exactly
once. Scenario-local labels are configuration conveniences, not runtime IDs or
NPC-visible knowledge.

World-definition YAML is an input format for Definition vocabulary, not a
serialized `WorldState`. `SimulationEngine.load_definitions(path)` validates a
strict document containing only ordered definitions, their initial attributes,
and participating systems, then registers the complete set atomically. YAML
cannot introduce runtime entity identifiers, ticks, events, or NPC cognitive
records. Runtime entities remain exclusively owned by `EntityManager.create()`.

Additional registries may be introduced in the future as the simulation
grows.

## Design Principles

- The engine understands structure, not meaning.
- State belongs to the object that changes.
- Relationships are first-class objects with endpoints.
- Systems change the world.
- Events record history.
- Managers own lifecycle.
- Repositories own persistence.
- LLMs interpret truth but never own truth.

`DecisionEngine` may ask an NPC cognition client to propose from filtered
`NPCContext` and offered `ActionOption` values, but its `NPCDecision` has no
authoritative result. `NPCActionResolver` is called separately with an
engine-only actor ID, validates the offered vocabulary again, and dispatches
only an accepted proposal to a domain handler. Handlers own their manager
mutations and domain events; the generic gateway owns neither domain rules nor
generic history.

`LLMPerceptionEngine` is one such interpretation boundary. It submits only a
curated, provider-neutral perception request to a local model client, then
constructs the authoritative observation identity, tick and evidence itself.
Provider failure or invalid output falls back to deterministic perception.
`OllamaPerceptionClient` and `LlamaCppPerceptionClient` are loopback-only HTTP
adapters for that protocol; neither is allowed to use a cloud endpoint.

## Persistence

`GraphRepository` persists complete `WorldState` snapshots. The built-in
`SQLiteRepository` stores a versioned JSON representation in an atomic SQLite
transaction; its schema contains generic record collections only. Loading
constructs fresh domain records, so database rows and mutable SQLite objects
are never exposed to runtime callers.

`SimulationEngine(repository)` loads through the repository during composition.
Call `save_world()` to persist the current snapshot. Omitting a repository
retains the existing in-memory engine behavior.

SQLite schema version 2 adds optional run metadata. Schema-version-1 v0.5
snapshots remain loadable as unbound legacy worlds and are written as the
current schema on their next save.

## Privileged inspection

The HTTP inspection application exposes detached, deterministic snapshots for
operators. In addition to generic entities and history, it presents NPC
identity, occupation, and schedule attributes and every persisted cognitive
record collection. `/world/cognitive-history/{holder_id}` groups observations,
memories, knowledge, beliefs, experiences, and NPC-relationship interpretations
for one known holder. This privileged projection includes internal provenance
that must never be passed to NPC retrieval, context assembly, perception, or an
LLM.

See [HTTP inspection API](http_inspection_api.md) for startup instructions,
the complete route list, request examples, and deployment cautions.

Conversations, meetings, council calls and results, invitation feedback, and
action resolutions are ephemeral service return values rather than
`WorldState` records. The inspection API therefore does not advertise
persistence-like conversation or council endpoints.

## Entity Lifecycle

Runtime entities are created exclusively through `EntityManager.create()`.

The manager is responsible for:

- validating the referenced definition,
- generating a unique identifier,
- copying the definition's `initial_attributes`,
- applying caller-supplied attribute overrides,
- registering the entity in `WorldState`.

Production code should not instantiate runtime entities directly. Tests and migration tooling may do so when appropriate.

### Entity Resources

Entities may optionally contain a structured `resources` attribute.

The attribute maps resource identifiers to quantities owned by the
entity.

Example:

```python
{
    "resources": {
        "wood": 120,
        "water": 35,
    }
}
```

## Relationship Lifecycle

Runtime relationships are created exclusively through
`RelationshipManager.create()`.

The manager is responsible for:

- validating source and target entities,
- generating a unique identifier,
- creating the runtime relationship,
- registering the relationship in `WorldState`.

Together, `EntityManager` and `RelationshipManager` form the mutation
boundary of the simulation runtime.

Simulation systems should mutate the world only through managers or explicitly
provided system APIs. `EntityManager.set_attribute()` owns ordinary entity
attribute mutation; systems must not write to `WorldState` collections.

## World History

The simulation records immutable history through `Event` objects.

Events are created exclusively through `EventManager.record()`.

Unlike entities and relationships, events are append-only and are never
modified or removed. Event attribute trees are recursively immutable: mappings
are read-only, sequences are tuples, and sets are frozensets.

Observations are immutable records of an entity's perception of another
entity or the world. They are not events, although an event may result in
an observation. Observations are recorded through `ObservationManager`.
The observation description represents the perceiver's interpretation,
while internal evidence may retain objective simulator data for debugging
and provenance without exposing that data as the NPC-facing perception.
`NPCPerceptionBoundary` validates the description before an observation leaves
the perception engine and again when it is projected into `NPCContext`; the
latter path has no access to the observation's evidence or metadata.
`NPCInformationBoundary` additionally compares every context prose field with
authoritative placement numbers and spatial vocabulary, so an unsafe stored
observation or cognitive record cannot bypass perception-time validation.

`ConversationService` records a validated NPC utterance as an observation for
each other conversation participant, with empty evidence and metadata. It does
not create cognitive records or events directly; ordinary consolidation may
later make a visible observation memorable.

`MeetingService` is an ephemeral coordination wrapper around bounded dialogue.
It validates engine-side requester and invitee identifiers, preserves a
requester-first participant order, and may use an engine-owned call schedule.
Only a participant's own qualitative perspective enters that participant's
context; meetings create no persistent invitation, consent, relationship, or
governance state.

History represents objective facts about the world and recorded
perceptions of the world, forming the foundation for future systems such
as:

- NPC memory
- beliefs
- debugging
- simulation replay

A memory is a holder-scoped retained interpretation of a visible observation.
An experience is holder-scoped learning from repeated observations, while a
belief is a holder-scoped proposition that may be wrong. `NPCRelationship` is
likewise an NPC's interpretation, not a generic graph `Relationship`. These
records use `CognitiveSalience`: importance at or above `0.6` is important;
core is an explicit state requiring importance at or above `0.8`.

`Knowledge` is a separate, holder-scoped claim with NPC-readable source
attribution: it records what an NPC has heard or learned, not what the engine
asserts is true. Its statement and source description remain visible prose;
internal observation, memory, and experience identifiers are provenance links
only. Knowledge may be incomplete, stale, or false.

`CognitiveConsolidationSystem` runs after `ScheduleSystem`. It processes only
entities whose engine-owned `active_activity` is `"sleeping"`. A cognitive day
is 24 ticks: at tick 24 through 47 it considers only observations from ticks 0
through 23. It retains observation IDs solely as internal provenance, derives
all visible prose from `Observation.description`, and never reads evidence,
raw attributes, event internals, or world truth into cognition. Existing
provenance makes repeated consolidation idempotent.

## Simulation

Simulation behavior is implemented through `SimulationSystem`
implementations.

Systems execute in deterministic registration order through the
`SimulationScheduler`.

Each system is responsible for a single aspect of simulation behavior.

Some systems provide generic simulation mechanisms rather than
domain-specific behavior.

Current generic systems include:

- `ProgressSystem`, which advances bounded progress values over time.
- `ResourceSystem`, which provides generic operations for manipulating
  resource quantities stored by entities.
- `WeatherSystem`, which cycles the `weather` of definitions opting in with
  `systems: [weather]` using a non-empty `weather_cycle` sequence and optional
  integer `weather_index`.
- `PopulationSystem`, which applies integer `population_change` to integer
  `population` for definitions opting in with `systems: [population]`, then
  clamps it to optional `population_min` and `population_max` bounds.
- `OrganizationSystem`, which derives an opt-in organization's unique
  `member_count` from incoming `member_of` relationships.
- `SettlementSystem`, which derives an opt-in settlement's `is_located` and
  `owner_count` from one outgoing `located_in` relationship and incoming
  `owns` relationships.
- `ConstructionSystem`, which marks an opt-in entity constructed only after
  generic bounded progress has reached `progress_max` and its entity-held
  `construction_requirements` can be consumed through `ResourceSystem`.
- `HousingSystem`, which derives `housing_allocated` for completed opt-in
  dwellings from incoming `housed_in` relationships, bounded by
  `housing_capacity`.
- `ProductionSystem`, which applies an opt-in entity's
  `production_inputs` and `production_outputs` recipe through
  `ResourceSystem`.
- `TradeSystem`, which transfers the configured resource and amount of a
  `trade` relationship only when its endpoints have an existing `road`
  relationship and the source has sufficient quantity.
- `ScheduleSystem`, which derives a generic NPC entity's engine-owned
  `active_activity` from validated inclusive-start, exclusive-end schedule
  entries and records only material activity transitions.
- `CognitiveConsolidationSystem`, which creates holder-scoped memories,
  repeated-observation experiences, and candidate beliefs from completed-day
  visible observations while an NPC is sleeping.

Regions and terrain are ordinary entities. A `contains` relationship may link
a region to terrain it contains, while `adjacent` may link peer entities. These
relationship kinds are conventions, not engine primitives. Weather and
population events are recorded as `weather_changed` and `population_changed`
when their user-meaningful values change.

Organizations and settlements are likewise ordinary entities. The
`member_of` convention points from a member to an organization; `owns` points
from an owner to a settlement; and `located_in` points from a settlement to
its location. The organization and settlement systems ignore malformed or
ambiguous graph patterns. Material summary changes are recorded as
`organization_membership_changed`, `settlement_location_changed`, or
`settlement_ownership_changed` events.

Settlement-economy conventions remain graph and attribute vocabulary rather
than specialized runtime types. A `road` connects two entities in either
direction and is always created by `RelationshipManager`; it is never created
or edited by a simulation system. A `trade` relationship points from resource
source to recipient and supplies non-negative integer `amount` and non-empty
string `resource` attributes. `housed_in` points from a resident to a completed
dwelling. Construction, production, and trade use `ResourceSystem`, whose
quantities are non-negative integers and whose failed transfers leave both
endpoints unchanged. Material outcomes are recorded respectively as
`construction_completed`, `housing_allocation_changed`, `production_completed`,
and `trade_completed`.

The engine assigns no semantic meaning to these mechanisms. Higher-level
systems interpret them according to their own requirements.

For example, the `ProgressSystem` advances a generic `progress` value by
`progress_rate` every simulation tick. Optional inclusive
`progress_min` and `progress_max` attributes constrain progression.

The engine assigns no semantic meaning to progress values. Higher-level
systems interpret progress according to their own requirements.

Systems mutate the world exclusively through managers.

### NPC identity, schedule, and occupation attributes

An NPC remains a generic `Entity`; it has no NPC runtime subclass or separate
state registry. The validated `NPCIdentity`, `Occupation`, and `ScheduleEntry`
value objects are conversion boundaries for these JSON-compatible entity
attributes:

```python
{
    "npc_identity": {
        "name": "Mira",
        "description": "A dependable village woodcutter.",
        "capability_descriptions": ["Experienced woodcutter"],
    },
    "occupation": {
        "title": "Woodcutter",
        "description": "Harvests and prepares timber for the settlement.",
    },
    "schedule": [
        {"start_tick": 0, "end_tick": 8, "activity": "resting"},
    ],
    "active_activity": "resting",
}
```

`ScheduleSystem` owns the runtime `active_activity` status and changes it only
through `EntityManager`, recording `npc_activity_changed` through
`EventManager`. Identity and occupation are presentation/domain data; their
prose capability descriptions are not numeric engine skills. These attributes
are not cognition inputs and do not grant an NPC direct access to world state.

## NPC Retrieval and Context

`NPCContextAssembler` is the only current composition point for NPC-facing
context. It receives an internal holder ID only to look up the entity and
returns display-name identity, prose self-knowledge, holder-scoped observation
descriptions, core cognitive projections, and optional query retrieval. The
returned `NPCContext` has no holder or entity ID and no raw capability or
attribute mapping.

`DeterministicCognitiveRetriever` is read-only. Its default policy returns up
to ten core memories, beliefs, and experiences ordered by descending salience
importance, descending tick, then ascending record ID. Relationships and
knowledge claims require a non-empty topic match. `RetrievedCognition` exposes
only kind, visible prose, importance, and core status; internal identifiers,
provenance, metadata, confidence, and raw attributes remain engine-only.

`NPCInformationBoundary` validates every completed context before it is
returned. It rejects mappings, engine objects, known internal IDs, and numeric
values copied from authoritative entity attributes, while allowing ordinary
qualitative prose. Observation descriptions remain perception output; Task
09a owns mandatory perception-description filtering.

The scheduler is responsible only for calling `step(state)` in registration
order and advancing the simulation tick.

## Simulation Engine

`SimulationEngine` is the primary entry point for applications using the
Living World engine.

## Privileged World Inspection

The HTTP inspection API exposes detached, JSON-safe snapshots of authoritative
engine state for privileged external operators. `create_app(engine)` provides
GET-only `/world` inspection routes for the current tick, entities,
definitions, resources, relationships, events, observations, beliefs, and
experiences. Collection snapshots are ordered by record identifier.

Inspection is observability, not an action or simulation interface: it has no
mutation or stepping endpoints. Its raw values are deliberately outside the
NPC information boundary and must never be supplied to NPC context assembly,
cognitive retrieval, or cognition clients.

The engine composes the runtime by constructing:

- WorldState
- DefinitionManager
- EntityManager
- RelationshipManager
- EventManager
- ObservationManager
- MemoryManager
- BeliefManager
- ExperienceManager
- NPCRelationshipManager
- SimulationScheduler

The engine exposes a simplified API for running simulations while
preserving the existing responsibilities of managers and systems.

Simulation behavior remains implemented by simulation systems rather than
the engine itself.

## Executable Documentation

Examples are executable documentation for the public runtime API. `make
examples` discovers numbered top-level files in `examples/`, executes them in
lexical order, reports the outcome for each file, and stops at the first
failure.

Locations are represented by ordinary `Entity` instances whose definitions
describe a location; there is no location-specific runtime type or registry.

## Spatial placement contract

Spatial state is a dedicated authoritative collection keyed by entity ID, not
an entity-attribute convention. A frozen placement contains an immutable
integer `Point`, an immutable positive axis-aligned `Bounds`, or the explicit
unplaced state. Bounded placements distinguish areas from structures and carry
a typed sibling-overlap policy. An optional container must be a live entity
with bounds, and child geometry must lie fully inside it.

The implemented spatial manager alone creates, atomically replaces, unplaces,
and removes placements. It validates entities, containment, cycles, and mutual
overlap permission before recording one immutable event. Queries use canonical
container/geometry/entity ordering. SQLite migration treats legacy entities as
spatially unknown, and privileged inspection returns detached exact geometry.
`SpatialPerceptionEngine` resolves only one caller-selected live observer and
subject. It translates containment, doubled point/bounds centers, and an
explicitly supplied active direct road into deterministic qualitative prose.
Positive x is east and positive y is north. The returned observation is not
recorded automatically; callers use `ObservationManager`, after which normal
holder-scoped context assembly applies. Exact geometry, magnitude, IDs, and
privileged spatial vocabulary remain outside NPC context. See ADR-0016.

## External-world references

Off-map anchors are dedicated frozen records owned by their lifecycle manager,
not generic entities or secretly simulated places. They hold exact engine
trade/contact policy and persist in SQLite schema 4. Operator inspection may
show the full detached record; NPC-facing use is a separate qualitative DTO
and is not automatically added to context. See ADR-0017.

External dispatches are frozen durable records owned by a dedicated manager.
They reserve local resources atomically and advance through a deterministic
seeded scheduler system. Exact policy remains privileged; the separate safe
perception is qualitative and holder-neutral until a later perception path
establishes NPC knowledge. See ADR-0018.

# Councils

A council is an ephemeral agenda-driven composition of meeting coordination.
Eligible members may attend or decline; only a strict attendee-majority proposal
is offered to the normal simulation action gateway. As a temporary v0.5 policy,
if every non-empty set of invitees explicitly declines and delegates, the caller
may submit one offered agenda proposal through that same gateway. Unavailable
and no-selection replies never delegate. Each result may also carry
an ephemeral, operator-visible invitation-feedback trace in invitee order. It
records only the resolver outcome and filtered submitted statement/rationale;
it is not supplied to another NPC, retrieval, context assembly, cognition,
governance, an event, memory, or world state.

For automatic discussion, the engine may supply a non-negative turn-order
offset. Confirmed attendees are rotated by that offset and then scheduled in a
bounded deterministic round robin. An explicit speaker-call schedule takes
precedence. The offset is ephemeral engine coordination: it is not NPC input,
cognitive state, authority, or model output.

Manual council scenarios prepare organizations, participants, and membership
through `SimulationEngine` managers and retain manager-generated IDs only for
engine calls. The cognition-shaped demonstration records holder-scoped
observations, memories, experiences, beliefs, and social interpretations
through their managers. Every NPC still receives only its filtered
`NPCContext`; beliefs do not mutate world truth or select a proposal.
# Engine-owned goals

`WorldState` stores immutable goal and objective definitions separately from
their immutable lifecycle state and progress evidence. `GoalManager` alone
creates graphs and replaces state records. Criteria use six closed typed
variants. A final deterministic simulation system evaluates them after the
other systems at each tick. Typed evaluators return satisfied, unsatisfied, or
unavailable results with detached evidence. Unavailable authoritative domains
block progress; they are never inferred from arbitrary entity attributes.

Dependencies are prerequisites and alternative objectives may satisfy their
parent. Completion requires every completion criterion, while any satisfied
failure criterion fails the record. The goal manager remains the sole mutation
boundary and records exactly one immutable event for each actual lifecycle
transition. Re-evaluation without a status change adds no lifecycle event.
Materially changed evaluation snapshots may add manager-owned progress evidence
without changing status or emitting an event. The manager compares normalized
description and source-event provenance, so an unchanged snapshot on later
ticks is idempotent.

An NPC receives only `NPCGoalInterpretation(label, description)`. Definition
IDs, owner IDs, criteria, evidence, deadlines, action policy, and authoritative
status remain engine/inspection data. Both visible fields reject internal ID
forms; operator-only purpose text remains unrestricted and privileged.
