# Task 09a — Perception-Boundary Enforcement Report

## Outcome

Completed the perception translation guard without changing observation,
cognition, belief, memory, experience, action, persistence, or HTTP domain
semantics. `NPCPerceptionBoundary` is now the shared validator for the
NPC-readable projection of an `Observation`.

## Files Changed

- `src/living_world/perception/npc_perception_boundary.py` (new)
- `src/living_world/perception/deterministic_perception_engine.py`
- `src/living_world/perception/llm_perception_engine.py`
- `src/living_world/perception/llm_perception_client.py`
- `src/living_world/perception/local_llm_perception_format.py`
- `src/living_world/cognition/npc_context.py`
- `tests/test_npc_perception_boundary.py` (new)
- `tests/test_deterministic_perception_engine.py`
- `tests/test_llm_perception_engine.py`
- `tests/test_llm_perception_client.py`
- `tests/test_npc_context.py`
- `docs/npc_information_boundary.md`
- `docs/architectural_direction.md`
- `docs/core_model.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/09a_perception_boundary_enforcement.md`
- `docs/subagent_execution_plan/09a_perception_boundary_enforcement-prombt.md`
- `docs/subagent_execution_plan/09a_perception_boundary_enforcement-report.md`

## Public Interfaces

```python
class NPCPerceptionBoundary(Protocol):
    def visible_description(
        self,
        observation: Observation,
        *,
        context: PerceptionContext | None = None,
    ) -> str: ...

class DefaultNPCPerceptionBoundary:
    def visible_description(
        self,
        observation: Observation,
        *,
        context: PerceptionContext | None = None,
    ) -> str: ...
```

- `DeterministicPerceptionEngine(boundary: NPCPerceptionBoundary | None = None)`
  validates every produced observation with its engine-only context and fails
  closed if the boundary rejects it.
- `LLMPerceptionEngine(..., boundary: NPCPerceptionBoundary | None = None)`
  uses the same context-aware validation. Unsafe provider output uses the
  existing deterministic fallback; unsafe fallback output raises
  `LLMPerceptionFallbackError`.
- `NPCContextAssembler(..., perception_boundary: NPCPerceptionBoundary | None = None)`
  obtains current perceptions exclusively through
  `visible_description(observation)`, without passing a `PerceptionContext`.

## Boundary Evidence

- Unit tests reject observation IDs, observer/subject IDs, exact protected
  subject and nested-capability numbers, raw notation such as `wood=120`,
  evidence/metadata vocabulary, hidden-state wording, and `WorldState` engine
  wording.
- Qualitative prose using ordinary words such as `healthy` and `wood` remains
  valid.
- Both engines keep their observation evidence. Context assembly projects only
  the description and the recording test proves it supplies `None` rather than
  an engine context to its boundary dependency.
- Unsafe LLM provider descriptions fall back. A deliberately unsafe fallback
  is rejected with the dedicated fallback error.
- `LLMPerceptionRequest` continues to hold curated provider data only and is
  explicitly documented and tested as distinct from `NPCContext` fields; no
  cognition-client pathway was added.

## Validation

All commands passed:

```text
make
# Ruff and Black passed; 237 pytest tests passed; examples 001–019 passed.

make examples
# examples 001–019 passed.

git diff --check
# passed with no output.
```

## Documentation and Boundary Compliance

The information-boundary, architecture, core-model, changelog, and journal
documents now distinguish the engine-side perception request and context-aware
validation from the contextless NPC-facing projection. Only files authorized by
Task 09a were created or edited, apart from pre-existing plan/prompt working
tree changes. No blockers or deferred implementation work remain for this
task.
