# Changelog

## Unreleased

### Added

- Deterministic consumption, storage loss, and maintenance consequences with schema-8 persistence, privileged inspection, and qualitative NPC-safe interpretations.

- Add authoritative settlement food, water, shelter, and storage pressure with
  bounded history, sustained goal evaluation, schema-7 persistence, privileged
  inspection, and qualitative NPC-safe interpretations.

- Add deterministic NPC-safe spatial perception for explicitly selected
  entities, containment, compass direction, co-location, and caller-filtered
  direct roads, with coordinate-leak rejection at perception and context
  boundaries.

- Add deterministic engine-owned goal/objective criterion evaluation with
  typed evaluators, stable graph ordering, normalized evidence, and immutable
  lifecycle events. Material progress changes append manager-owned evidence
  without fabricating lifecycle events.

- Add immutable engine-owned goal/objective graphs, manager-owned lifecycle
  state, schema-v6 persistence, privileged inspection, and explicit prose-only
  NPC interpretations. Automatic evaluation remains deferred to Task 18a.

- Add durable deterministic external dispatches with resource reservation,
  immutable lifecycle events, offered-label gateway handling, schema-v5
  persistence, privileged inspection, and qualitative safe results.

- Add deliberately partial external-world references with manager-owned contact
  lifecycle, immutable events, schema-v4 persistence, privileged inspection,
  and a separate qualitative NPC-safe interpretation.

- Implement frozen spatial point/bounds placement records, manager-owned
  lifecycle and events, guarded entity removal, schema-v3 persistence,
  canonical queries, and detached privileged HTTP inspection.
- Define ADR-0016's canonical local integer-coordinate point/bounds placement
  contract, containment and overlap rules, deterministic ordering, persistence
  migration, privileged inspection, and NPC information boundary.
- Add the supported `living-world run` headless command and typed runner for
  bounded or explicit continuous execution, atomic checkpointing, compatible
  resume, graceful SIGINT, stable summaries, and classified failure exits.
- Add a strict versioned YAML scenario contract with deterministic initial
  graph creation, persisted run identity/fingerprint, compatible definition
  reload on resume, and privileged read-only run inspection.
- Add SQLite schema-version-2 snapshots while retaining schema-version-1 v0.5
  loading as unbound legacy worlds.

### Changed

- Refresh the architect/orchestrator handoff at the reviewed Task 19 milestone
  merge and identify Task 19a contract reconciliation as the next action.

- Evaluate goals after existing systems and before the simulation tick
  advances, including direct blocked-to-completed transitions when fresh
  authoritative state proves completion.

## v0.5.0 - 2026-08-12

### Added

- Synchronize release metadata, the public runtime version, and the HTTP health
  response at `0.5.0`, with one runtime version export and a consistency test.
- Extend the privileged GET-only inspection API across persisted NPC
  presentation and cognitive records, including deterministic holder-scoped
  history and summary counts, without persisting ephemeral coordination results.
- Add a cognition-shaped manual council scenario whose shared manager-owned
  runtime seeds isolated observations, memories, experiences, beliefs, and
  social interpretations without forcing a proposal or exposing provenance.
- Add an opt-in opposing-interests council scenario with five independently
  eligible members, safe cross-cutting affiliations, and three unforced choices.
- Add a shared immutable manual council-scenario catalog and deterministic
  `--scenario settlement` demonstration that separates a settlement-wide issue
  from the engine-appointed caller's procedural coordinator role.
- Expand both opt-in local council examples into longer five-NPC scenarios with
  three agenda choices, deterministic turn rotation, opaque engine IDs, an
  accepted no-mutation gateway demonstration, and an opt-in safe request trace.
- Add a request-only cognition-client decorator that records filtered
  `NPCContext` and offered actions without retaining provider responses/errors.
- Guide local NPC cognition to open directly when given only a topic or agenda,
  while limiting replies to labelled visible dialogue once prior turns exist.
