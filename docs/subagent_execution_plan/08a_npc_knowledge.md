# 08a — NPC knowledge

## Task Description

Add source-attributed NPC knowledge as a distinct cognitive record, preserving
the difference between what an NPC has heard and what the simulation knows.

## Context Needed

- Create: `docs/subagent_execution_plan/08a_npc_knowledge-report.md`.
- Create: `src/living_world/core/knowledge.py`,
  `src/living_world/managers/knowledge_manager.py`,
  `tests/test_knowledge.py`, `tests/test_knowledge_manager.py`, and
  `examples/019_npc_knowledge.py`.
- Edit: `src/living_world/state/world_state.py`,
  `src/living_world/simulation/simulation_engine.py`,
  `src/living_world/cognition/__init__.py`, `Makefile`,
  `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Know: Task 08's `Memory`, `Belief`, `Experience`, `NPCRelationship`,
  `CognitiveSalience`, and the current `Observation` model.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class Knowledge:
    id: str
    tick: int
    holder_id: str
    subject_id: str
    statement: str
    source_description: str
    salience: CognitiveSalience
    supporting_observations: tuple[str, ...] = ()
    supporting_memories: tuple[str, ...] = ()
    supporting_experiences: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
```

```python
class KnowledgeManager:
    def __init__(self, state: WorldState) -> None: ...
    def record(
        self,
        *,
        holder_id: str,
        subject_id: str,
        statement: str,
        source_description: str,
        salience: CognitiveSalience,
        supporting_observations: tuple[str, ...] = (),
        supporting_memories: tuple[str, ...] = (),
        supporting_experiences: tuple[str, ...] = (),
        metadata: Mapping[str, object] | None = None,
    ) -> Knowledge: ...
    def knowledge_for(self, holder_id: str) -> tuple[Knowledge, ...]: ...
```

- `Knowledge` is an NPC-held, source-attributed claim: for example, “The
  miller told me the east bridge is closed.” It is distinct from `Memory`
  (what was retained), `Belief` (an inference), and `Experience` (learning
  from lived interaction).
- It is not authoritative simulation truth and can be incomplete, stale, or
  false. Its `source_description` is NPC-readable attribution, never an
  engine ID, evidence dump, or privileged event record.
- Add `knowledge: dict[str, Knowledge]` to `WorldState` and expose
  `SimulationEngine.knowledge` as its manager. Only `KnowledgeManager` mutates
  that collection.

## Test Criteria

- Knowledge is immutable, validates non-empty visible text and holder/subject,
  and defensively freezes metadata.
- Holder-scoped lookup cannot return another NPC's knowledge.
- Source attribution and provenance links are retained while raw engine data
  cannot enter `statement` or `source_description`.
- Engine wiring, the example, and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/08a_npc_knowledge-report.md`. Report the
implemented distinction between knowledge, memory, belief, and experience;
source-attribution safeguards; boundary evidence; and validation results.

## Boundary

- Touch only the listed knowledge/state/engine/export/example/test/docs files.
- The approved report artifact is also allowed.
- Do not alter retrieval or prompt context in this task; Task 09 consumes this
  completed interface.
- Adhere to `docs/architectural_direction.md` and
  `docs/npc_information_boundary.md`: knowledge is NPC cognition, never a
  second representation of world truth.
