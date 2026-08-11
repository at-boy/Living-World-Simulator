# 09 — Retrieval, context assembly, and boundary enforcement

## Task Description

Implement deterministic retrieval and an LLM-safe NPC context that exposes
only holder-scoped cognitive interpretations, never engine truth.

## Context Needed

- Create: `docs/subagent_execution_plan/09_npc_retrieval_context_boundary-report.md`.
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

class DeterministicCognitiveRetriever:
    def __init__(self, state: WorldState) -> None: ...
    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedCognition, ...]: ...

class NPCInformationBoundary:
    def __init__(self, state: WorldState) -> None: ...
    def validate_context(self, context: NPCContext) -> None: ...

@dataclass(frozen=True, slots=True)
class NPCContext:
    identity: str
    self_knowledge: tuple[str, ...]
    current_perceptions: tuple[str, ...]
    core_cognition: tuple[RetrievedCognition, ...]
    retrieved_information: tuple[RetrievedCognition, ...]

class NPCContextAssembler:
    def __init__(
        self,
        state: WorldState,
        retriever: CognitiveRetriever | None = None,
        boundary: NPCInformationBoundary | None = None,
    ) -> None: ...
    def assemble(
        self,
        *,
        holder_id: str,
        capability_descriptions: tuple[str, ...] = (),
        query: RetrievalQuery | None = None,
        max_perceptions: int | None = None,
    ) -> NPCContext: ...
```

- The assembler uses `holder_id` internally but `NPCContext` has no holder or
  entity ID field. It accepts only prose capability descriptions.
- The initial policy returns the top ten core memories, beliefs, and
  experiences by deterministic salience/tick ordering. Relationships and
  knowledge claims are retrieved only when relevant to the query.
- `RetrievalQuery` validates a non-empty holder ID, a non-empty topic when one
  is supplied, and a positive limit. Core records are ordered by descending
  salience importance, descending tick, then ascending record ID, before the
  query limit is applied. A relationship is relevant when its summary matches
  the query topic case-insensitively; knowledge is relevant when its statement
  or visible source description matches. Its returned text is
  `"{statement} Source: {source_description}"`. No ID, provenance, metadata,
  confidence, or raw attributes appear in `RetrievedCognition`.
- `NPCContextAssembler` requires a known entity holder and uses its display
  name only for `identity`; it never falls back to the internal holder ID.
  `capability_descriptions` must be a tuple of non-empty prose strings and is
  exposed only as `self_knowledge`. Current perceptions are holder-scoped
  observation descriptions; Task 09a will make their perception-boundary
  validation mandatory. The assembler validates its completed context before
  returning it.
- `NPCInformationBoundary.validate_context(context: NPCContext) -> None`
  rejects raw mappings, engine object references, internal IDs, evidence,
  metadata, and numeric values sourced from authoritative entity attributes.
  It must not reject ordinary qualitative prose merely because a word also
  names an attribute.

## Test Criteria

- Another NPC’s cognition never appears.
- Top-ten core selection, relevance matching, and tie ordering are exact.
- Knowledge claims preserve their source attribution and do not displace the
  documented top-ten core memory/belief/experience policy.
- No returned item has an ID/provenance field; hostile metadata cannot leak.
- Context rejects raw skill numbers, `WorldState`, and raw entity attributes.
- `make` passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/09_npc_retrieval_context_boundary-report.md`.
Report retrieval ordering/limits, holder isolation, explicit non-leakage test
evidence, changed public interfaces, and validation results.

## Boundary

- Touch only stated cognition modules/tests/docs.
- The approved report artifact is also allowed.
- Do not change perception engines: they are engine-side translators that may
  retain protected evidence.
- This task is the mandatory enforcement point for all rules in
  `npc_information_boundary.md`.
