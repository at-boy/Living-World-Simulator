# Task 06 — Correction Request Before Commit

Task 06 is not ready to commit. Its construction logic reads generic progress
correctly, but the engine does not schedule `ProgressSystem`. A caller must
manually invoke that system before `SimulationEngine.step()`, so construction
does not form the intended deterministic, engine-owned lifecycle.

## Required Corrections

1. Register the existing `ProgressSystem` with `SimulationEngine`.

   It must run before `ConstructionSystem` in the deterministic scheduler
   order, so an entity can advance bounded progress and have construction
   complete in the same engine step when it reaches `progress_max` and can
   satisfy its requirements.

2. Update `tests/test_construction_system.py`.

   Replace the test's direct `ProgressSystem(engine.entities).step(...)` call
   with an `engine.step()`-only assertion that proves the engine advances
   progress, completes construction, consumes requirements, records the one
   completion event, and leaves the unrelated road relationship intact.

3. Update
   `docs/subagent_execution_plan/06_settlement_economy-report.md`.

   State the corrected scheduler order, the engine-level construction test,
   exact validation commands/results, and boundary compliance. Do not state
   that the task is complete or has no blockers until the required validation
   passes.

4. Update `tests/test_progress_system.py` to remove its redundant explicit
   `ProgressSystem` registration and its now-unused import. The engine now
   owns that registration; the existing assertions must continue proving one
   bounded progress advance per `engine.step()`.

## Validation Required Before Handoff

Run and report the outcome of:

```bash
make
make examples
git diff --check
```

## Boundary

Only edit the following files:

- `src/living_world/simulation/simulation_engine.py`
- `tests/test_construction_system.py`
- `tests/test_progress_system.py`
- `docs/subagent_execution_plan/06_settlement_economy-report.md`

Do not modify `ProgressSystem`, any other Task 06 implementation file, the
example, or unrelated documentation. Do not commit.
