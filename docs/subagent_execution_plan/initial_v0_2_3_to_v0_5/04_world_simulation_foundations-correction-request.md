# Task 04 — Correction Request Before Commit

Task 04's scheduler/system migration is now explicitly authorized by the
amended task plan. The implementation is functionally validated, but its
report and an unnecessary Makefile change must be corrected before commit.

## Required Corrections

1. Revert the comment-only change in `Makefile`.

   Task 04 does not need to modify example discovery. Restore the existing
   generic `EXAMPLES` comment; do not alter the example-discovery behavior.

2. Update
   `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`
   with the required handoff sections:

   - **Exact Files Changed**, including every scheduler/system-protocol
     migration file now authorized by the amended task;
   - **Boundary Compliance**, stating that the migration is authorized by the
     amended Task 04 boundary and that no location-specific runtime model was
     added;
   - **Blockers and Deferred Work**, with `None` only after validation passes.

3. Update the report's validation section to include the exact successful
   `make` result, in addition to the pytest and example counts already stated.

## Validation Required Before Handoff

Run and report the outcome of:

```bash
make
make examples
git diff --check
```

## Boundary

Only edit:

- `Makefile` — restore the pre-existing generic comment only;
- `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`.

Do not change the validated Task 04 implementation or tests during this
correction. Do not commit until all validation commands pass.
