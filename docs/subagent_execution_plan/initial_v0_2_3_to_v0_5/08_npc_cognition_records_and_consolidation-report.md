# Task 08 — Orchestrator Report

## Outcome

Completed the v0.4 holder-scoped cognitive record model and deterministic
sleep-time consolidation. No NPC cognition record is an authoritative world
fact, and candidate beliefs are explicitly marked `BeliefStatus.CANDIDATE`.

## Files Changed

- `src/living_world/core/memory.py`
- `src/living_world/core/npc_relationship.py`
- `src/living_world/core/belief.py`
- `src/living_world/core/experience.py`
- `src/living_world/managers/memory_manager.py`
- `src/living_world/managers/npc_relationship_manager.py`
- `src/living_world/managers/belief_manager.py`
- `src/living_world/managers/experience_manager.py`
- `src/living_world/cognition/consolidation.py`
- `src/living_world/cognition/__init__.py`
- `src/living_world/state/world_state.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `tests/test_memory.py`
- `tests/test_memory_manager.py`
- `tests/test_npc_relationship.py`
- `tests/test_consolidation.py`
- `tests/test_sqlite_repository.py`
- `examples/018_npc_cognition.py`
- `docs/adr/ADR-0008-npc-cognitive-records.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/backlog.md`
- `CHANGELOG.md`
- `docs/project_journal.md`

## Public Interfaces and Record Schemas

- `CognitiveSalience(importance: float, is_core: bool = False)` validates an
  inclusive `0.0..1.0` importance range; important is `>= 0.6`, and core
  requires both `is_core=True` and importance `>= 0.8`.
- `Memory` and `NPCRelationship` are frozen, slotted, holder-scoped records
  containing `id`, `tick`, `holder_id`, `subject_id`, visible `summary`,
  `salience`, and internal `source_observation_ids` provenance.
- `MemoryManager` and `NPCRelationshipManager` own their lifecycle and
  identifiers. `MemoryManager.has_observation_provenance()` supports explicit
  idempotence checks.
- `Belief` and `Experience` now retain `CognitiveSalience`; existing manager
  APIs accept an optional salience extension without breaking callers.
- `CognitiveConsolidator` defines
  `consolidate(*, holder_id: str, through_tick: int) -> tuple[Memory |
  Experience | Belief, ...]`. `SleepCognitiveConsolidator` implements it.
- `SimulationEngine.memories` and `SimulationEngine.npc_relationships` expose
  the new lifecycle managers.

## Consolidation Eligibility and Idempotence

- A cognitive day is explicitly 24 ticks (`DAY_LENGTH_TICKS = 24`). At ticks
  24–47, only observations with ticks 0–23 are eligible; current-day material
  is excluded.
- Consolidation returns no records unless the holder exists and its
  engine-owned `active_activity` equals exactly `"sleeping"`.
- Eligible observations are ordered by `(tick, id)`. Each unprocessed source
  creates one memory. Two or more observations of the same subject create one
  repeated-observation experience and one candidate belief.
- Provenance is stored as observation IDs on cognitive records. Existing
  memory, experience, and belief provenance prevents duplicate records on a
  repeated call and after SQLite reload.
- `CognitiveConsolidationSystem` is registered after `ScheduleSystem`, so the
  current schedule activity is established before consolidation runs.

## Information-Boundary Audit

- Consolidation derives every visible summary and proposition exclusively from
  `Observation.description`.
- `Observation.evidence`, entity attributes, resource quantities, events, and
  provenance IDs are never interpolated into visible cognitive prose.
- `NPCRelationship` is a separate holder-scoped interpretation collection;
  generic `Relationship` remains authoritative graph infrastructure.
- The implementation adds no NPC subclass, LLM, retrieval path, or action
  handling. Candidate beliefs remain cognitive interpretations and can be
  wrong.

## Persistence

SQLite serialization and reconstruction now cover memories, NPC relationships,
cognitive salience, and provenance. The deserializer accepts snapshots made
before the new collections/salience fields by using empty collections and the
legacy belief/experience salience defaults. Round-trip tests confirm immutable
cognitive records and provenance survive reload; a reloaded consolidator
returns no duplicate records for the same source inputs.

## Validation

- `make` — passed: Ruff auto-fix/check, Black formatting/check, and **201
  pytest tests**.
- `make examples` — passed: executable examples `001` through `018`.
- `git diff --check` — passed with no whitespace errors.

## Boundary Compliance

All implementation changes are confined to Task 08's approved cognitive,
manager, engine/state, SQLite, test, example, documentation, ADR, and report
boundary. The canonical Task 08 plan and saved prompt were amended by the
orchestrator before implementation to authorize SQLite persistence.

## Blockers / Deferred Work

None. Retrieval, LLM-safe context assembly, knowledge claims, and further
information-boundary enforcement remain explicitly deferred to their planned
tasks.
