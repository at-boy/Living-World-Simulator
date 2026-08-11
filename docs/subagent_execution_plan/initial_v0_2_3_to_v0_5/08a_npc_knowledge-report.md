# Task 08a — NPC knowledge report

## Outcome

Implemented immutable, holder-scoped `Knowledge` records for NPC-attributed
claims. Knowledge represents what an NPC has heard or learned; it is not a
statement of authoritative simulation truth and may be incomplete, stale, or
false.

## Files Changed

- `src/living_world/core/knowledge.py`
- `src/living_world/managers/knowledge_manager.py`
- `src/living_world/state/world_state.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/cognition/__init__.py`
- `tests/test_knowledge.py`
- `tests/test_knowledge_manager.py`
- `tests/test_simulation_engine.py`
- `tests/test_sqlite_repository.py`
- `examples/019_npc_knowledge.py`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/08a_npc_knowledge.md`
- `docs/subagent_execution_plan/08a_npc_knowledge-prombt.md`
- `docs/subagent_execution_plan/08a_npc_knowledge-correction-prombt.md`
- `docs/subagent_execution_plan/08a_npc_knowledge-report.md`

`Makefile` was not changed. Its existing numbered-example wildcard discovers
and executes `examples/019_npc_knowledge.py`, so a no-op Makefile edit was not
needed.

## Public Interfaces

Added `Knowledge`, a frozen slots dataclass with the specified identifier,
tick, holder, subject, visible statement, visible source description,
`CognitiveSalience`, internal provenance tuples, and defensively copied
recursively immutable metadata. Each provenance field requires exactly a
`tuple[str, ...]`; strings and other iterables are rejected.

Added `KnowledgeManager(state: WorldState)` with the specified
`record(...) -> Knowledge` and `knowledge_for(holder_id) -> tuple[Knowledge,
...]` interfaces, plus manager-consistent `add`, `get`, and `all` helpers.
The manager is exposed through `SimulationEngine.knowledge`; `WorldState`
owns `knowledge: dict[str, Knowledge]` and no other task code mutates that
collection.

## Cognitive Distinction and Information Boundary

- `Memory` retains an interpretation of an observation.
- `Experience` represents learning from lived or repeated interaction.
- `Belief` is an inference with confidence and status.
- `Knowledge` is a source-attributed claim the holder has heard or learned.

Visible `statement` and `source_description` fields are supplied as
NPC-readable prose. The manager accepts no `WorldState`, entity attribute,
evidence, event, or inspection payload as an input for either field. Internal
observation, memory, and experience identifiers are held only in dedicated
provenance tuples. The record rejects either visible field when it contains a
provided provenance identifier, so internal record links cannot become
NPC-visible prose. No retrieval, context assembly, prompt construction, or
LLM integration was added.

## SQLite and Legacy Compatibility

`SQLiteRepository` serializes and deserializes all Knowledge fields: salience,
source attribution, three provenance collections, and metadata. A round-trip
assertion verifies equality with the original knowledge collection. A legacy
payload with no `knowledge` collection loads as an empty collection without
discarding the rest of the snapshot. Recursively frozen mappings, tuples, and
sets are explicitly converted to JSON-safe mutable values for persistence and
are safely frozen again on load.

## Tests and Validation

- `make` — passed after the correction: Ruff fixed one newly introduced test
  lint issue, then Ruff check, Black check, 214 pytest tests, and examples
  `001` through `019` all passed.
- `make examples` — passed: all examples `001` through `019` passed.
- `git diff --check` — passed with no whitespace errors.

Focused coverage validates immutable recursively frozen metadata (including
input detachment and nested mutation rejection), exact tuple provenance,
visible-text provenance rejection, identity validation, holder-scoped lookup,
engine wiring, SQLite complete-record persistence, and legacy snapshot
loading.

## Documentation

Updated the core model, engine glossary, changelog, and project journal to
state the distinct semantics and NPC information boundary of Knowledge.

## Boundary Compliance

Only the Task 08a-allowed code, test, example, documentation, persistence,
and report files were created or edited. The existing Makefile was intentionally
left unchanged because its automatic example discovery already covers the new
example. Retrieval/context assembly and LLM/prompt behavior remain deferred to
Task 09.

## Correction Applied

The narrow correction requires exact provenance tuple types, recursively
immutable metadata, and record-boundary prevention of provenance IDs leaking
into visible text. The SQLite serializer now explicitly thaws frozen metadata
to JSON-safe values before storage. Direct model and persistence tests cover
these rules.

## Blockers and Deferred Work

No blockers. Task 09 remains responsible for consuming completed cognitive
records in a holder-scoped retrieval/context boundary.