- Strengthen local NPC cognition response-shape guidance with a bare-JSON
  checklist and schema-compliant templates while retaining strict validation.
- Add an engine-owned offset for deterministic rotation of automatic council
  turns while preserving explicit speaker-call schedules.
- Add bounded, agenda-driven NPC council coordination with membership checks,
  attendance delegation, and action-gateway majority proposals.
- Clarify manual Ollama and llama.cpp council output by marking the caller,
  distinguishing absent invitees, and documenting valid repeatable outcomes.
- Add filtered, ephemeral council invitation feedback for each invitee's
  attendance proposal without exposing provider errors or creating world state.
- Distinguish unavailable council invitation replies with fixed safe diagnostics
  for provider availability, invalid structured responses, and invalid decisions.
- Direct council invitees to submit exactly one offered attendance action, while
  retaining no-selection handling for statement-only local-model responses and
  filtering selected-action rationales into transient operator feedback only.
- Permit one caller agenda proposal through the ordinary action gateway only
  after every invited NPC explicitly declines and delegates; unavailable and
  no-selection replies never grant that fallback.

- Ephemeral `MeetingService` coordination for requester-initiated, bounded NPC
  dialogue with engine-owned speaker calls and holder-scoped qualitative
  perspectives. Meetings retain the existing conversation and action-gateway
  boundaries without creating invitation, consent, relationship, event, or
  governance state.
- `MeetingRequest`, engine delegation, ADR-0012, and an executable NPC meeting
  example.

- Bounded `ConversationService` NPC dialogue with per-turn holder-scoped
  context, boundary-validated history, and recipient-only visible observations.
- `ConversationResult` and `ConversationTurn` value objects, engine delegation,
  ADR-0011, and an executable NPC-conversations example.

- `DecisionEngine` and `NPCActionResolver` establish the NPC proposal-to-
  application authority gateway. They revalidate offered action vocabulary,
  keep actor IDs engine-only, and require a domain handler to validate before
  manager-owned application and domain-event recording.

- Loopback-only Ollama and llama.cpp NPC cognition clients that return strictly
  validated, untrusted speech and action proposals from filtered `NPCContext`.
- Structured cognition request/response validation that restricts model action
  keys and target labels to vocabulary offered by the engine, without granting
  model-side action authority.

- Mandatory `NPCPerceptionBoundary` validation for deterministic and local-LLM
  perception outputs, including nested protected-value, internal-ID, raw
  attribute, hidden-state, metadata, and engine-object protections.
- NPC context assembly now projects current perceptions solely through that
  boundary and never reads observation evidence or metadata.

- Deterministic holder-scoped cognitive retrieval and an NPC context assembly
  contract with no holder IDs or raw capability mappings.
- Mandatory NPC information-boundary validation for returned context,
  including internal-ID and authoritative-number protection.

- Immutable holder-scoped `Knowledge` claims with NPC-readable source
  attribution and internal provenance links.
- SQLite persistence, legacy-load compatibility, engine composition, and an
  executable NPC knowledge example.

- Immutable holder-scoped `Memory` and `NPCRelationship` cognitive records,
  with salience and internal observation provenance.
- Sleep-only, deterministic 24-tick cognitive consolidation that derives
  memories, repeated-observation experiences, and candidate beliefs from
  NPC-visible observation descriptions.
- SQLite persistence and round-trip support for cognitive records, salience,
  and consolidation provenance.
- Executable NPC cognition example.

- Validated `NPCIdentity`, `Occupation`, and `ScheduleEntry` value objects
  with JSON-compatible generic entity-attribute forms.
- Deterministic `ScheduleSystem` activity transitions with immutable
  `npc_activity_changed` history and an executable NPC schedule example.
- v0.3 settlement systems for construction, capacity-bounded housing,
  recipe-based production, road-gated trade, and non-negative resource
  operations.
- Executable YAML-backed settlement economy example.

- Property-graph organization and settlement foundations using `member_of`,
  `owns`, and `located_in` relationship conventions.
- Deterministic organization membership and settlement location/ownership
  summary systems with immutable material-change events.
