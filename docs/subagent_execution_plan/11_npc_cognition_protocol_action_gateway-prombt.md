# Task 11 — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Your scope is strictly limited to **Task 11 — NPC Cognition Protocol
and action gateway**. Do not write code outside this task.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the complete, amended contract in
`docs/subagent_execution_plan/11_npc_cognition_protocol_action_gateway.md`.

Preserve the authority boundary exactly:

- `DecisionEngine` accepts an already filtered `NPCContext` and offered
  `ActionOption` vocabulary and returns only an untrusted `NPCDecision`.
  It must perform its own offered-key/target validation even if a fake client
  directly constructs a decision and therefore bypasses Task 10's JSON parser.
- The LLM has no actor ID, `WorldState`, manager, event, result, or success
  interface. Do not infer semantic success from `spoken_text`; the structured
  public decision schema simply contains no authoritative result field.
- `NPCActionResolver` validates a request against the offered vocabulary,
  selects a supporting handler, calls `validate()` before `apply()`, and
  returns a rejected `ActionResolution` without state mutation/event recording
  for untrusted or unsupported input.
- The gateway must have no default domain handler and must not create generic
  domain events. A test-only stub handler may mutate exclusively through an
  injected existing manager and, after successful validation, record exactly
  one event through `EventManager`.
- A handler must not apply after its own rejected validation, and may not return
  a rejected result from `apply()`. Treat either as a handler-contract error;
  never turn it into an applied action.
- The new `SimulationEngine.resolve_npc_action` is only a thin, engine-owned
  delegation path. It must not pass its `actor_id` to cognition/LLM code.

Use frozen slots dataclasses for the public action-resolution result. Validate
all public inputs strictly. Existing `ActionOption`/`ActionRequest` protections
for internal record-ID prose remain in force; add gateway tests showing IDs,
unknown keys, undeclared targets, and malformed/nonconforming requests cannot
mutate state.

Create the approved report artifact
`docs/subagent_execution_plan/11_npc_cognition_protocol_action_gateway-report.md`.
It must describe exact files changed; public interfaces; proposal validation;
rejected-action non-mutation evidence; accepted handler/event evidence; the
authority boundary; validation commands/results; documentation; boundary
compliance; and blockers/deferred work.

Run `make`, `make examples`, and `git diff --check`. Do not commit. Only edit
the files explicitly allowed by Task 11, including its plan/prompt/report,
required ADR, and stated documentation files. Do not edit Task 10 clients,
repositories, HTTP inspection, perception, or introduce domain action rules.
