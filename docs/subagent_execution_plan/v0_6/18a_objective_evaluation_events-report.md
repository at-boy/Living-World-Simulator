# Task 18a — Objective evaluation and events report

## Delivered contract

Task 18a adds a deterministic final simulation system and closed typed
criterion-evaluator registry. Resource minimum, constructed capability,
capacity, and external connection criteria read their binding authoritative
sources. Sustained need and settlement stage are registered but unavailable
until Tasks 19 and 21; they deterministically block without guessing future
domain state.

Objectives are visited in stable dependency/alternative order. Dependencies
are prerequisites, alternative completion may satisfy a parent, required
objectives follow the binding graph rule, deadlines use the current engine
tick, all completion criteria are required, and any failure criterion is
sufficient. Lifecycle changes go only through `GoalManager`; blocked records
may complete directly. Each actual transition appends one immutable event and
one normalized detached evidence record. While status remains active or
blocked, materially changed normalized evaluation description or source-event
provenance appends manager-owned progress evidence without an event. Repeated
unchanged evaluation is idempotent, and a failed transition rolls back the
evaluation pass.

## Boundary and composition

The implementation stays within the Task 18a allowed-file boundary and changes
no persistence schema or inspection shape. Schema v6 already persists the
resulting state and evidence. `GoalEvaluationSystem` is registered after all
existing domain and cognition systems and runs before tick increment. It adds
no needs, stages, work, UI, or NPC-visible evidence. Existing prose-only
`NPCGoalInterpretation` remains unchanged.

## Validation

- Focused goal/evaluation/persistence/scenario/engine tests: 94 passed.
- `make`: Ruff and Black passed, 569 tests passed, and examples 001–030
  passed.
- Separate `make examples`: examples 001–030 passed.
- `git diff --check`: passed.