- Executable organization and settlement foundations example.
- Deterministic `WeatherSystem` and `PopulationSystem` implementations for
  definition-opt-in entities, including bounded population updates and
  immutable material-change events.
- Executable region and terrain world-simulation example.

- GET-only privileged HTTP world-inspection API with detached, deterministically
  ordered snapshots of authoritative runtime and registry state.
- `create_app(engine)` for inspected engine composition and a world-inspection
  executable example.

- Strict, duplicate-key-safe YAML definition vocabulary loading through
  `SimulationEngine.load_definitions()`.
- Atomic batch definition registration and an executable YAML world-definition
  example.
- `GraphRepository` persistence boundary and versioned `SQLiteRepository`.
- SQLite round-trip support for entities, relationships, events, observations,
  beliefs, experiences, and immutable history.
- Optional repository composition and explicit `SimulationEngine.save_world()`.
- Provider-neutral `LLMPerceptionEngine` and `LLMPerceptionClient` boundary.
- Deterministic fallback for unavailable, invalid or unsafe local LLM output.
- Executable LLM perception example using a fake local client.
- Local Ollama and llama.cpp setup documentation.
- Loopback-only `OllamaPerceptionClient` and `LlamaCppPerceptionClient` HTTP
  adapters.
- Manual real-server examples using Qwen3-4B Q4_K_M.

### Changed

- `ResourceSystem` now rejects negative quantities and guarantees failed
  transfers leave both resource holders unchanged.

- Event attribute trees are now recursively immutable and detached from caller
  input, including after SQLite persistence round trips.
- LLM perception results are validated before becoming NPC-readable
  observations; model output cannot set simulation identity, tick or evidence.
- Local provider calls use structured JSON responses and no cloud endpoint or
  API key configuration.
- `make examples` now discovers numbered top-level examples automatically,
  reports PASS or FAIL for each, and stops on the first failure.

## v0.2.2 (Unreleased)

### Added

- Explicit NPC information-boundary guardrails to keep engine truth separate from NPC-visible cognition.
- Documentation clarifying that perception is a translation layer and that LLM reasoning remains downstream of NPC-accessible knowledge.
- Backlog and journal tracking for future NPC retrieval, context assembly, and boundary enforcement work.

### Changed

- The cognitive architecture now explicitly treats raw world state as authoritative simulation data rather than NPC knowledge.
- The project roadmap reflects the need to preserve the NPC information boundary while implementing future cognition features.

## v0.2.2 (Unreleased)

### Added

- Immutable `Experience` runtime objects representing lived interaction and accumulated learning.
- `ExperienceHistoryEntry` for append-only experience change tracking.
- `ExperienceManager` for recording and retrieving NPC experiences.
- `Experience` support in `WorldState` and `SimulationEngine`.
- `generate_from_observations()` and `consolidate_repeated_observations()` helpers for creating experiences from repeated observation patterns.
- Example demonstrating experience generation from repeated observations.

### Changed

- Beliefs can now reference supporting experiences without losing their distinct identity.
- The cognitive architecture now explicitly distinguishes observation, memory, belief, and experience.

## v0.2.2 (Unreleased)

### Added

- Immutable `Observation` runtime objects.
- `ObservationManager` for observation lifecycle and recording.
- Observation storage to `WorldState`.
- `PerceptionContext` for supplying observer, subject, capabilities, relationships, world state, and tick to perception engines.
- The `PerceptionEngine` protocol.
- `DeterministicPerceptionEngine` as the first concrete perception implementation.
- Capability-dependent perception so the same world state can produce different observations for different observers.
- Internal evidence to observations so objective world data used during perception can be retained for debugging and future systems without being exposed directly in the NPC-facing description.
- Observation runtime integration through `SimulationEngine`.
- `examples/008_observations.py`.
- Comprehensive tests for observation recording and deterministic perception.


## v0.2.2 (Unreleased)

### Added

