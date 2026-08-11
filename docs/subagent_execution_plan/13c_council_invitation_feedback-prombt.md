# Task 13c — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black.

Your scope is strictly limited to executing **Task 13c — Council
invitation-feedback trace**. Do not write code outside this scope.

Here is the Codebase Standard you must follow:

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

Read and execute the complete task specification in
`docs/subagent_execution_plan/13c_council_invitation_feedback.md`. That
specification is authoritative, including its Context Needed, Interface
Contract, Test Criteria, Orchestrator Report, and Boundary sections.

Implement only the required safe ephemeral council-feedback feature, tests,
manual output, and docs. In particular, do not expose raw provider output or
errors, do not persist feedback, and do not change attendance-resolution
semantics to create an artificial status. Before handoff create the required
report, run `make`, `make examples`, and `git diff --check`, and do not commit.
