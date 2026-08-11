# 09a — Perception-boundary enforcement

## Task Description

Make perception a rigorously enforced translation boundary so protected engine
data cannot cross from observations into NPC cognition.

## Context Needed

- Create: `docs/subagent_execution_plan/09a_perception_boundary_enforcement-report.md`.
- Create: `src/living_world/perception/npc_perception_boundary.py`,
  `tests/test_npc_perception_boundary.py`.
- Edit: `src/living_world/perception/deterministic_perception_engine.py`,
  `src/living_world/perception/llm_perception_engine.py`,
  `src/living_world/perception/llm_perception_client.py`,
  `src/living_world/perception/local_llm_perception_format.py`,
  `src/living_world/cognition/npc_context.py`,
  `tests/test_deterministic_perception_engine.py`,
  `tests/test_llm_perception_engine.py`, and `tests/test_npc_context.py`.
- Edit docs: `docs/npc_information_boundary.md`,
  `docs/architectural_direction.md`, `docs/core_model.md`, `CHANGELOG.md`,
  `docs/project_journal.md`.
- Know: `PerceptionContext`, `Observation`, current deterministic/LLM
  perception contracts, and Task 09's `NPCInformationBoundary`.

## Interface Contract

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

class DeterministicPerceptionEngine:
    def __init__(self, boundary: NPCPerceptionBoundary | None = None) -> None: ...
    def perceive(self, context: PerceptionContext) -> Observation: ...

class LLMPerceptionEngine:
    def __init__(
        self,
        client: LLMPerceptionClient,
        *,
        fallback_engine: PerceptionEngine | None = None,
        boundary: NPCPerceptionBoundary | None = None,
    ) -> None: ...
    def perceive(self, context: PerceptionContext) -> Observation: ...

class NPCContextAssembler:
    def __init__(
        self,
        state: WorldState,
        retriever: CognitiveRetriever | None = None,
        boundary: NPCInformationBoundary | None = None,
        perception_boundary: NPCPerceptionBoundary | None = None,
    ) -> None: ...
```

- `visible_description()` validates and returns only the NPC-readable
  observation description. It always rejects observation internal IDs, raw
  attribute notation, evidence/metadata vocabulary, hidden-state wording, and
  engine object names. When the optional engine-only `context` is supplied, it
  also rejects its observer/subject IDs and exact numeric values from protected
  attributes/capabilities, including nested values.
- `DeterministicPerceptionEngine` and `LLMPerceptionEngine` both validate their
  produced observation through this boundary with their `PerceptionContext`
  before returning it. The LLM engine retains its deterministic fallback
  behavior and validates the fallback output through the same boundary.
- `NPCContextAssembler` obtains current perceptions exclusively through
  `NPCPerceptionBoundary.visible_description(observation)` with no context; it
  must never retain/read `PerceptionContext`, `Observation.evidence`, or
  `Observation.metadata`. Add an optional boundary constructor dependency to
  `NPCContextAssembler`, defaulting to `DefaultNPCPerceptionBoundary`.
- The LLM perception request may remain a curated engine-side translation
  request containing attributes, as documented. It is not NPC cognition and
  must never be reused as an NPC-context or cognition-client request.

## Test Criteria

- Both engines reject/fallback from an unsafe description containing an ID,
  exact protected value, raw attribute notation, or hidden-state wording.
- Safe qualitative descriptions remain valid, including ordinary words that
  happen to match an attribute name.
- Protected evidence is retained for engine debugging but cannot be obtained
  through `NPCContext` or retrieval.
- A perception LLM request is demonstrably distinct from an NPC cognition
  request and has no path into the latter.
- All existing perception tests, context tests, and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/09a_perception_boundary_enforcement-report.md`.
Report unsafe-output cases tested, fallback behavior, evidence-retention versus
context-exclusion proof, and validation results.

## Boundary

- Touch only the listed perception/context/test/documentation files.
- The approved report artifact is also allowed.
- Do not change the domain meaning of observations, beliefs, memories, or
  actions; this task enforces the translation boundary only.
- Follow the explicit distinction in `npc_information_boundary.md`: the
  perception LLM is simulation machinery, while the NPC LLM receives only the
  filtered observation result.
