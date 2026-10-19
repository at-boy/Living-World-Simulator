# Task 20b implementation report

## Status

DONE. The root amended the boundary to authorize the two schema rewrite
expectations identified by the first full validation; both now expect schema
10 and all required validation passes.

## Files changed

- `src/living_world/work/model.py`
- `src/living_world/work/manager.py`
- `src/living_world/work/execution.py`
- `src/living_world/work/__init__.py`
- `src/living_world/__init__.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/repositories/sqlite_repository.py`
- `src/living_world/needs/consequence.py`
- `tests/test_work_execution.py`
- `tests/test_work_orders.py`
- `tests/test_sqlite_repository.py`
- `tests/test_simulation_scheduler.py`
- `tests/test_scenario_run_contract.py`
- `tests/test_spatial_domain.py`
- `examples/036_work_execution.py`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/backlog.md`
- this report

The pre-existing `.codex/config.toml` modification was not touched.

## Behavioral and invariant change

Work state now persists `inputs_charged_tick`; `WorkManager` records charging
once and charged reservations stop locking consumables while retaining tool
locks. Schema 10 writes the marker and schemas 1-9 default it to `None`.

`WorkExecutionSystem` executes stable work order on a shadow state, selects
eligible labor, blocks and recovers transiently unavailable work, charges
inputs once, emits exact progress thresholds, applies resource, construction,
maintenance, and contact effects through their domain managers, and commits
only after the complete phase succeeds. It is scheduled before consequences,
needs, and goals. `ConsequenceManager.restore` atomically records bounded
maintenance restoration.

Managers remain mutation owners, the system owns behavior, events remain
immutable, and no goal/objective/stage or external-dispatch authority was
added. Task 20b adds no NPC-visible pathway: work IDs, reservations, charge
state, progress, reasons, effects, events, and ticks remain engine-only. LLM
output remains an untrusted Task 20a proposal.

## TDD evidence

RED: `PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
tests/test_work_orders.py -q` failed during collection because
`WorkExecutionSystem` did not exist. The added exact-once manager test also
targeted the absent `record_inputs_charged` API.

Additional RED coverage exposed two real integration defects: charged blocked
work attempted a second charge on recovery, and same-tick work restoration
violated the consequence manager's loaded-state preflight. The focused run
failed in those exact branches before production corrections. Recovery now
activates without charging when the persisted marker exists, and unprocessed
maintenance permits a manager-restored condition between its initial and
maximum bounds.

GREEN focused matrix:
`PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
tests/test_work_orders.py tests/test_consumption_maintenance.py
tests/test_external_world_references.py tests/test_simulation_scheduler.py
tests/test_sqlite_repository.py -q` passed: 245 passed, 10 skipped.

Example plus diff check:
`PYTHONPATH=src .venv/bin/python examples/036_work_execution.py && git diff
--check` passed. The example reported completed work and `{'seed': 0,
'food': 5}`.

Full validation: `make` passed lint, formatting, 911 tests with 10 skips, and
all 36 examples. Separate `make examples` also passed all 36 examples.
`git diff --check` passed.

## Failures, corrections, and self-review

The first shadow-copy implementation deep-copied immutable mapping proxies and
replaced unrelated object identities even when no work existed. Full
validation exposed both problems. The phase now returns without mutation when
there are no work definitions, shallow-copies immutable record collections,
and deep-copies mutable entities and relationships.

Self-review found no edits outside the amended authorized list and no direct domain,
goal, stage, dispatch, cognition, or NPC-context mutation. Remaining execution
coverage now includes stable undercollateralization ordering and one recovery
event, exact effects for all six categories, deterministic multiple
construction, permanent target loss, late effect/completion fault rollback,
extra-step no-op behavior, and assigned/charged/partial/blocked/completed
save-resume equivalence. Independent review should still inspect the shadow
copy/commit implementation carefully.

## Correction round 1

Independent review found that active reserved labor was incorrectly checked
through a truncated new-assignment candidate list, point construction used the
point entity rather than its existing parent as the placement container,
charged recovered work still required consumables during manager reassignment,
and the execution system rewrote the event dictionary to manufacture recovery.

RED: `PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
tests/test_work_orders.py -q` failed three exact regressions: higher-ID reserved
labor was replaced, point construction attempted an invalid point container,
and charged recovery rejected zero remaining seed.

GREEN corrections validate each existing reserved laborer without truncation,
use a point location's existing parent while bounds use the location itself,
ignore consumables for charged reassignment, and make `WorkManager.mark_ready`
own the exact `work_order_recovered` event. The system no longer edits events
directly.

Coverage added for priority and same-tick ID competition; unscheduled, working, and
non-working scheduled labor; active reservation continuity; exclusive
deadlines; failed and cancelled prerequisites; consumable shortage; exact
charge payload; malformed charge lifecycle; schema-9 active-unpaid resume;
point/bounds construction parenting; already-contactable idempotence; same-tick
work/consequence/need/goal visibility; complete shadow-field rollback; and
allocator-visible entity/relationship/event reuse after rollback.

Focused correction matrix:
`PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py
tests/test_work_orders.py tests/test_consumption_maintenance.py
tests/test_external_world_references.py tests/test_simulation_scheduler.py
tests/test_sqlite_repository.py -q` passed: 260 passed, 10 skipped.

The first correction-round `make` stopped at lint because one new test retained
an unused local variable. That test-only issue was removed. Final `make` passed
lint, formatting, 926 tests with 10 skips, and all 36 examples. Separate
`make examples` passed all 36 examples. `git diff --check` passed.

No NPC-visible surface or cognition authority changed. The correction retains
manager-owned mutation, immutable events, stable ordering, persisted charge
evidence, and atomic shadow-phase rollback.

## Correction round 2

The original ordering test covered priority and the same-tick ID fallback but
did not isolate `created_tick`. A new adversarial regression gives equal-priority
work deliberately opposed creation-tick and ID ordering; the higher ID wins
because its persisted creation tick is earlier. This proves creation tick is
considered before the final ID tie-breaker while preserving the existing
priority and same-tick ID coverage.

`PYTHONPATH=src .venv/bin/pytest tests/test_work_execution.py -q -k
'priority_then_creation_then_id or creation_tick_precedes_work_id'` passed: 2
passed, 28 deselected. `git diff --check` passed.

## Root validation

After independent re-review concluded with no substantive findings, the root
orchestrator ran the authoritative validation gate. The focused work,
consequence, external-reference, scheduler, and persistence matrix passed with
261 tests and 10 skips. `make` passed lint, formatting, 927 tests with 10
skips, and all 36 examples. A separate `make examples` passed all 36 examples,
and `git diff --check` passed.
