# 09 — Retrieval, context assembly, and boundary enforcement

## Task Description

Implement deterministic retrieval and an LLM-safe NPC context that exposes
only holder-scoped cognitive interpretations, never engine truth.

## Context Needed

- Create: `src/living_world/cognition/retrieval.py`,
  `src/living_world/cognition/information_boundary.py`,
  `tests/test_cognitive_retrieval.py`, `tests/test_npc_information_boundary.py`.
- Edit: `src/living_world/cognition/npc_context.py`, `cognition/__init__.py`,
  `tests/test_npc_context.py`, and standard docs/ADR.
- Know: Task 08 cognitive records, Task 08a `Knowledge`, `Observation`, current
  `NPCContextAssembler`, and `npc_information_boundary.md` in full.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    holder_id: str
    topic: str | None = None
    limit: int = 10

@dataclass(frozen=True, slots=True)
class RetrievedCognition:
    kind: Literal["memory", "belief", "experience", "relationship", "knowledge"]
    text: str
    importance: float
    is_core: bool

class CognitiveRetriever(Protocol):
    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedCognition, ...]: ...

@dataclass(frozen=True, slots=True)
class NPCContext:
    identity: str
    self_knowledge: tuple[str, ...]
    current_perceptions: tuple[str, ...]
    core_cognition: tuple[RetrievedCognition, ...]
    retrieved_information: tuple[RetrievedCognition, ...]
```

- The assembler uses `holder_id` internally but `NPCContext` has no holder or
  entity ID field. It accepts only prose capability descriptions.
- The initial policy returns the top ten core memories, beliefs, and
  experiences by deterministic salience/tick ordering. Relationships and
  knowledge claims are retrieved only when relevant to the query.
- `NPCInformationBoundary.validate_context(context: NPCContext) -> None`
  rejects raw mappings, engine object references, internal IDs, evidence,
  metadata, and known raw values.

## Test Criteria

- Another NPC’s cognition never appears.
- Top-ten core selection, relevance matching, and tie ordering are exact.
- Knowledge claims preserve their source attribution and do not displace the
  documented top-ten core memory/belief/experience policy.
- No returned item has an ID/provenance field; hostile metadata cannot leak.
- Context rejects raw skill numbers, `WorldState`, and raw entity attributes.
- `make` passes.

## Boundary

- Touch only stated cognition modules/tests/docs.
- Do not change perception engines: they are engine-side translators that may
  retain protected evidence.
- This task is the mandatory enforcement point for all rules in
  `npc_information_boundary.md`.
