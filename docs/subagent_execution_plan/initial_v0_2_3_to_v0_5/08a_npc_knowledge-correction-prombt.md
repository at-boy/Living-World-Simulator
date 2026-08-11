# Task 08a — Correction Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Correct only Task 08a's implementation; do not commit.

## Required Corrections

1. Enforce the exact `tuple[str, ...]` contract for all three provenance
   fields. Lists, sets, other iterables, and strings must raise `TypeError`.
   Retain validation that each ID is a unique, non-empty string.
2. Make `Knowledge.metadata` recursively detached and immutable. Mutating the
   input after construction, or a nested value reachable from the record, must
   not alter the record. Preserve JSON persistence by explicitly converting
   frozen metadata to JSON-safe mutable values before serialization and
   reconstructing it safely on load.
3. Enforce the NPC information boundary at the record boundary: reject a
   `statement` or `source_description` containing any identifier supplied in
   its provenance tuples. Do not invent a fragile content filter for ordinary
   human-readable prose; the manager must continue to accept no raw
   `WorldState`, entity, evidence, event, or inspection object as input.
4. Add direct model and SQLite round-trip tests for these rules. Update the
   report with the correction and complete validation evidence.

## Allowed Files

- `src/living_world/core/knowledge.py`
- `src/living_world/repositories/sqlite_repository.py`
- `tests/test_knowledge.py`
- `tests/test_sqlite_repository.py`
- `docs/subagent_execution_plan/08a_npc_knowledge-report.md`

Run and report `make`, `make examples`, and `git diff --check`. Do not edit
other files, do not amend the plan, and do not commit. Follow
`docs/npc_information_boundary.md`.
