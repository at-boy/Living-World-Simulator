# Task 03 — Correction Request Before Commit

Task 03 is not ready to commit because it changes the project-wide Python
compatibility contract contrary to the agreed baseline.

## Required Corrections

1. In `pyproject.toml`, restore the existing support policy:

   ```toml
   requires-python = ">=3.11"

   [tool.black]
   target-version = ["py311"]
   ```

   Keep `PyYAML` as a runtime dependency; it is required by the YAML loader.
   Python 3.13.5 is the local validation runtime, not the minimum supported
   version and not a reason to change Black's compatibility target.

2. Do not change Task 02's `sqlite_repository.py` to satisfy Ruff `UP047`.
   That warning is introduced only because Task 03 changed the inferred target
   Python version to 3.13. Restoring the agreed 3.11 project target is the
   correct fix and keeps this task within scope.

3. Update
   `docs/subagent_execution_plan/03_yaml_world_definition_loader-report.md`
   to state the restored Python compatibility policy and report the complete,
   successful validation results. The report must not present an unresolved
   lint blocker as an external pre-existing issue when this task introduced it.

## Validation Required Before Handoff

Run and report the outcome of:

```bash
make
make examples
git diff --check
```

## Boundary

Only edit the Task 03-approved files required above:

- `pyproject.toml`
- `docs/subagent_execution_plan/03_yaml_world_definition_loader-report.md`

Do not alter any Task 02 repository source file or any unrelated project
configuration. Do not commit until all validation commands pass.
