# Task 12 — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Your scope is strictly limited to **Task 12 — NPC conversations**. Do
not write code outside this task.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the complete amended contract in
`docs/subagent_execution_plan/12_npc_conversations.md`.

Conversation dialogue is NPC-readable prose, not a second route to
authoritative state. Extend `NPCContext` and its assembler with the required
safe `conversation_history` projection, validate it through
`NPCInformationBoundary`, and serialize it in Task 10's local-LLM request
format. The only history supplied to a model is the topic preamble and earlier
visible turn prose. It must contain no participant/entity/observation IDs,
transcript object, evidence, metadata, raw attributes, numeric engine facts,
private cognition, or action result.

`ConversationService` must receive all dependencies through its constructor.
It validates participant IDs, topic, turn bound, and offered actions before
side effects. Its deterministic speaker order is the supplied participant tuple
cycled for at most `max_turns` model calls. For each turn it assembles a fresh,
boundary-validated context for that speaker; calls `DecisionEngine`; validates
the returned spoken prose before recording it; records the utterance as an
observation for every other participant with empty evidence/metadata; and only
then makes that visible prose available in later turn contexts. Do not record
or infer a turn for a decision with no spoken text.

An action proposal is still untrusted. Send it to the injected
`NPCActionResolver` with the service-internal actor ID only; append its
authoritative resolution to the result. Never expose that actor ID or any
resolution to the LLM. The conversation service itself owns no manager mutation
other than recipient observations and has no domain action handler, event,
memory, belief, experience, relationship, council, or governance behaviour.

Write focused tests for context/history serialization and validation, private
cognition isolation, recipient observation shape, rejected action
non-mutation, deterministic ordering, zero/bad bounds and bad participants
with no calls/writes, plus engine delegation. Add example 020; do not edit the
Makefile because its numbered-example wildcard already discovers it.

Create `docs/subagent_execution_plan/12_npc_conversations-report.md`, covering
exact files changed; public interfaces; context/history filtering; recipient
observation evidence; private-cognition isolation; action-resolution evidence;
validation commands/results; documentation; boundary compliance; and blockers.

Run `make`, `make examples`, and `git diff --check`. Do not commit. Only edit
the explicit Task 12 boundary, including its plan, saved prompt, report, and
ADR. Do not alter resolver/client action authority or add council policy.
