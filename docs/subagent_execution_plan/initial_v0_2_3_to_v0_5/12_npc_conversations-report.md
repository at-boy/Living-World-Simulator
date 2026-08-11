# Task 12 — NPC Conversations Report

## Outcome

Implemented bounded NPC dialogue as visible recipient observations. The service
keeps internal participant identifiers and action resolutions out of every
model context, and it does not create cognitive records, relationships, or
events.

## Files Changed

- `src/living_world/cognition/conversation.py`
- `src/living_world/cognition/npc_context.py`
- `src/living_world/cognition/information_boundary.py`
- `src/living_world/cognition/local_llm_cognition_format.py`
- `src/living_world/cognition/__init__.py`
- `src/living_world/simulation/simulation_engine.py`
- `tests/test_conversation.py`
- `tests/test_npc_context.py`
- `tests/test_npc_information_boundary.py`
- `tests/test_npc_cognition_client.py`
- `examples/020_npc_conversations.py`
- `docs/adr/ADR-0011-npc-conversation-boundary.md`
- `CHANGELOG.md`, `docs/project_journal.md`, `docs/backlog.md`,
  `docs/core_model.md`, and `docs/engine_glossary.md`
- Task-plan artifacts: `12_npc_conversations.md` and
  `12_npc_conversations-prombt.md`, plus the documented
  `12_npc_conversations-correction-prombt.md`

## Public Interfaces

- `ConversationTurn(speaker_label: str, utterance: str)`
- `ConversationResult(turns: tuple[ConversationTurn, ...], resolutions:
  tuple[ActionResolution, ...])`
- `ConversationService(...).conduct(*, participant_ids: tuple[str, ...],
  topic: str, max_turns: int) -> ConversationResult`
- `NPCContext.conversation_history: tuple[str, ...] = ()`
- `NPCContextAssembler.assemble(..., conversation_history: tuple[str, ...] =
  ()) -> NPCContext`
- `SimulationEngine.conduct_npc_conversation(...) -> ConversationResult`

## Boundary Evidence

- A fresh holder-scoped context is assembled for each turn. Tests demonstrate
  that each speaker receives only its own cognitive retrieval projection.
- Context history contains a validated topic preamble and prior visible turns
  in the form `"Display Name: utterance"`. Internal IDs and authoritative
  attribute numbers are
  rejected before topic-model invocation; returned unsafe speech is rejected
  before an observation write or later history use.
- Spoken text is recorded for every other participant in supplied order as an
  observation whose description is only the utterance and whose evidence and
  metadata are empty.
- A proposed action is passed to `NPCActionResolver` with an internal actor ID
  only. The test covers the no-handler rejection path with no observations or
  events; no action result is put in model context.
- The service has no default action handler and adds no direct memory, belief,
  experience, relationship, event, council, or governance behavior.

## Tests and Validation

- Added focused tests for private-cognition isolation, visible recipient
  observations, safe serialized history, unsafe topic/speech rejection,
  invalid input no-call/no-write behavior, deterministic ordering, rejected
  action non-mutation, and engine delegation.
- Added direct `NPCInformationBoundary.validate_context()` coverage proving it
  rejects both internal IDs and authoritative numeric values in
  `conversation_history`.
- Post-correction `make` — passed: Ruff, Black, 282 pytest tests, and examples
  001–020.
- `make examples` — passed: examples 001–020.
- `git diff --check` — passed.

## Documentation

Added ADR-0011 and updated the backlog, core model, engine glossary,
changelog, and project journal with the conversation boundary and normal
consolidation behavior.

## Boundary Compliance

Only the Task 12-approved code, tests, example, documentation, ADR, plan
artifacts, and this report were edited. No resolver/client authority rules,
domain action handlers, Makefile, or council policy were changed.

## Blockers

None.
