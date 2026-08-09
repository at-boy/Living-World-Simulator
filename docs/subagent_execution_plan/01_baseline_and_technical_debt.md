# 01 — Baseline and technical-debt reconciliation

## Task Description

Audit the v0.2.3 baseline, complete only verifiable technical-debt cleanup,
and make the example runner reliably validate all executable documentation.

## Context Needed

- Create: `docs/subagent_execution_plan/01_baseline_and_technical_debt-report.md`.
- Edit: `Makefile`, `docs/technical_debt.md`, `docs/core_model.md`,
  `docs/engine_glossary.md`, `CHANGELOG.md`, `docs/project_journal.md`.
- Create: `tests/test_examples_runner.py` only if the example runner needs a
  testable discovery helper; otherwise no test file is required.
- Inspect: all `examples/*.py`, `src/living_world/core/entity.py`,
  `src/living_world/managers/entity_manager.py`,
  `src/living_world/managers/relationship_manager.py`.
- Know: `Entity`, `Relationship`, `WorldState`, `EntityManager`, and
  `RelationshipManager`.  The version stays `0.2.3` in `VERSION` and
  `pyproject.toml` until the final release task. Python support remains
  `>=3.11` and Black stays `py311`.

## Interface Contract

- `make examples` discovers and executes every numbered top-level example in
  lexical/numeric order, reports the file being run, and stops on failure.
- Examples create locations as `Entity` instances through
  `EntityManager.create()`; no `Location` domain class or location-specific
  collection may be introduced.
- Before editing technical debt, audit each claimed debt item. Mark an item
  resolved only when its stated resolution criteria are demonstrably true.
  `EventManager` and relationship lifecycle are already described as resolved
  and must not be reimplemented.

## Test Criteria

- `make examples` runs every eligible example exactly once and fails when an
  example exits unsuccessfully.
- Existing entity and relationship manager tests still pass.
- `make` passes under the local Python 3.13.5 runtime.

## Orchestrator Report

Create `docs/subagent_execution_plan/01_baseline_and_technical_debt-report.md`.
Report the audit evidence for every debt item reviewed, runner validation,
changed files, validation results, and any repository-wide blocker.

## Boundary

- Touch only the listed files, the approved report artifact, and a single
  narrowly-scoped runner test if necessary.
- Ignore repository persistence, YAML loading, settlement behavior, NPC
  cognition, and LLM code.
- Adhere to `docs/development_rules.md`, `docs/development_workflow.md`, and
  the resolution wording already present in `docs/technical_debt.md`.
