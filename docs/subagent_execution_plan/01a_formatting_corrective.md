# 01a — Formatting corrective task

## Task Description

Restore the repository-wide Black formatting gate by applying Black's required
formatting to the single pre-existing out-of-scope file that blocked Task 1.

## Context Needed

- Edit: `src/living_world/perception/llm_perception_engine.py`.
- Create: `docs/subagent_execution_plan/01a_formatting_corrective-report.md`.
- Know: this is a formatting-only correction. The module's public classes,
  functions, type hints, control flow, behavior, and tests are not being
  redesigned.

## Interface Contract

- Preserve every existing public and private interface and runtime behavior in
  `llm_perception_engine.py`.
- The file must be formatted exactly as required by the repository's installed
  Black version. No refactor, test change, documentation change, or adjacent
  source edit is permitted.

## Test Criteria

- `./.venv/bin/black --check src tests` passes.
- `make check` passes.
- `make examples` passes.
- Run `make` only after the checks above confirm it will not modify any file
  outside this task's allowed source file.

## Orchestrator Report

Create `docs/subagent_execution_plan/01a_formatting_corrective-report.md`.
State the exact formatting command used, confirm behavior-preserving scope,
list validation results, and record any blocker.

## Boundary

- Allowed: exactly `src/living_world/perception/llm_perception_engine.py` and
  `docs/subagent_execution_plan/01a_formatting_corrective-report.md`.
- Ignore every other source, test, example, configuration, and documentation
  file.
- Adhere to the formatting-only interface contract and the standard
  development rules.
