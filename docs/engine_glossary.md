# Engine Glossary

## Definition

**Purpose**

Template describing what may exist.

**Owns**

- key
- initial_attributes
- participating systems

**Does Not Own**

- runtime state
- relationships
- history

---

## Entity

**Purpose**

Runtime instance created from a Definition.

**Owns**

- identity
- definition_key
- attributes
- lifecycle

**Does Not Own**

- relationships
- simulation logic
- history

Locations are entities whose definitions describe locations. They do not have a
separate runtime class or collection.

### NPC attribute conventions

An NPC is an ordinary entity carrying validated `npc_identity`, `occupation`,
and `schedule` attributes. `active_activity` is engine-owned runtime status,
not a memory, belief, observation, experience, or direct NPC cognition input.
`NPCIdentity` contains prose capability descriptions only; numerical skills
remain authoritative entity attributes and are not represented by identity.

## ScheduleSystem

**Purpose**

Derive an NPC entity's current activity from its validated schedule.

**Responsibilities**

- use inclusive `start_tick` and exclusive `end_tick` intervals
- update `active_activity` only through `EntityManager`
- record material changes as `npc_activity_changed` through `EventManager`

**Does Not Own**

- an NPC-specific entity type or state store
- perception, memory, belief, experience, or LLM context

---

## CognitiveConsolidationSystem

**Purpose**

Create NPC-scoped interpretations from the prior completed day only while the
engine-owned `active_activity` is `"sleeping"`.

**Responsibilities**

- use a fixed 24-tick day and exclude the current day
- create memories from visible observation descriptions
- derive repeated-observation experiences and candidate beliefs with internal
  observation provenance
- avoid duplicate records when the same persisted provenance is processed

**Does Not Own**

- world truth, entity mutation, or actions
- observation evidence, raw attributes, event internals, or LLM context

---

## Cognitive Records

**Purpose**

Represent holder-scoped NPC interpretations: `Memory`, `Experience`, `Belief`,
`NPCRelationship`, and `Knowledge`.

**Owns**

- NPC-visible prose
- salience and core policy
- internal provenance IDs

**Does Not Own**

- authoritative `Relationship` graph edges
- raw simulator values or inspection data
- validation of a belief as objective fact

`CognitiveSalience` is important at `importance >= 0.6`; an explicitly core
record requires `importance >= 0.8`.

## Knowledge

**Purpose**

Record a holder-scoped, source-attributed claim an NPC has heard or learned.

**Owns**

- NPC-readable statement and source description
- salience
- internal observation, memory, and experience provenance links

**Does Not Own**

- authoritative world truth
- raw simulation attributes, engine IDs in visible prose, or event internals
- belief confidence or inference

---

## Relationship

**Purpose**

Runtime connection between two Entities.

**Owns**

- source entity
- target entity
- relationship attributes

**Does Not Own**

- entity state
- simulation logic

### Organization and settlement graph conventions

- `member_of`: source member to target organization
- `owns`: source owner to target settlement
- `located_in`: source settlement to target location
- `road`: connects its two endpoint entities; direction has no road-network
  meaning and only `RelationshipManager` may create it
- `housed_in`: source resident to target dwelling
- `trade`: source resource holder to target recipient, with `resource` and
  `amount` attributes

These are domain conventions interpreted by systems, not relationship runtime
types or bespoke domain objects.

---

## WorldState

**Purpose**

Represents the current objective state of the simulation.
Runtime state should only be mutated through managers.

**Owns**

- entities
- relationships
- current tick
- holder-scoped memories and NPC relationship interpretations

**Does Not Own**

- simulation logic
- definitions

---

## WorldInspector

**Purpose**

Read-only privileged observability view over authoritative engine state.

**Responsibilities**

- return detached JSON-safe snapshots
- order collections by record identifier
- expose engine truth only to external operators

**Does Not Own**

- world mutation
- simulation stepping
- NPC-readable knowledge

---

## GraphRepository

**Purpose**

Persistence boundary for complete `WorldState` snapshots.

**Responsibilities**

- load a validated world snapshot
- atomically save a complete world snapshot
- keep storage-specific objects outside the runtime model

