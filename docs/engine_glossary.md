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
