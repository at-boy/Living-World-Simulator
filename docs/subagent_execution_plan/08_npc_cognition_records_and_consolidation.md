# 08 — Cognitive records and sleep consolidation

## Task Description

Complete the core v0.4 cognitive record model and add sleep-time consolidation
that creates NPC interpretations without converting them into world truth.

## Context Needed

- Create: `docs/subagent_execution_plan/08_npc_cognition_records_and_consolidation-report.md`.
- Create: `src/living_world/core/memory.py`,
  `src/living_world/core/npc_relationship.py`,
  `src/living_world/managers/memory_manager.py`,
  `src/living_world/managers/npc_relationship_manager.py`,
  `src/living_world/cognition/consolidation.py`,
  `tests/test_memory.py`, `tests/test_memory_manager.py`,
  `tests/test_npc_relationship.py`, `tests/test_consolidation.py`,
  `examples/018_npc_cognition.py`.
- Edit: `core/belief.py`, `core/experience.py`, `state/world_state.py`,
  `simulation/simulation_engine.py`, `cognition/__init__.py`, `Makefile`, and
  standard docs/ADR.
- Know: immutable `Observation`, `Belief`, `Experience`, their managers, and
  the sleep requirement in `architectural_direction.md`.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class CognitiveSalience:
    importance: float
    is_core: bool = False

@dataclass(frozen=True, slots=True)
class Memory: ...

@dataclass(frozen=True, slots=True)
class NPCRelationship: ...

class CognitiveConsolidator(Protocol):
    def consolidate(self, *, holder_id: str, through_tick: int) -> tuple[Memory | Experience | Belief, ...]: ...
```

- Salience has `0.0 <= importance <= 1.0`; core requires `importance >= 0.8`.
  Important (`>=0.6`) and core are distinct.
- Memory, belief, experience, and NPC relationship records are immutable,
  holder-scoped interpretations. Their internal provenance links may use IDs,
  but their visible summaries/descriptions may not contain engine truth.
- Consolidation runs only during an explicit sleep schedule activity, consumes
  the prior day’s observations, and may create memory, repeated-observation
  experiences, and belief candidates. It never asserts a belief as fact.

## Test Criteria

- Records validate, are immutable, and remain holder-scoped.
- Sleep consolidation ignores current-day/ineligible material and is
  deterministic/idempotent for the same processed inputs.
- Candidate beliefs retain provenance and can be wrong.
- Existing observation, belief, and experience tests remain green; example and
  `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/08_npc_cognition_records_and_consolidation-report.md`.
Report the cognitive-model distinctions, consolidation eligibility/idempotence
evidence, provenance handling, boundary audit, and validation results.

## Boundary

- Touch only listed cognitive record/manager/consolidation files and stated
  integration/docs, plus the approved report artifact.
- Generic `Relationship` stays authoritative graph infrastructure; do not turn
  it into NPC knowledge.
- Adhere to the cognitive distinctions and sleep policy in architectural docs.
