# Task 10 — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Your scope is strictly limited to **Task 10 — Local LLM cognition
client**. Do not write code outside this task.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the full amended contract in
`docs/subagent_execution_plan/10_local_llm_cognition_client.md`. Reuse,
without editing, `perception/local_llm_http.py` and its loopback URL
validation/transport protocol.

The cognition clients receive only completed `NPCContext` and offered
`ActionOption` vocabulary. They never receive `WorldState`, entities,
observations, evidence, metadata, provenance, raw attributes, IDs, or
numerical capabilities. Their request schema must serialize only the public
dataclass fields of that safe context and offered action values.

Implement strict frozen value objects and strict structured JSON parsing:

- `action_request` in a provider response is either `null` or exactly the
  public action-request schema; reject unknown fields and malformed types.
- Require an action key to be one of the options offered to this call. Where
  an option has target labels, require the response target to be one of them;
  where it has none, require a null target. This is vocabulary validation, not
  simulation validation.
- The output remains untrusted and must never report an authoritative success
  result. Do not add any manager call, event, mutation, tool invocation, or
  action application. Task 11 owns that.
- Make Ollama and llama.cpp loopback-only HTTP adapters following the existing
  perception adapters’ endpoint/request shapes and translated errors. Invalid
  JSON/schema/network output must raise the new dedicated cognition-client
  errors.

Write all required tests, including prompt-boundary assertions, client
round-trip/error tests, non-loopback rejection, and absence of side effects.
Update local LLM docs and required project docs. Create
`docs/subagent_execution_plan/10_local_llm_cognition_client-report.md` with
outcome; exact files; interfaces; request/response contracts; loopback and
boundary evidence; errors; test/command results; docs; boundary compliance;
blockers/deferred work.

Run `make`, `make examples`, and `git diff --check`. Do not commit. Only edit
the files allowed by Task 10, including its approved report artifact. Do not
modify existing perception clients or action application code.
