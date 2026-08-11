# Task 09 — NPC retrieval, context assembly, and boundary enforcement report

## Outcome

Implemented deterministic, read-only holder-scoped cognitive retrieval and a
validated NPC context projection. The completed `NPCContext` contains no
holder/entity ID and no raw capability mapping.

## Files Changed

- `src/living_world/cognition/retrieval.py`
- `src/living_world/cognition/information_boundary.py`
- `src/living_world/cognition/npc_context.py`
- `src/living_world/cognition/__init__.py`
- `tests/test_cognitive_retrieval.py`
- `tests/test_npc_information_boundary.py`
- `tests/test_npc_context.py`
- `docs/adr/ADR-0009-npc-retrieval-context-boundary.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/backlog.md`
- `docs/subagent_execution_plan/09_npc_retrieval_context_boundary.md`
- `docs/subagent_execution_plan/09_npc_retrieval_context_boundary-prombt.md`
- `docs/subagent_execution_plan/09_npc_retrieval_context_boundary-correction-prombt.md`
- `docs/subagent_execution_plan/09_npc_retrieval_context_boundary-report.md`

## Public Interfaces

- `RetrievalQuery(holder_id: str, topic: str | None = None, limit: int = 10)`
  validates holder, optional topic, and positive limits.
- `RetrievedCognition` is the restricted result projection containing only
  kind, visible text, importance, and core status.
- `CognitiveRetriever` is the protocol; `DeterministicCognitiveRetriever`
  implements it over internal `WorldState`.
- `NPCContext` now contains identity, prose self-knowledge, current
  perceptions, core cognition, and retrieved information. It has no internal
  holder field.
- `NPCContextAssembler` accepts injectable retrieval and boundary protocols,
  requires a known holder, validates query ownership, and validates the
  finished context before return.
- `NPCInformationBoundary.validate_context(context: NPCContext) -> None`
  rejects structural engine data, internal IDs, and authoritative numeric
  attribute values.

## Retrieval and Isolation Evidence

Core memory, belief, and experience results are ordered by descending
salience importance, descending tick, then ascending record ID before the
limit is applied. The default limit is ten. Relationships and knowledge are
returned only for a non-empty case-insensitive query match, after core records
and within the same limit. Knowledge is rendered only as
`"{statement} Source: {source_description}"`.

Focused tests prove that another holder's cognition never appears, the exact
top-ten order is stable, query matching is holder-scoped, and no result has an
ID or provenance field. Hidden knowledge metadata does not become result text.

## Information-Boundary Evidence

The boundary admits qualitative prose such as "healthy" and "woodcraft" even
when those words also name attributes. It rejects raw mappings, engine object
references, known internal IDs, and numeric text matching authoritative entity
attributes, including nested skill values. Context assembly performs this
validation as a mandatory final step.

The correction adds direct proof that an otherwise valid `NPCContext` is
rejected when a raw `WorldState` is substituted into its identity field. It
also independently proves rejection when NPC-facing prose contains a raw value
from `attributes["skills"]`; the validator remains structural/value-aware and
does not rely on an attribute-name word blacklist.

## Validation

- `make` — passed after the correction: Ruff, Black, **223 pytest tests**, and
  examples `001` through `019` passed.
- `make examples` — passed after the correction: examples `001` through `019`
  passed.
- `git diff --check` — passed after the correction with no whitespace errors.

## Documentation and Boundary Compliance

ADR-0009 records the retrieval policy and the eight required engine/NPC
information-boundary questions. The core model, glossary, changelog, journal,
and backlog were updated. Perception engines, persistence, HTTP inspection,
LLM invocation, and actions were not changed. Task 09a remains responsible
for mandatory perception-description filtering.

## Blockers and Deferred Work

No blockers. Task 09a remains responsible for mandatory
perception-description filtering.