---

## SQLiteRepository

**Purpose**

SQLite implementation of `GraphRepository` using a versioned generic-record
snapshot.

---

## DefinitionManager

**Purpose**

Registry of available definitions.

`register_many()` validates an entire batch before changing the registry, which
allows `SimulationEngine.load_definitions(path)` to register YAML vocabulary
atomically.

---

## WorldDefinitionLoader

**Purpose**

Read validated definition vocabulary before runtime entities are created.

**Does Not Own**

- `WorldState`
- runtime entity identities
- ticks, events, or NPC cognitive records

`YAMLWorldDefinitionLoader` accepts only a top-level `definitions` list. Each
item has a `key`, optional `initial_attributes` mapping, and optional `systems`
list. Unknown schema fields and duplicate YAML keys are rejected.

---

## EntityManager

**Purpose**

Owns the lifecycle of runtime entities.

Responsible for creating, validating, registering and removing entities.

## RelationshipManager

**Purpose**

Owns the lifecycle of runtime relationships.

**Responsibilities**

- create relationships
- validate endpoints
- assign identifiers
- register relationships
- remove relationships

**Collaborates With**

- EntityManager
- WorldState

## Event

**Purpose**

Immutable record of something that happened in the world.

**Owns**

- identifier
- tick
- event kind
- subject reference
- recursively immutable event attributes

**Does Not Own**

- mutable state
- simulation logic

---

## EventManager

**Purpose**

Records immutable world history.

**Responsibilities**

- record events
- assign identifiers
- timestamp events
- retrieve recorded history

## SimulationScheduler

**Purpose**

Executes simulation systems in deterministic order.

**Responsibilities**

- register systems
- execute systems
- advance simulation ticks

---

## SimulationSystem

**Purpose**

Encapsulates one aspect of simulation behavior.

**Responsibilities**

- implement `step(state)` to update world state
- use managers for mutations

---

## WeatherSystem

**Purpose**

Cycle the `weather` attribute for definitions that opt into `weather` through
`Definition.systems`.

**Configuration**

- non-empty string `weather_cycle`
- optional integer `weather_index`

The system records `weather_changed` when the displayed weather changes.

---

## PopulationSystem

**Purpose**

Advance bounded integer population values for definitions that opt into
`population` through `Definition.systems`.

**Configuration**

- required integer `population`
- optional integer `population_change` (default `0`)
- optional integer `population_min` (default `0`)
- optional integer `population_max`

The system records `population_changed` only when the resulting population is
different.

---

## ProgressSystem

**Purpose**

Advance progress values over time.

The system understands progress as a generic concept rather than any
specific domain such as construction or farming.

Other systems interpret the meaning of progress.

---

## ResourceSystem

**Purpose**

Own generic resource quantities stored in an entity's `resources` attribute.

**Guarantees**

- quantities and operation amounts are non-negative integers
- failed removals and transfers do not make quantities negative
- transfer validates the source before mutating either endpoint

---

## ConstructionSystem

**Purpose**

Interpret completed generic progress as construction after consuming an
entity's `construction_requirements` through `ResourceSystem`.

---

## HousingSystem

**Purpose**

Interpret completed dwellings and summarize incoming `housed_in` relationships
into capacity-bounded `housing_allocated` state.

---

## ProductionSystem

**Purpose**

Interpret opt-in `production_inputs` and `production_outputs` recipes through
`ResourceSystem`.

---

## TradeSystem

**Purpose**

Transfer the configured resource of a `trade` relationship only between
endpoints connected by an existing `road` relationship.

## SimulationEngine

**Purpose**

High-level façade over the Living World runtime.

**Responsibilities**

- compose runtime components
- register simulation systems
- advance the simulation
- expose the public engine API
- load and save an optional repository snapshot

**Does Not Own**

- simulation behavior
- entity state
- relationship logic
- event history

Simulation behavior remains implemented by simulation systems.

---

## Executable Example

**Purpose**

Documents and smoke-tests the public runtime API.

Numbered top-level examples are discovered by `make examples`, run in lexical
order, and report PASS or FAIL. A failure stops the command.
