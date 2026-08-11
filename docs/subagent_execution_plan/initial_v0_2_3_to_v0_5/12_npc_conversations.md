# 12 — NPC conversations

## Task Description

Implement bounded NPC dialogue as visible, recordable perception while keeping
private cognition private and all proposed actions non-authoritative.

## Context Needed

- Create: `docs/subagent_execution_plan/12_npc_conversations-report.md`.
- Create: `src/living_world/cognition/conversation.py`,
  `tests/test_conversation.py`, `examples/020_npc_conversations.py`.
- Edit: `src/living_world/cognition/__init__.py`,
  `src/living_world/simulation/simulation_engine.py`,
  `src/living_world/cognition/npc_context.py`,
  `src/living_world/cognition/information_boundary.py`,
  `src/living_world/cognition/local_llm_cognition_format.py`,
  `tests/test_npc_context.py`, `tests/test_npc_information_boundary.py`,
  `tests/test_npc_cognition_client.py`, `CHANGELOG.md`, `docs/project_journal.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`, and an ADR.
- Know: `NPCContextAssembler`, `DecisionEngine`, `ObservationManager`,
  `MemoryManager`, `NPCActionResolver`, and Task 09 boundary validation.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class ConversationTurn:
    speaker_label: str
    utterance: str

@dataclass(frozen=True, slots=True)
class ConversationResult:
    turns: tuple[ConversationTurn, ...]
    resolutions: tuple[ActionResolution, ...]

class ConversationService:
    def __init__(
        self,
        context_assembler: NPCContextAssembler,
        decision_engine: DecisionEngine,
        action_resolver: NPCActionResolver,
        observations: ObservationManager,
        action_options: tuple[ActionOption, ...],
    ) -> None: ...
    def conduct(
        self,
        *,
        participant_ids: tuple[str, ...],
        topic: str,
        max_turns: int,
    ) -> ConversationResult: ...
```

- Extend `NPCContext` with
  `conversation_history: tuple[str, ...] = ()`, and extend
  `NPCContextAssembler.assemble()` with a matching keyword-only parameter.
  It is prose-only, fully validated by `NPCInformationBoundary`, and must be
  included in Task 10's serialized local-LLM request. It contains the safe
  topic preamble and only prior visible turn prose—never participant IDs,
  observation IDs, transcript objects, metadata, evidence, or raw state.
- `participant_ids` are service-internal. They must be a non-empty, unique
  tuple of known entities; the service validates them before any context
  assembly or model call. `topic` is non-empty prose and `max_turns` is a
  non-negative non-boolean integer. Turn speakers follow the supplied
  participant order cyclically, for exactly at most `max_turns` model calls.
- Each model receives a freshly assembled, boundary-validated context with the
  safe topic/history accumulated before its own turn. Every returned utterance
  must be boundary-validated before it is recorded or supplied to a later
  model.
- An utterance is recorded as an NPC-readable observation for recipients. It
  uses only the visible utterance as its description and empty evidence and
  metadata; recipient and speaker IDs stay solely in the internal observation
  record. It can later become memory through normal consolidation, not
  instantly as fact.
- Any proposed action passes through the Task 11 resolver.
- `ConversationService` adds no memory, belief, experience, relationship, or
  event. It has no default action handler and does not treat speech or an
  accepted action as a fact or a successful conversation outcome.

## Test Criteria

- Private cognition of a non-speaker never leaks to other participants.
- Recipient observations contain prose only, no transcript metadata or IDs.
- Local-client serialization contains the safe conversation history and no
  internal conversation representation; unsafe history (ID, raw state or an
  authoritative number) is rejected before a model call or observation write.
- Invalid/rejected proposals cause no world mutation.
- Turn ordering, recipient observation order, action-resolution order, and
  `max_turns` are deterministic. Invalid participant/topic/bound inputs make
  no model calls or observation writes. The example and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/12_npc_conversations-report.md`. Report
turn-context filtering, recipient-observation recording, private-cognition
isolation, action-resolution evidence, and validation results.

## Boundary

- Touch only stated conversation/context/format files, integration, tests,
  example, ADR, and docs.
- The approved report artifact is also allowed.
- Do not implement council policy here.
- Adhere to the information boundary for every turn, not merely initial context.
