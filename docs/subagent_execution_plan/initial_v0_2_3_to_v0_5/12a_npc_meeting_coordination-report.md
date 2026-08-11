# Task 12a — NPC Meeting Coordination Report

## Delivered

Implemented bounded, ephemeral NPC meeting coordination. A `MeetingRequest`
keeps requester, invitee, and optional call-schedule identifiers engine-side;
`MeetingService` validates the requester-first participant set and delegates to
the existing `ConversationService`. No meeting, invitation, consent,
availability, relationship, event, voting, or policy record is created.

## Public Interfaces

```python
@dataclass(frozen=True, slots=True)
class MeetingRequest:
    requester_id: str
    invitee_ids: tuple[str, ...]
    topic: str
    max_turns: int
    called_speaker_ids: tuple[str, ...] = ()
    participant_self_knowledge: Mapping[str, tuple[str, ...]] = ...

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

class SimulationEngine:
    def conduct_npc_meeting(
        self,
        *,
        service: MeetingService,
        request: MeetingRequest,
    ) -> ConversationResult: ...
```

`MeetingRequest` validates primitive shapes and replaces the supplied
perspective mapping with an owned `MappingProxyType` copy. The service checks
known membership, distinct invitees, and non-self-invitation before delegating.

## Semantics and Boundary Evidence

- Effective participant order is requester first, then invitees in supplied
  order. With no call schedule, turns remain cyclic. A supplied schedule is
  exact, may repeat a participant, is bounded by `max_turns`, and is never put
  in a context, transcript, or model request.
- Perspective mapping keys must identify effective participants. Each value is
  a non-empty tuple that is validated as NPC-visible prose before any context,
  model invocation, observation, event, or action side effect.
- `tests/test_meeting.py` uses five distinct perspectives and a repeated
  speaker schedule. Each recorded `NPCContext` receives only its own expected
  perspective tuple, never another participant's tuple or an internal ID.
- Invalid self/duplicate/unknown invitations, invalid schedules, unknown
  perspective owners, and unsafe perspective prose fail with no model calls,
  observations, or events.
- Action proposals remain routed through `NPCActionResolver`; the rejected
  meeting action test confirms no mutation or event occurs.

## Files Changed

- `src/living_world/cognition/meeting.py`
- `src/living_world/cognition/conversation.py`
- `src/living_world/cognition/__init__.py`
- `src/living_world/simulation/simulation_engine.py`
- `tests/test_meeting.py`
- `tests/test_conversation.py`
- `examples/021_npc_meeting.py`
- `docs/adr/ADR-0012-npc-meeting-coordination.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/subagent_execution_plan/12a_npc_meeting_coordination.md`
- `docs/subagent_execution_plan/12a_npc_meeting_coordination-prombt.md`
- `docs/subagent_execution_plan/12a_npc_meeting_coordination-report.md`

## Validation

All required commands passed:

```text
make
  Ruff: pass
  Black: pass
  pytest: 294 passed
  numbered examples: 001 through 021 passed

make examples
  numbered examples: 001 through 021 passed

git diff --check
  pass
```

## Deferred Behaviour

This task intentionally does not implement persistent meetings, invitation
delivery/acceptance, consent, availability, attendance, relationships,
governance, council agendas, voting, decisions, or action handlers. Those
remain future explicit simulation systems.
