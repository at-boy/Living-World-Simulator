# 20b — Deterministic work execution implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development` while implementing this plan. The root
> orchestrator delegates this complete isolated task to one worker and retains
> review, validation, commit, merge, and push authority.

**Goal:** Execute Task 20/20a work orders deterministically through
manager-owned effects with exact-once charging, save/resume equivalence, and
atomic phase rollback.

**Architecture:** `WorkExecutionSystem` performs stable selection and behavior
against a shadow `WorldState`, using freshly composed domain managers. It
commits the shadow fields only after the complete work phase succeeds and runs
before consequences, needs, and goals.

**Tech stack:** Python 3.11+, frozen dataclasses, manager-owned mutations,
immutable events, SQLite snapshot schema 10, pytest.

**Spec:** `docs/adr/ADR-0023-deterministic-work-execution.md`

## Status and dependencies

Authorized after reviewed Task 20a. Execute only on
`task/20b-work-execution`. ADR-0021, ADR-0022, and ADR-0023 are binding.

## Global constraints

- Preserve `WorldState -> perception -> immutable cognitive records ->
  filtered NPC context -> cognition proposal -> action gateway -> world
  event/state change`.
- Managers own mutation, systems own behavior, and events are immutable.
- LLM output remains an untrusted proposal and never executes work or mutates
  goals, objectives, or settlement stages.
- Stable work ordering is `(-priority, created_tick, work_id)`.
- The work phase is atomic; scheduler-wide rollback is out of scope.
- Consumables charge exactly once; tools are never consumed.
- Support schema versions 1–10 and write schema 10.
- Do not commit, merge, push, or change branches as the implementation worker.

## Exact execution contract

The binding lifecycle, availability, arithmetic, deadline, rollback, event,
domain-effect, persistence, and information-boundary decisions are defined in
ADR-0023. Implementation must not substitute inferred charging, in-memory
execution flags, direct `WorldState` domain mutation, recipe invention,
external dispatch creation, or new NPC-visible execution data.

Expected transient conditions use these stable engine-only reasons:

- `Waiting for eligible labor.`
- `Reserved tools are unavailable.`
- `Required consumables are unavailable.`

Expected permanent failure reasons are:

- `A prerequisite cannot complete.`
- `The work deadline expired.`
- `The work target is permanently unavailable.`

## Allowed files

Implementation may modify only:

- `src/living_world/work/model.py`
- `src/living_world/work/manager.py`
- `src/living_world/work/execution.py` (new)
- `src/living_world/work/__init__.py`
- `src/living_world/__init__.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/needs/consequence.py`
- `tests/test_work_execution.py` (new)
- `tests/test_work_orders.py`
- `tests/test_sqlite_repository.py`
- `tests/test_simulation_scheduler.py`
- `tests/test_scenario_run_contract.py`
- `tests/test_spatial_domain.py`
- `examples/036_work_execution.py` (new)
- `docs/adr/ADR-0023-deterministic-work-execution.md`
- `docs/subagent_execution_plan/v0_6/20b_work_execution.md`
- `docs/subagent_execution_plan/v0_6/20b_work_execution-prombt.md`
- `docs/subagent_execution_plan/v0_6/20b_work_execution-report.md` (new)
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/backlog.md`

Stop and report rather than expanding this boundary. The root must amend the
plan and saved prompt before any additional file is authorized.

---

### Task 1: Persist exact-once charge state

**Files:** `src/living_world/work/model.py`,
`src/living_world/work/manager.py`,
`src/living_world/repositories/sqlite_repository.py`,
`tests/test_work_orders.py`, `tests/test_sqlite_repository.py`

**Interfaces:**

- Add `WorkState.inputs_charged_tick: int | None = None` after
  `started_tick` and before `resolution_tick`.
- Add `WorkManager.record_inputs_charged(work_id: str) -> WorkState`; it
  accepts assigned or active work with an active reservation, rejects a second
  charge, records the exact ADR-0023 `work_inputs_charged` payload, and persists
  the current tick atomically.
- Make reservation availability calculations ignore a definition's
  consumable requirements once its state has `inputs_charged_tick`, while
  continuing to lock every tool requirement.
- Serialize the exact `inputs_charged_tick` key in schema 10. Versions 1–9
  deserialize the value as `None`.

- [ ] Add failing lifecycle, charge-once, released/reassigned-lock, malformed
  loaded-state, and schema 9→10 tests.
- [ ] Run the named Task 1 tests and confirm they fail for missing schema/model
  behavior.
- [ ] Implement the frozen field, manager mutation/validation, lock arithmetic,
  schema bump, serialization, deserialization, and migration default.
- [ ] Run `PYTHONPATH=src .venv/bin/pytest tests/test_work_orders.py
  tests/test_sqlite_repository.py -q` and retain the result for the report.

### Task 2: Add deterministic selection and lifecycle behavior

**Files:** `src/living_world/work/execution.py`,
`src/living_world/work/__init__.py`, `src/living_world/__init__.py`,
`tests/test_work_execution.py`

**Interfaces:**

- Create `WorkExecutionSystem(definitions: DefinitionManager)` implementing
  `SimulationSystem`. It composes `EventManager`, `WorkManager`,
  `SpatialManager`, `EntityManager`, `RelationshipManager`, `ResourceSystem`,
  `ConsequenceManager`, and `ExternalWorldReferenceManager` against each
  shadow state without retaining authoritative execution state outside
  `WorldState`.
- `step(state: WorldState) -> None` deep-copies state, executes the entire phase
  on the shadow, and commits every dataclass field only after success.
- Internal selection uses `WorkManager.all()`, sorted eligible entity IDs, and
  an in-phase labor/tool ledger. It applies the exact ADR-0023 availability,
  prerequisite, recovery, deadline, and progress rules.
- First activation removes all consumables, calls
  `record_inputs_charged()`, then `activate()` in the same shadow transaction.
  Active legacy/direct-manager work without a charge marker charges before its
  next progress mutation.
- Each progress update emits threshold events for every newly crossed member
  of `(25, 50, 75)` using integer cross multiplication:
  `previous * 100 < required * threshold <= current * 100`.

- [ ] Add failing tests for priority/creation/ID competition, zero-labor work,
  unscheduled and scheduled labor, double-booking, actor loss, tool and
  consumable undercollateralization, block/recovery, deadline/prerequisite
  failure, bounded progress, and exact threshold events.
- [ ] Run the new named tests and confirm failure for the absent system.
- [ ] Implement the minimal selection, lifecycle, charging, progress, and
  phase-transaction behavior.
- [ ] Run `PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
  tests/test_work_orders.py -q` and retain the result for the report.

### Task 3: Apply all six authoritative effects

**Files:** `src/living_world/work/execution.py`,
`src/living_world/needs/consequence.py`, `tests/test_work_execution.py`

**Interfaces:**

- Add `ConsequenceManager.restore(policy_id: str, amount: int) ->
  MaintenanceState`. It validates a live positive-condition target, caps at
  `maximum_condition`, records one immutable restoration event, and rolls its
  local mutation back if event recording fails.
- Resource effects call `ResourceSystem.add()` and record
  `work_resource_produced` with the settlement as subject.
- Capability effects call `EntityManager.create()`,
  `RelationshipManager.create(kind="owns", ...)`, and `SpatialManager.place()`
  with the exact ADR-0023 naming/point rule; record
  `work_capability_constructed` with the capability as subject.
- Maintenance calls `ConsequenceManager.restore()` with
  `recovery_per_paid_tick`.
- Connection work calls `ExternalWorldReferenceManager.transition_contact()`
  only from `KNOWN` or `UNAVAILABLE`; already `CONTACTABLE` is an idempotent
  satisfied effect without another contact event.
- Every fully progressed effect precedes `WorkManager.complete()` in the same
  shadow transaction.

- [ ] Add failing parametrized exact-effect tests for all six categories,
  deterministic multiple capability construction, permanent target loss,
  extra-step no-op behavior, and no duplicate effects after reload.
- [ ] Add fault-injection tests proving late effect/event/completion failure
  leaves work, resources, entities, relationships, placements, maintenance,
  references, reservations, events, and ID allocation observably unchanged.
- [ ] Run the new named tests and confirm failure for missing adapters.
- [ ] Implement only the exact domain adapters above.
- [ ] Run `PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
  tests/test_consumption_maintenance.py tests/test_external_world_references.py
  -q` and retain the result for the report.

### Task 4: Compose scheduler order and save/resume equivalence

**Files:** `src/living_world/simulation/simulation_engine.py`,
`tests/test_simulation_scheduler.py`, `tests/test_work_execution.py`,
`tests/test_sqlite_repository.py`

**Interfaces:**

- `SimulationEngine` owns one `WorkExecutionSystem` and registers it after all
  `_registered_systems` but before `ConsequenceSystem`, `NeedAssessmentSystem`,
  and `GoalEvaluationSystem` in every scheduler rebuild.
- Work produced in a tick is therefore visible to consequences in that same
  tick and to needs/goals later in the same tick.
- Reloaded engines reconstruct execution solely from persisted `WorldState`;
  no system cache, offer, selection list, or manager counter is persisted.

- [ ] Replace the Task 20 no-work-system assertion with an exact phase-order
  test.
- [ ] Add uninterrupted-versus-resumed comparisons at assigned/unpaid,
  active/charged, partially progressed, blocked, and completed checkpoints.
- [ ] Assert equality of work state, reservations, domain state, events, and
  final tick, including no second charge or effect.
- [ ] Run `PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
  tests/test_simulation_scheduler.py tests/test_sqlite_repository.py -q` and
  retain the result for the report.
- [ ] Update only the schema rewrite expectations in
  `tests/test_scenario_run_contract.py` and `tests/test_spatial_domain.py` from
  version 9 to version 10; do not otherwise change their legacy contracts.

### Task 5: Example, documentation, and worker validation

**Files:** `examples/036_work_execution.py`, `CHANGELOG.md`,
`docs/project_journal.md`, `docs/backlog.md`, and
`docs/subagent_execution_plan/v0_6/20b_work_execution-report.md`

- [ ] Add a deterministic example that creates authorized food work, lets the
  engine select/execute it, and prints only concise safe outcome summaries.
- [ ] Update changelog and journal with Task 20b behavior; remove stale Task
  20b backlog text and preserve unrelated future work.
- [ ] Create the truthful report with files changed, contract decisions,
  focused commands/results/counts, failures/corrections, schema migration,
  NPC-boundary statement, and remaining risks.
- [ ] Run `.venv/bin/ruff check --fix` and `.venv/bin/black` only on allowed
  Python files, then rerun the focused Task 20b matrix.
- [ ] Run `make`, `make examples`, and `git diff --check`. Record commands,
  results, counts, and meaningful warnings only; do not paste successful
  output into the report.
- [ ] Return the worker contract: concise summary, exact files changed,
  focused/full validation results, and unresolved issues. Do not commit.

## Required review

An independent read-only reviewer must inspect `AGENTS.md`, this plan, the
saved prompt, ADR-0023, the actual diff, the implementation report, and only
directly relevant code/tests. The reviewer checks allowed-file compliance,
manager/system ownership, immutable event semantics, deterministic ordering,
schema migration, rollback, save/resume, all six effects, test quality,
simulation authority, NPC/LLM boundaries, and report accuracy. With no
substantive findings, return exactly `NO SUBSTANTIVE FINDINGS` plus any
unverifiable item that the root must resolve.

## Root validation and delivery

After review findings are resolved and re-reviewed, the root independently
runs the focused matrix, `make`, separate `make examples`, and
`git diff --check`; completes truthful documentation; commits and pushes the
task branch; merges it with `--no-ff` only into `milestone/v0.6`; validates and
pushes the milestone branch; then updates the continuation checkpoint.
