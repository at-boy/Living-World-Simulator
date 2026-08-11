# Task 09a — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Your scope is strictly limited to **Task 09a — Perception-boundary
enforcement**. Do not write code outside this task.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the complete amended contract in
`docs/subagent_execution_plan/09a_perception_boundary_enforcement.md`. Read
`docs/npc_information_boundary.md` in full before implementation.

The amended optional `PerceptionContext` parameter is intentional and solves
the information-boundary ownership rule:

- Both perception engines validate produced observations with their engine-only
  context before returning. This validation must recurse through protected
  subject attributes and observer capabilities, and reject their exact numeric
  values and IDs in visible description text.
- `NPCContextAssembler` must call the same boundary with only the
  `Observation` and **no** `PerceptionContext`. It must never read evidence or
  metadata. This second validation guards direct/legacy observations without
  allowing the assembler to hold or recover engine data.
- Validate only actual unsafe constructs: internal IDs, exact protected
  numbers when context is available, raw attribute notation such as `wood=120`,
  evidence/metadata terminology, hidden-state wording, and engine-object
  names. Do not blacklist ordinary qualitative prose just because it uses an
  attribute word such as “wood”, “health”, or “mature”.
- Preserve the LLM engine’s deterministic fallback. Unsafe LLM output must
  fall back, and unsafe fallback output must fail closed with the existing
  dedicated fallback error.
- Perception-provider request payloads may contain curated engine data; they
  must remain distinct from `NPCContext` and must not be used by the cognition
  path. Do not begin Task 10 cognition-client work.

Create the required tests, docs updates, and
`docs/subagent_execution_plan/09a_perception_boundary_enforcement-report.md`.
The report must state outcome; exact files changed; public interfaces; unsafe
cases and fallback evidence; evidence-retention/context-exclusion proof;
request-context distinction; command results; documentation; boundary
compliance; blockers/deferred work.

Run `make`, `make examples`, and `git diff --check`. Do not commit. Touch only
the files allowed by Task 09a, including its report artifact. Do not modify
domain cognition/action meanings, persistence, or HTTP inspection.
