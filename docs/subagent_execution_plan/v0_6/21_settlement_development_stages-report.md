# Task 21 — settlement development stages implementation report

## Status and boundary

Implemented on `task/21-settlement-development-stages` in the isolated Task 21
worktree. No commit, merge, push, branch/configuration change, or main change was
performed by this worker. Worker delivery subsequently passed independent review and root acceptance;
see root sections below. ADR-0024 remains accurate and unchanged.

The root amended the task plan and saved prompt before edits to three additional
regression files: schema-version assertions in `test_scenario_run_contract.py`
and `test_spatial_domain.py`, and the trailing phase assertion in
`test_simulation_scheduler.py`. Those edits contain only the specified assertion
updates. No adjacent feature work was included.

## Implemented behavior

- Frozen/slotted stage records, the closed canonical three-stage vocabulary, and
  immutable directly bound per-settlement programs/state. Configuration validates
  live owners, exact stage order, empty founding requirements, nonempty promotion
  requirements, unique objective references, unique settlement-goal ownership,
  typed completion-criterion roles and sustainable unique owner need windows.
  Population-only promotion is rejected. Requirement order is normalized before
  storage so exact programs round-trip in canonical order.
- Manager-owned adjacent transitions consume only completed objective statuses
  and normalized progress/lifecycle provenance. Transition evidence is checked
  against authoritative evidence rather than trusting caller-supplied sources.
  One transition per settlement per tick, terminal-town idempotence, exact frozen
  event attributes, individual rollback and complete stage-phase rollback are
  covered. Earlier phases and events remain intact on stage-phase failure.
- New population and maintained-capability goal criteria have strict manager
  validation, closed deterministic registry dispatch, normalized descriptions
  and sorted source IDs. Missing population is unavailable; missing maintenance
  matches are unsatisfied; malformed/contradictory authoritative records raise.
  Existing stage criteria read managed state and see promotion on the next tick.
- Engine composition exposes `settlement_stages`; scheduler order is ordinary
  systems, work, consequences, needs, goals, stages, tick increment. Existing
  entity removal/destruction guards remain and now also protect stage owners.
- Schema 11 persists exact stage programs/states and both new goal criteria.
  Schemas 1–10 load empty stage collections and write forward. Decoding rejects
  malformed fields, discriminators, ordering, duplicates, ownership, missing
  paired records and invalid ticks; stage validation follows prerequisite
  reconstruction. Failed saves retain the previous database snapshot.
- Detached, settlement-ID ordered privileged inspection and GET-only
  `/world/settlement-stages`, plus the summary program count. Fixed explicitly
  selected qualitative NPC prose contains no authoritative IDs, thresholds,
  ticks, criteria, or evidence. Stage IDs, field vocabulary, ticks and referenced
  objective thresholds participate in fail-closed boundary validation. No
  automatic context/perception/memory injection or LLM promotion gateway exists.
- Example 037 demonstrates explicit objective configuration, adjacent promotions,
  privileged inspection and separately selected qualitative prose.

## Changed files

- New `src/living_world/stages/{__init__,model,manager,system}.py`.
- Goal model, manager, evaluation and exports; world state; engine composition;
  entity manager; SQLite repository; inspection protocol/implementation and HTTP
  server; NPC information boundary; established root stage exports.
- New `tests/test_settlement_stages.py` (159 test cases), snapshot version
  assertions in `tests/test_sqlite_repository.py`, summary assertion in
  `tests/test_inspection_api.py`, and the three explicitly amended regression
  files above. Remaining affected test files were validated without edits.
- New `examples/037_settlement_development_stages.py`.
- `CHANGELOG.md`, project journal, backlog, core model, engine glossary, NPC
  information boundary documentation, and this report. Root-authored task plan
  and saved-prompt boundary amendments are included in the working diff.

## TDD, corrections and validation

Initial lifecycle tests failed collection because `PopulationMinimumCriterion`
did not exist; implementing records, goal support and lifecycle yielded three
passing initial tests. Expanded tests exposed live maintenance terminal-condition
contradiction and hidden stage prose acceptance (10 failures / 99 passing);
corrections produced 140 passing combined stage/NPC tests. A later focused red
proved referenced stage-objective thresholds could escape prose validation;
including these numeric thresholds made the complete focused matrix green.
A final focused red used valid GoalManager evidence with unsorted source IDs;
stage normalization now sorts this input before constructing strict transition
evidence, retaining compatibility with existing goal-manager provenance.
An implementation-time criterion-validation branch error was caught and corrected
before final validation. API tests use the repository's existing dependency-free
ASGI client; no new runtime/test dependency was introduced.

