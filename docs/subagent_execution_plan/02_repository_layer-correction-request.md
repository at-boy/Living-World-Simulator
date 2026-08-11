# Task 02 — Correction Request Before Commit

Task 02 is not ready to commit. The repository-layer implementation remains
within its allowed file boundary, but its report incorrectly states that
validation passed and that there are no blockers.

## Required Corrections

1. Fix the five Ruff `TRY004` violations in
   `src/living_world/repositories/sqlite_repository.py`.

   The following helpers raise `ValueError` when an input has the wrong type.
   Change those type-mismatch failures to `TypeError`, while preserving the
   existing repository-boundary behavior:

   - `_records()`
   - `_list()`
   - `_string()`
   - `_integer()`
   - `_number()`

2. Add a pytest case in `tests/test_sqlite_repository.py` for an unsupported
   persisted `schema_version`.

   The implementation claims to reject unsupported versions, and the report
   says this behavior is covered, but the current test suite does not verify
   it. The test must assert `RepositoryLoadError` and confirm no partial world
   state is returned.

3. Update
   `docs/subagent_execution_plan/02_repository_layer-report.md`.

   The report must include:

   - the exact files changed;
   - public interfaces added or changed;
   - the unsupported-schema test result;
   - exact validation commands and results;
   - boundary compliance; and
   - blockers, if any.

   Do not state “None” under blockers until all required validation succeeds.

## Validation Required Before Handoff

Run and report the outcome of:

```bash
make
make examples
git diff --check
```

`make` previously ran Ruff's auto-fix phase and made two safe formatting/import
adjustments before stopping. Those changes are within Task 02's permitted
SQLite-file scope and may remain as part of the correction.

## Boundary

Only edit files already allowed by Task 02:

- `src/living_world/repositories/sqlite_repository.py`
- `tests/test_sqlite_repository.py`
- `docs/subagent_execution_plan/02_repository_layer-report.md`

Do not commit until all validation commands pass.
