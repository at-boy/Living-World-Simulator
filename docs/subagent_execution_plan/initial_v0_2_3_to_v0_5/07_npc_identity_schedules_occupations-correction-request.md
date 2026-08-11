# Task 07 — Validation Correction Before Commit

Task 07 is not ready to commit. Its schedule behavior and information boundary
are correct, but direct construction of its new value objects is not fully
validated:

- `NPCIdentity(capability_descriptions="experienced woodcutter")` is accepted
  as a tuple of characters rather than rejected as a non-tuple input.
- Non-string `NPCIdentity.name`, `NPCIdentity.description`,
  `Occupation.title`, and `Occupation.description` fail incidentally when
  `.strip()` is called rather than producing deliberate type validation.

## Required Corrections

1. In `src/living_world/npc/identity.py`, validate direct-construction field
   types before invoking string operations:

   - `name` and `description` must be `str`.
   - `capability_descriptions` must be `tuple[str, ...]`; a list, string, or
     non-string element raises `TypeError`.
   - Preserve conversion of valid input to its canonical tuple and the existing
     JSON attribute form.

2. In `src/living_world/npc/occupation.py`, validate that `title` and
   `description` are `str` before invoking string operations.

3. Add focused direct-construction pytest cases in
   `tests/test_npc_identity.py` for the invalid values above. Assert
   `TypeError` and preserve all existing round-trip behavior.

4. Update
   `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`
   with the corrected validation evidence, exact files, commands/results, and
   boundary compliance. Do not report no blockers until validation passes.

## Validation Required Before Handoff

```bash
make
make examples
git diff --check
```

## Boundary

Only edit:

- `src/living_world/npc/identity.py`
- `src/living_world/npc/occupation.py`
- `tests/test_npc_identity.py`
- `docs/subagent_execution_plan/07_npc_identity_schedules_occupations-report.md`

Do not change schedule semantics, engine registration, any NPC information
boundary, or other task files. Do not commit.