The first affected matrix had 106 passes and 17 schema-version expectation
failures, including the former unsupported-schema-11 fixture. Expectations were
updated to schema 11 and the unsupported fixture to 12. The first full `make`
had 1075 passes, 10 deliberate skips, and three outdated schema/phase assertions
in the files outside the original boundary. The root amended the boundary first;
those focused assertion updates then passed 31 tests. These were test-contract
updates, not production behavior relaxations.

Final commands and results:

- `.venv/bin/pytest -q tests/test_settlement_stages.py
  tests/test_goal_evaluation.py tests/test_goals.py tests/test_entity_manager.py
  tests/test_simulation_engine.py tests/test_sqlite_repository.py
  tests/test_inspection_api.py tests/test_npc_information_boundary.py
  tests/test_npc_context.py tests/test_scenario_run_contract.py
  tests/test_spatial_domain.py tests/test_simulation_scheduler.py`: **408 passed**.
- `make`: **passed**, lint/format checks passed, **1086 passed / 10 skipped**;
  all **37 examples passed**.
- Separate `make examples`: **passed**, all **37 examples passed**.
- `git diff --check`: **passed**.

The 10 skips are the existing deliberate repository skips. No new skips or
meaningful validation warnings were introduced. Successful command output is
not reproduced here. Independent review round 1 confirmed production behavior and requested strict
test annotations. That scoped correction is documented below; this report does
not claim re-review approval or milestone integration.

## Independent review round 1 correction

The read-only review in `/tmp/living-world-task21-review.md` found no substantive
runtime defect but identified missing strict annotations in the new test module.
The correction adds concrete setup-helper tuple returns, `GoalCriterion | None`
and requirement-kind inputs, typed enum/case/fixture/factory parameters, and
return annotations for all 38 functions. Tests and the event-failure callback
return `None`; the transition callback retains its concrete
`SettlementStageState` return on the successful path. Explicit casts document
invalid record/enum/tick fixtures, optional managed-state results, detached
inspection projections, immutable event mappings and malformed JSON records.
There is no `Any` shortcut and production code is unchanged.

Correction validation:

- AST annotation audit: **38 functions**, **0 missing return annotations**,
  **0 missing non-self parameter annotations**, **0 `Any` annotations**.
- `.venv/bin/pytest -q tests/test_settlement_stages.py`: **159 passed**.
- `.venv/bin/pytest -q tests/test_settlement_stages.py
  tests/test_goal_evaluation.py tests/test_goals.py tests/test_entity_manager.py
  tests/test_simulation_engine.py tests/test_sqlite_repository.py
  tests/test_inspection_api.py tests/test_npc_information_boundary.py
  tests/test_npc_context.py`: **377 passed**.
- `.venv/bin/ruff check tests/test_settlement_stages.py`,
  `.venv/bin/black --check tests/test_settlement_stages.py`, and
  `git diff --check`: **passed**.

The correction leaves runtime behavior and test counts unchanged. Full gates
were not repeated solely for annotations; the root owns re-review and final
full-tree validation. Only the test module and this report were changed during
this correction.

## Remaining non-goals

Decline/demotion/recovery, reusable templates, scenario-YAML stage bindings,
automatic NPC stage perception/cognition injection and inspector UI work remain
outside Task 21. Population or LLM prose alone cannot promote a settlement.

## Root acceptance — 2026-10-13

Independent review found no production defect and one required test-typing
correction. The original worker corrected it; scoped re-review returned
**Spec PASS, Quality PASS, NO SUBSTANTIVE FINDINGS**.

Root final current-tree validation after re-review:

- `make`: passed; Ruff/Black passed; **1086 passed, 10 existing skips**;
  **examples 001–037 passed**.
- Separate `make examples`: passed; **37 examples passed**.
- `git diff HEAD --check`: passed.

The root accepts Task 21 for task-branch commit and milestone integration.
This report does not claim that integration or remote verification has already
occurred; the milestone continuation checkpoint records those results.

## Integration checkpoint

Root committed the reviewed delivery as `c821efe`, merged it into
`milestone/v0.6` with `1ab288b`, and verified both pushed remote tips. The merged
`make VENV=.worktrees/task21/.venv` gate passed 1086 tests with 10 existing skips
and all 37 examples; separate examples and whitespace checks passed. Live
`main` remained `12f2f17`. User configuration changes were excluded.
