# 18a — Objective evaluation and events

## Status and dependency

Authorized after reviewed Task 18. Execute on
`task/18a-objective-evaluation-events`.

## Task description

Add a deterministic evaluation system that derives objective activation,
progress evidence, blockage, completion, and failure from authoritative state
after domain systems run. Record one immutable event per actual transition.

## Contract and tests

- Add typed criterion evaluators behind a protocol/registry; reject unknown
  criteria at configuration time. Evaluation reads world state and mutates only
  through the Task 18 manager.
- Dependencies activate in stable graph order; alternatives complete their
  parent when policy is satisfied; deadlines fail only from engine tick.
- Evidence is detached, normalized, deterministic, and persisted without
  copying arbitrary runtime objects. Repeated unchanged evaluation is
  idempotent.
- Extend scheduler/engine composition, focused inspection where needed,
  tests/example/docs, changelog, journal, backlog, and report. Do not add needs,
  work, stage implementations, UI, or NPC access to exact evidence.
- Cover all criterion kinds available at this point, dependency/alternative
  order, blocked and deadline paths, idempotence, save/resume, and events. Run
  `make`, `make examples`, and `git diff --check`.

## Binding evaluation semantics

- Evaluation runs after every existing domain/cognition system at the current
  tick and before the scheduler increments the tick. A deadline fails when the
  current engine tick is greater than or equal to its configured deadline.
- Dependencies are prerequisites. An objective activates only after all of its
  dependencies complete. A failed dependency fails the dependent objective;
  an incomplete or blocked dependency leaves it inactive or blocked without
  inventing progress.
- An objective completes when all of its completion criteria are satisfied or
  any declared alternative objective completes. Objectives referenced as
  alternatives are optional paths and are not independently required for goal
  completion unless they are also required elsewhere in the graph.
- Required objectives are every goal objective except an ID that appears in an
  `alternatives` tuple and nowhere in a `dependencies` tuple. A goal completes
  only when every required objective completes
  and all goal-level completion criteria are satisfied. It fails on its
  deadline, satisfied failure criteria, or failure of a required objective.
- Completion requires every completion criterion. Any satisfied failure
  criterion is sufficient to fail its goal or objective.
- For each non-terminal record, apply this precedence: deadline failure,
  satisfied failure criteria, dependency failure/blockage, completion or
  alternative satisfaction, then active-but-incomplete. Terminal states remain
  unchanged.
- `BLOCKED -> COMPLETED` is a valid direct manager transition when fresh
  authoritative evaluation proves completion; do not emit an artificial
  activation transition first. Every actual transition emits exactly one
  immutable event, and unchanged evaluation emits neither events nor evidence.
- Criterion evaluators return a frozen satisfied/unsatisfied/unavailable result
  with normalized prose and lexically sorted source event IDs. Evidence may
  contain only detached primitive data accepted by `ProgressEvidence`.
- The registry must include all six Task 18 criterion types. Resource minimum,
  constructed capability, capacity, and external connection have concrete
  evaluators in this task. Constructed capability and capacity are scoped to
  the live goal owner plus live entities directly owned through canonical
  `owns` relationships; construction requires `is_constructed is True`.
- Resource minimum reads the goal owner's existing `resources` mapping without
  mutating it; an absent resource is quantity zero. Constructed capability
  matches `Entity.definition_key` exactly to `criterion.capability`. Capacity
  sums non-negative integer attributes named
  `<criterion.capacity>_capacity`; if no scoped live entity defines that
  attribute, the result is unavailable rather than zero. External connection
  matches `ExternalWorldReference.role` and `ContactState.value` exactly in
  lexical reference-ID order. Invalid authoritative field types fail loudly.
- `SustainedNeedCriterion` is registered but unavailable until Task 19 provides
  authoritative need state. `SettlementStageCriterion` is registered but
  unavailable until Task 21 provides authoritative stage state. These known
  deferred criteria deterministically block rather than being treated as
  unknown or guessed from arbitrary attributes. An unregistered criterion type
  is rejected when the evaluation system is configured.

## Allowed-file boundary

- `src/living_world/goals/evaluation.py`,
  `src/living_world/goals/manager.py`, and
  `src/living_world/goals/__init__.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/__init__.py` only if the new evaluator protocol/result are
  intentionally part of the root public API
- `tests/test_goal_evaluation.py` and focused additions to
  `tests/test_goals.py`, `tests/test_sqlite_repository.py`, and
  `tests/test_scenario_run_contract.py`
- `examples/030_objective_evaluation.py`
- `CHANGELOG.md`, `docs/adr/ADR-0019-engine-owned-goals.md`,
  `docs/backlog.md`, `docs/core_model.md`, `docs/engine_glossary.md`, and
  `docs/project_journal.md`
- This plan, its saved `-prombt.md`, and
  `docs/subagent_execution_plan/v0_6/18a_objective_evaluation_events-report.md`

No persistence schema or inspection shape change is expected: schema v6 and
`GET /world/goals` already persist and expose privileged lifecycle evidence.
Amend this plan and its saved prompt before touching any other file.

## Report

Create `docs/subagent_execution_plan/v0_6/18a_objective_evaluation_events-report.md`.
