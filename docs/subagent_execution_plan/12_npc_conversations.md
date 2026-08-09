# 12 — NPC conversations

## Task Description

Implement bounded NPC dialogue as visible, recordable perception while keeping
private cognition private and all proposed actions non-authoritative.

## Context Needed

- Create: `docs/subagent_execution_plan/12_npc_conversations-report.md`.
- Create: `src/living_world/cognition/conversation.py`,
  `tests/test_conversation.py`, `examples/019_npc_conversations.py`.
- Edit: `src/living_world/cognition/__init__.py`,
  `src/living_world/simulation/simulation_engine.py`, `Makefile`, and standard
  docs.
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
    def conduct(
        self,
        *,
        participant_ids: tuple[str, ...],
        topic: str,
        max_turns: int,
    ) -> ConversationResult: ...
```

- IDs are service-internal; each model receives a fresh filtered context and
  only earlier visible turns.
- An utterance is recorded as an NPC-readable observation for recipients. It
  can later become memory through normal consolidation, not instantly as fact.
- Any proposed action passes through the Task 11 resolver.

## Test Criteria

- Private cognition of a non-speaker never leaks to other participants.
- Recipient observations contain prose only, no transcript metadata or IDs.
- Invalid/rejected proposals cause no world mutation.
- Turn ordering and `max_turns` are deterministic; example and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/12_npc_conversations-report.md`. Report
turn-context filtering, recipient-observation recording, private-cognition
isolation, action-resolution evidence, and validation results.

## Boundary

- Touch only stated conversation files, integration, tests, example, and docs.
- The approved report artifact is also allowed.
- Do not implement council policy here.
- Adhere to the information boundary for every turn, not merely initial context.
