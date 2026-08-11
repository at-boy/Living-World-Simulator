# Task 12a — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Your scope is strictly limited to **Task 12a — NPC meeting coordination
and directed dialogue**. Do not write code outside this task.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the complete contract in
`docs/subagent_execution_plan/12a_npc_meeting_coordination.md`.

`MeetingRequest` is an engine/service-side value object. It must strictly
validate primitive shape and detached/frozen mapping ownership in
`__post_init__`; the service must validate all world-dependent membership and
all perspective prose through the existing information boundary before any
context/model/action/observation side effect. Never include requester,
invitee, called-speaker, or perspective-map identifiers in an `NPCContext`,
serialized LLM request, visible turn, or result.

Extend `ConversationService.conduct` exactly as planned. With an empty
`called_speaker_ids`, retain the existing cyclic order and `max_turns` model
calls. With a supplied schedule, make exactly one model call for each listed
speaker, in its listed order, only if its length is at most `max_turns`; repeat
speakers are valid. The schedule itself is engine-only. Pass only a speaker's
own validated perspective tuple through `NPCContext.self_knowledge`; do not
merge or expose other participants' perspective values. Topic/history and
recipient observations must retain every Task 12 safety property.

`MeetingService` turns requester plus invitees into the effective ordered
participants and delegates to `ConversationService`; it owns no persistence or
social policy. `SimulationEngine.conduct_npc_meeting` is a thin delegation
method only. Do not create meeting entities, invitation delivery/acceptance,
consent/availability records, relationships, events, voting, councils, or
domain action handlers.

Tests must prove five differently profiled participants receive only their own
private qualitative self-knowledge; explicit calling controls speakers without
leakage; empty schedules cycle; malformed requests have no calls/writes; and
rejected action proposals remain non-mutating. Use fake/scripted cognition in
pytest and the automatic example. The numbered-example Makefile wildcard
already discovers example 021—do not edit the Makefile.

Create `docs/subagent_execution_plan/12a_npc_meeting_coordination-report.md`
with exact files changed, public interfaces, request/schedule semantics,
perspective isolation evidence, action-boundary evidence, validation output,
docs, boundary compliance, and deferred work.

Run `make`, `make examples`, and `git diff --check`. Do not commit. Only edit
the files named in Task 12a's Context Needed/Boundary, including this plan,
saved prompt, report, required ADR, and stated docs. Do not edit Task 13 or
any later plan.
