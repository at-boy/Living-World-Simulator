# Task 08a — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff,
and Black.

Your scope is strictly limited to executing **Task 08a — NPC knowledge**. Do
not write code outside this scope.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the complete contract in
`docs/subagent_execution_plan/08a_npc_knowledge.md`, including its
persistence amendment. Treat the task file as the authoritative specification
for the required files, interfaces, tests, documentation, and boundary.

The feature is a holder-scoped, immutable `Knowledge` record that represents
an NPC-attributed claim, not authoritative world truth. Preserve the
distinction from memory, belief, and experience. `statement` and
`source_description` are NPC-readable text only: never construct them from
raw authoritative attributes, internal IDs, evidence dumps, or privileged
events. Provenance IDs remain internal record links and must not be inserted
into the visible text.

Use manager-owned mutation only. The engine must expose the knowledge manager.
Persist and restore the complete record through the SQLite repository, while
remaining compatible with existing snapshots that do not contain `knowledge`.
Do not begin retrieval/context assembly or any LLM/prompt integration; that is
Task 09.

Before handoff:

1. Create
   `docs/subagent_execution_plan/08a_npc_knowledge-report.md`.
2. In that report state: outcome; exact files changed; public interfaces added
   or changed; knowledge/memory/belief/experience distinction; source-attribution
   and NPC-boundary evidence; SQLite/legacy-load evidence; tests and exact
   commands/results; documentation updated; boundary compliance; and blockers
   or deferred work.
3. Run and report `make`, `make examples`, and `git diff --check`.
4. Do not commit. Report back that the task is ready for orchestrator review.

Only edit files permitted by the Task 08a Context Needed and Boundary,
including the approved report artifact. Adhere to
`docs/architectural_direction.md` and `docs/npc_information_boundary.md`.
