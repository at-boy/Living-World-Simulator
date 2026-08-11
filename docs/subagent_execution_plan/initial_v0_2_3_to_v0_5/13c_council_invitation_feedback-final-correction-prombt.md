# Task 13c — Final Correction Prompt: Documentation Boundary Accuracy

You are an isolated Subagent developer. Correct Task 13c documentation only;
do not alter Python code, tests, plan files, or commit.

## Required Corrections

1. In `docs/core_model.md`, replace the inaccurate phrase
   “NPC-visible invitation-feedback trace.” It is an **operator-visible**
   ephemeral diagnostic result. The feedback is explicitly not supplied to
   another NPC, retrieval, context assembly, or cognition.
2. In
   `docs/subagent_execution_plan/13c_council_invitation_feedback-report.md`,
   remove the duplicate `make examples` and `git diff --check` validation
   lines. Retain one accurate result for each command.
3. Update the report's boundary evidence to explicitly say the trace is
   operator-visible and is not forwarded to NPCs.

## Boundary

Only edit:

- `docs/core_model.md`
- `docs/subagent_execution_plan/13c_council_invitation_feedback-report.md`

Run `git diff --check` and report its result. Do not commit.
