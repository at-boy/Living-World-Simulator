# 13 — Council meetings

## Task Description

Implement councils as bounded, agenda-driven meetings called by an eligible
NPC. Invitees may attend or decline from a safe view of the caller and agenda;
every decision and any resulting action remains non-authoritative until the
standard simulation gateway validates it. Councils use Task 12a's meeting
coordination rather than owning a second dialogue scheduler.

## Context Needed

- Create: `docs/subagent_execution_plan/13_council_meetings-report.md`.
- Create: `src/living_world/cognition/council.py`, `tests/test_council.py`,
  `examples/022_council_meeting.py`,
  `examples/manual/ollama_council_meeting.py`, and
  `examples/manual/llama_cpp_council_meeting.py`.
- Edit: `src/living_world/cognition/__init__.py`,
  `src/living_world/cognition/conversation.py`,
  `src/living_world/cognition/meeting.py`, `tests/test_conversation.py`,
  `tests/test_meeting.py`,
  `src/living_world/simulation/simulation_engine.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, `docs/project_journal.md`, `docs/backlog.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`, and an ADR.
- Know: Task 12 conversation service, Task 11 action gateway, Task 05
  organization membership graph, Task 09 context boundary, and Task 12a
  meeting-request/call-order contract.

## Interface Contract

```python
@dataclass(frozen=True, slots=True)
class CouncilAgenda:
    topic: str
    action_options: tuple[ActionOption, ...]

@dataclass(frozen=True, slots=True)
class CouncilCall:
    caller_id: str
    organization_id: str
    invited_participant_ids: tuple[str, ...]
    agenda: CouncilAgenda
    max_rounds: int
    called_speaker_ids: tuple[str, ...] = ()
    participant_self_knowledge: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict
    )

@dataclass(frozen=True, slots=True)
class CouncilAttendance:
    participant_label: str
    attending: bool
    delegates_to_majority: bool

@dataclass(frozen=True, slots=True)
class CouncilResult:
    attendance: tuple[CouncilAttendance, ...]
    conversation: ConversationResult
    majority_proposal: ActionRequest | None
    resolutions: tuple[ActionResolution, ...]

class CouncilService:
    def convene(self, *, call: CouncilCall) -> CouncilResult: ...
```

- A council is an orchestration of bounded conversation rounds, not a new
  authoritative governance subsystem.
- The caller, every invitee, and each prospective attendee must be an eligible
  council member according to the engine-side organization membership graph.
  Eligibility is checked before context assembly or any model call.
- Before a meeting, every eligible invitee receives a freshly assembled,
  holder-scoped context plus only safe invitation prose: the caller display
  label and agenda topic. The invitee can propose exactly one of the offered
  `attend_council` or `decline_council` actions. These proposals are processed
  through a council attendance handler and the standard `NPCActionResolver`.
  The handler creates no world mutation or event; it returns an authoritative
  attendance selection only after engine-side eligibility validation. A missing,
  malformed, rejected, or unavailable response means the NPC does not attend.
  The LLM never receives caller/member IDs, relationship scores, attendance
  records, or another invitee's response.
- `CouncilAttendance` exposes only safe display labels and attendance booleans;
  it contains no internal IDs, rationale, cognitive record, or action result.
- A council may proceed with any non-empty attending set, including fewer than
  five NPCs. A caller remains an attendee. A `decline_council` choice means
  that NPC deliberately delegates its position to the eventual majority of
  attendees: `attending=False` and `delegates_to_majority=True`. This is a
  bounded social conclusion only; it does not itself mutate the world, alter a
  relationship, or make an agenda action succeed.
- The council records an attendee-majority conclusion only when an explicit
  vote/proposal outcome is available from the meeting's bounded dialogue. Each
  attendee's first valid agenda `ActionRequest` is one vote; candidates are
  grouped by action key, target label, and arguments (not rationale). A
  candidate needs strictly more than half of attending NPC votes; ties,
  abstentions, and no majority yield no proposal. Decliners delegate to that
  winner only after it exists and do not lower the attendee-majority threshold.
- Council dialogue collects proposals without applying them. At most one
  majority proposal is then submitted once to the ordinary resolver with the
  engine-side caller as action sponsor. An accepted handler may mutate; no
  majority can bypass validation, and no majority/failed resolution changes
  state. The caller-as-sponsor convention is limited to this v0.5 coordination
  layer and is not institutional authority.
- The service delegates to `MeetingService` using an explicit, deterministic
  call schedule and safe per-participant self-knowledge. It does not
  reimplement invitation, context, observation, or turn logic.
- Agenda actions are predeclared by the simulation. Consensus is a proposal;
  every proposed action follows the same validation/application gateway.
- Membership eligibility is checked engine-side through relationships and does
  not expose membership IDs or scores to participants.
- The standard automated example may use a small scripted attendee set to keep
  acceptance checks deterministic. The two **manual** examples use
  `OllamaCognitionClient` and `LlamaCppCognitionClient` respectively and each
  create five distinct safe NPC perspectives with an attendance-friendly
  interest in the agenda, so an operator can run a substantial five-NPC
  discussion. They must remain opt-in, require a local loopback model server,
  make no network call during pytest/`make`, and document exact launch/run
  commands and expected local-model limitations. They are demonstrations, not
  deterministic acceptance tests; an actual model may still decline.

## Test Criteria

- Ineligible callers/invitees are rejected before context assembly; invitation
  responses with malformed or unoffered attendance actions cannot create
  attendance, conversation observations, actions, or events.
- Fewer than five attendees may still meet. A declined invitation is shown
  only as safe delegation-to-majority status, while each attendee receives only
  its own qualitative perspective and visible dialogue history. The call order
  is deterministic for the attending set.
- Participants only receive allowed agenda text and filtered dialogue/context.
- A consensus does not change state without an accepted handler result.
- A declined invitation delegates only to an attendee-majority social
  conclusion; it does not count as an engine-authoritative vote or action.
- Round limits and action-resolution order are deterministic; example and
  `make` pass.

## Orchestrator Report

Create `docs/subagent_execution_plan/13_council_meetings-report.md`. Report
membership-eligibility checks, agenda/context filtering, consensus-versus-action
validation evidence, and validation results.

## Boundary

- Touch only stated council files, integration, tests, automatic/manual
  examples, ADR, and docs.
- The approved report artifact is also allowed.
- Do not create a special `Council` world primitive or direct state mutation.
- Preserve all conversation and action-boundary guarantees.
- Do not implement faction formation, organized opposition, political
  legitimacy, settlement secession, or migration. Those require their own
  social, relationship, resource, and settlement-authority milestone.
