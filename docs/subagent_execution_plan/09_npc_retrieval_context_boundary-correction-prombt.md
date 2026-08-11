# Task 09 — Correction Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Correct only the missing Task 09 test evidence below; do not commit.

## Required Correction

The Task 09 contract expressly requires tests showing that the completed
`NPCInformationBoundary` rejects a raw `WorldState` and a raw skill number.
The implementation appears to enforce both, but the submitted tests do not
prove them directly.

Add focused tests in `tests/test_npc_information_boundary.py` that use an
otherwise valid `NPCContext` and assert the boundary rejects:

1. a `WorldState` object substituted into an NPC-facing prose field; and
2. a raw numeric skill value (for example, a value from an entity's
   authoritative `attributes["skills"]`) appearing in NPC-facing text.

Do not weaken the existing behavior or add a word blacklist. Update
`docs/subagent_execution_plan/09_npc_retrieval_context_boundary-report.md` to
state the new explicit evidence and the post-correction command results.

## Allowed Files

- `tests/test_npc_information_boundary.py`
- `docs/subagent_execution_plan/09_npc_retrieval_context_boundary-report.md`

Run and report `make`, `make examples`, and `git diff --check`. Do not edit
any other file and do not commit.
