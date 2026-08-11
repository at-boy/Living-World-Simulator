# 13c — Council invitation-feedback trace

## Task Description

Make a single council result explain, safely and readably, what each invited
NPC proposed in response to the invitation: its attendance outcome, any
NPC-visible statement, and its offered attendance rationale. The trace is
ephemeral diagnostic/interaction output; it is not a governance record,
cognitive record, event, or source of engine authority.

## Context Needed

- Create: `docs/subagent_execution_plan/13c_council_invitation_feedback-report.md`
  and `tests/test_council_invitation_feedback.py`.
- Edit: `src/living_world/cognition/council.py`,
  `src/living_world/cognition/__init__.py`, `tests/test_council.py`,
  `tests/test_manual_council_examples.py`,
  `examples/manual/ollama_council_meeting.py`,
  `examples/manual/llama_cpp_council_meeting.py`, `docs/local_llm_setup.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Know: `CouncilService`, `CouncilResult`, `CouncilAttendance`,
  `NPCDecision`, `ActionRequest`, `NPCContextAssembler.validate_conversation_prose`,
  `NPCInformationBoundary`, and the Task 13b formatting helpers.

## Interface Contract

```python
class CouncilInvitationStatus(StrEnum):
    ATTENDING = "attending"
    DECLINED = "declined"
    NO_SELECTION = "no_selection"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True, slots=True)
class CouncilInvitationFeedback:
    participant_label: str
    status: CouncilInvitationStatus
    spoken_text: str | None
    rationale: str | None

@dataclass(frozen=True, slots=True)
class CouncilResult:
    attendance: tuple[CouncilAttendance, ...]
    conversation: ConversationResult
    majority_proposal: ActionRequest | None
    resolutions: tuple[ActionResolution, ...]
    invitation_feedback: tuple[CouncilInvitationFeedback, ...] = ()
```

- `CouncilResult.invitation_feedback` contains one record per invitee in the
  `CouncilCall` order and never contains a caller record or internal ID.
- `ATTENDING` means the offered `attend_council` selection was accepted;
  `DECLINED` means `decline_council` was accepted; `NO_SELECTION` means a
  well-formed decision did not offer an attendance action; and `UNAVAILABLE`
  means the provider did not yield a usable decision. Existing council
  pre-validation and the offered attendance vocabulary make a resolver-rejected
  invitation unreachable in v0.5. Do not introduce a new rejection rule merely
  to create a diagnostic status.
- The feedback statement is `NPCDecision.spoken_text`; the rationale is the
  offered `ActionRequest.rationale`. Both may be `None`. Before either becomes
  feedback or is rendered, it must pass
  `NPCContextAssembler.validate_conversation_prose`. If it fails, suppress that
  field and render only a generic safe indication that no displayable text was
  supplied. Do not include provider exception text or raw provider payloads.
- Feedback exposes an NPC's submitted proposal only. It neither changes the
  attendance decision nor makes a claim about the NPC's true private mental
  state. It is not persisted in `WorldState`, used in retrieval/context,
  written as an observation/event/memory, or sent to another NPC.
- Each Task 13b formatter retains its public
  `format_council_result(result: CouncilResult) -> str` signature and prints an
  **Invitation feedback** section after attendance. For every invitee it shows
  the safe label, status, any safe statement, and any safe rationale; it must
  clearly distinguish a declined response from no usable response.

## Test Criteria

- Council tests prove deterministic feedback order and all four statuses,
  including an attendee/decliner statement and rationale, a no-selection
  statement, and unavailable provider output.
- Tests prove a statement/rationale containing an internal identifier or an
  authoritative numeric value is suppressed from the feedback and manual
  rendering, while no raw error text is exposed.
- Manual formatter tests prove all invitees have feedback shown without a
  provider call and that the caller does not have invitation feedback.
- Existing attendance, conversation, majority, action-gateway, and NPC
  information-boundary tests remain valid. `make`, `make examples`, and
  `git diff --check` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/13c_council_invitation_feedback-report.md`.
Report the new public types/result field, feedback status semantics, prose
filtering evidence, manual output evidence, tests/commands/results, files
changed, boundary compliance, and blockers/deferred work.

## Boundary

- Touch only the listed council, export, tests, manual examples, docs, and
  approved report artifact.
- Do not modify local cognition clients, `NPCInformationBoundary`, action
  resolution, meeting/conversation scheduling, persistence/repository code,
  HTTP endpoints, or the Makefile.
- Do not persist feedback, create facts, expose raw errors/responses/internal
  IDs/numeric engine data, or allow an invitation response to bypass the
  standard attendance/action resolver.
