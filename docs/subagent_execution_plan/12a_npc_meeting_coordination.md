# 12a — NPC meeting coordination and directed dialogue

## Task Description

Add engine-owned coordination for an NPC to request a bounded meeting with one
or more other NPCs, and for the simulation to call specific participants to
speak. This is ephemeral conversation orchestration, not a social, consent,
governance, or world-state subsystem.

## Context Needed

- Create: `docs/subagent_execution_plan/12a_npc_meeting_coordination-report.md`,
  `src/living_world/cognition/meeting.py`,
  `tests/test_meeting.py`, and `examples/021_npc_meeting.py`.
- Edit: `src/living_world/cognition/conversation.py`,
  `tests/test_conversation.py`,
  `src/living_world/cognition/__init__.py`,
  `src/living_world/simulation/simulation_engine.py`, `CHANGELOG.md`,
  `docs/project_journal.md`, `docs/backlog.md`, `docs/core_model.md`,
  `docs/engine_glossary.md`, and create an ADR.
- Know: `ConversationService`, `ConversationResult`, `NPCContextAssembler`,
  `DecisionEngine`, `NPCActionResolver`, `ActionOption`, and every NPC
  information-boundary rule.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class MeetingRequest:
    requester_id: str
    invitee_ids: tuple[str, ...]
    topic: str
    max_turns: int
    called_speaker_ids: tuple[str, ...] = ()
    participant_self_knowledge: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict
    )

class MeetingService:
    def __init__(self, conversation_service: ConversationService) -> None: ...
    def conduct(self, request: MeetingRequest) -> ConversationResult: ...

class ConversationService:
    def conduct(
        self,
        *,
        participant_ids: tuple[str, ...],
        topic: str,
        max_turns: int,
        called_speaker_ids: tuple[str, ...] = (),
        participant_self_knowledge: Mapping[str, tuple[str, ...]] | None = None,
    ) -> ConversationResult: ...
```

- `requester_id`, `invitee_ids`, `called_speaker_ids`, and mapping keys are
  engine/service-internal identifiers. They are never serialized, included in
  `NPCContext`, or returned in visible conversation data.
- A request requires one known requester and one or more distinct known
  invitees. Its effective participant order is requester first, then invitees
  in supplied order. A requester may not invite itself.
- When `called_speaker_ids` is empty, the existing deterministic cyclic
  participant order applies. When supplied, it is the exact bounded speaking
  schedule: it must be non-empty, contain only effective participants, and
  have length no greater than `max_turns`. A speaker may occur more than once,
  allowing the simulation to call that NPC back for a later response. The
  schedule is never disclosed to a model.
- `participant_self_knowledge` is optional engine-side setup for safe,
  qualitative participant perspective prose (for example, a stated concern or
  preference). It must have keys only from effective participants and values
  that are non-empty tuples of boundary-valid prose. A speaker receives only
  its own value through `NPCContext.self_knowledge`; no participant receives
  another participant's private perspective mapping. An omitted key means no
  additional self-knowledge. The mapping is copied/frozen on `MeetingRequest`.
- `MeetingService` delegates entirely to `ConversationService`. It creates no
  `Meeting` world object, relationship, event, acceptance/consent record,
  memory, belief, or policy result. Dialogue and action proposals retain all
  Task 12 and Task 11 guarantees.
- Add `SimulationEngine.conduct_npc_meeting(*, service: MeetingService,
  request: MeetingRequest) -> ConversationResult` as a thin delegation method.

## Test Criteria

- A one-to-many request yields requester-first, deterministic participants;
  an empty call schedule cycles, and an explicit call schedule controls the
  exact speakers without entering an LLM context.
- Unknown, duplicated-invitation, self-invited, non-participant-called,
  over-limit, and
  malformed requests fail before context assembly, model invocation,
  observations, events, or actions.
- Five participant perspectives remain holder-scoped: each context contains
  only that speaker's qualitative self-knowledge and the prior visible dialogue
  history, never another participant's private perspective or any IDs.
- A meeting action proposal still follows the resolver and rejected action
  proposals do not produce action mutation or events.
- The engine method is pure delegation; the example and `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/12a_npc_meeting_coordination-report.md`.
Report request/input validation, participant/speaking-order semantics,
perspective isolation, action-gateway evidence, public interfaces, exact files,
validation results, boundary compliance, and deferred behaviour.

## Boundary

- Touch only the stated meeting/conversation/engine files, tests, example,
  documentation, ADR, plan/prompt/report artifacts.
- Do not create persistent meetings, invitations, consent, availability,
  relationship, council, voting, or domain action systems.
- Preserve the rule: LLMs reason and propose only; the simulation validates
  and applies. Preserve the NPC information boundary for every participant and
  every turn.
