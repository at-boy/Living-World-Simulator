# Task 04 — Final Correction Before Commit

Task 04's implementation and validation are complete. One out-of-scope
Makefile comment change remains and must be reverted exactly before commit.

## Required Corrections

1. In `Makefile`, restore this exact pre-Task-04 comment:

   ```make
   # Every numbered top-level example, including 013_world_inspection.py, is executable documentation.
   ```

   Do not change the `EXAMPLES` assignment or any Make target.

2. In
   `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`,
   remove the `Makefile` entry from **Exact Files Changed**. The restored
   Makefile must not be part of the Task 04 commit.

## Validation Required Before Handoff

Run and report:

```bash
make
make examples
git diff --check
git diff -- Makefile
```

`git diff -- Makefile` must produce no output before the Task 04 commit.

## Boundary

Only edit these two files:

- `Makefile`
- `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`

Do not modify implementation code, tests, examples, task-plan files, or any
other documentation. Do not commit until all validation commands pass.