- Generic `ResourceSystem` for manipulating entity resource quantities.
- Resource operations:
  - get
  - set
  - add
  - remove
  - transfer
- Executable example demonstrating resource operations.

### Changed

- Resource manipulation is now centralized rather than performed directly
  by simulation systems.

## v0.2.2 (Unreleased)

### Added

- Entities can now store structured resource quantities.
- Example demonstrating entity resources.

### Changed

- Resource quantities are represented as a nested `resources`
  attribute rather than individual flat attributes.

## v0.2.2 (Unreleased)

### Added

- Resource definitions and `ResourceDefinitionManager`.
- Resource registry exposed through `SimulationEngine`.
- Executable example demonstrating resource registration.

### Changed

- The engine now maintains a vocabulary of known resource types.

## v0.2.2 (Unreleased)

### Added

- Generic bounded progress support through `progress_min` and
  `progress_max`.
- Dedicated ProgressSystem test suite.

### Changed

- Progress is now clamped to optional inclusive bounds.
- Progress examples demonstrate bounded progression.

## v0.2.2 (Unreleased)

### Added

- `make` now performs the complete development validation workflow.
- `make examples` executes every example in a defined order.
- Snapshot creation helper (`tools/create_snapshot.sh`).

### Changed

- Examples are now treated as executable documentation.
- Development workflow documentation updated to reflect the new tooling.

## v0.2.1 (Unreleased)

### Added

- Development workflow documentation.
- Standardized Architecture Decision Record format.

### Changed

- Architecture Decision Records now follow a consistent naming convention
  and structure.
- Development practices are formally documented.

## v0.1.5 (Unreleased)

### Added

- `SimulationEngine` façade for composing the runtime.
- Engine-level system registration.
- Engine-level simulation execution.
- SimulationEngine test coverage.
- Public API example (`004_engine.py`).

### Changed

- Runtime components can now be accessed through `SimulationEngine`.

## v0.1.4 (Unreleased)

### Added

- `SimulationScheduler` for deterministic execution of simulation systems.
- Abstract `SimulationSystem` base class.
- Initial `ProgressSystem`.
- Scheduler test coverage.
- Scheduler example demonstrating world evolution.

### Changed

- Simulation tick now advances through the scheduler.

## v0.1.3 (Unreleased)

### Added

- Immutable `Event` runtime object.
- `EventManager` for recording world history.
- Event identifier generation.
- Event timestamps based on simulation ticks.
- EventManager test coverage.

### Changed

- `WorldState` now stores events by identifier.
- Examples demonstrate recording world history.

## v0.1.3 (Unreleased)

### Added

- Relationship lifecycle managed by `RelationshipManager.create()`.
- Automatic relationship identifier generation.
- Relationship validation during creation.
- RelationshipManager test coverage.

### Changed

- Runtime relationships are now created exclusively through `RelationshipManager`.
- Examples no longer mutate `WorldState` directly.
- Managers are now the exclusive mutation boundary of the simulation runtime.

## v0.1.3 (Unreleased)

### Added

- Entity lifecycle managed by `EntityManager.create()`.
- Dependency injection between `EntityManager` and `DefinitionManager`.
- Automatic entity ID generation.
- Initial attribute application from definitions.

### Changed

- `Definition.attributes` renamed to `Definition.initial_attributes`.
- Examples now demonstrate entity lifecycle through `EntityManager`.
- Tests updated to validate entity creation instead of direct insertion.

## v0.1.3 (Unreleased)

### Changed

- Replaced Location with Entity.
- Replaced Connection with Relationship.
- WorldState now stores entities and relationships.
- Introduced EntityManager.

### Removed

- GraphManager
- Location
- Connection

## v0.1.2

### Added
- ADR-0001: World is a Property Graph
- ADR-0002: Simulation Owns Truth
- ADR-0003: Core Runtime Model
- docs/core_model.md
- Definition class
- DefinitionManager skeleton
- Relationship class
- RelationshipManager skeleton

### Changed
- Architecture documentation aligned with property graph model.
