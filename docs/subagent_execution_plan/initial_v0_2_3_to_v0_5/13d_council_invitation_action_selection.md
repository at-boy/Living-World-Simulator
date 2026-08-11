# 13d — Council invitation action-selection guidance

## Task Description

Strengthen the engine-provided, NPC-safe council invitation so a local cognition
model is explicitly instructed to choose exactly one of the two offered
attendance actions. This corrects the observed manual-example failure mode in
which a model supplies a relevant statement but returns no `action_request`,
leaving every invitee as `no_selection`. The instruction increases clarity; it
must never manufacture attendance, coerce a model response, or alter normal
action resolution.

## Context Needed

- Create: `docs/subagent_execution_plan/13d_council_invitation_action_selection-report.md`
  and `tests/test_council_invitation_action_selection.py`.
- Edit: `src/living_world/cognition/council.py`,
  `tests/test_council.py`, `docs/local_llm_setup.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Know: Task 13 `CouncilService.convene`, Task 10 structured local cognition
  request format, Task 13c invitation feedback, `NPCContextAssembler`, and
  `NPCInformationBoundary`.

## Interface Contract

```python
class CouncilService:
    def convene(self, *, call: CouncilCall) -> CouncilResult: ...
```

- No public function, dataclass, protocol, cognition-client schema, or action
  resolver interface changes in this task.
- Every invitation context supplied to an invitee includes safe prose that
  explicitly says the NPC must return exactly one **offered attendance action**
  in `action_request`. It explicitly says a statement by itself is not an
  attendance selection, and requires a short NPC-visible reason in that action
  request's `rationale` field. It must not repeat action-key literals in
  validated prose, because an action key can contain an internal identifier.
- The structured action vocabulary separately provides the offered action keys
  to the cognition client; the instruction contains only safe caller/agenda
  prose and stable response-field concepts. It must pass
  `NPCContextAssembler.validate_conversation_prose` before context assembly.
- A model that still supplies no action request remains `NO_SELECTION` and
  does not attend. A malformed/unavailable response remains `UNAVAILABLE`.
  The engine must not infer an action from prose, retry automatically, or
  fabricate a decision.
- A selected attendance action's rationale is available only as the already
  filtered `CouncilInvitationFeedback.rationale` for operator debugging. It is
  not public world state and must not be persisted, emitted as an event,
  supplied to another NPC, or used as authoritative evidence of private mental
  state.
- `CouncilAttendance`, `CouncilInvitationFeedback`, meeting scheduling,
  authority, events, persistence, and information exposure retain their Task
  13/13c semantics.

## Test Criteria

- A capturing scripted client proves every invitee receives the exact safe
  action-selection guidance in its `NPCContext.conversation_history`; it must
  contain no entity IDs, action-key literals, raw attributes, relationship
  values, or authoritative numbers.
- A scripted local-client decision with a statement plus
  `attend_council`/`decline_council` action continues through the ordinary
  resolver to ATTENDING/DECLINED feedback, preserving the safe operator-only
  rationale and normal downstream meeting behaviour.
- A scripted decision with statement and `action_request=None` remains
  `NO_SELECTION` and non-attending; its prose is not interpreted as attendance.
- Existing council and information-boundary tests pass. `make`, `make
  examples`, and `git diff --check` pass.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13d_council_invitation_action_selection-report.md`.
Report the exact safe instruction, no-inference evidence, tests/commands and
results, files changed, boundary compliance, and known limitation: local model
compliance remains probabilistic despite explicit guidance.

## Boundary

- Touch only the listed council/test/docs/report files.
- Do not modify local cognition clients, response schema, `DecisionEngine`,
  action resolution, invitation-feedback types, manual examples, persistence,
  HTTP APIs, Makefile, or task plans.
- Do not add retries, default attendance, text-to-action heuristics, hidden
  prompt data, raw provider logging, or any world mutation/event.
