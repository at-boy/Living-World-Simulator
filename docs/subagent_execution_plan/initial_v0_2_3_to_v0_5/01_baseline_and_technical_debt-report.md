# 01 — Baseline and Technical-Debt Reconciliation Report

## Outcome

The v0.2.3 baseline was audited and the verifiable technical-debt cleanup was
completed within the assigned scope.

`make examples` now discovers every top-level example matching
`[0-9][0-9][0-9]_*.py`, executes the files in lexical order, prints the file
being run, reports PASS or FAIL, and stops at the first failure.

## Audit Results

- `Location` is absent from the runtime. Locations are `Entity` instances
  created through `EntityManager.create()`, including in
  `examples/001_create_world.py`.
- No location-specific runtime collection remains.
- `RelationshipManager` is the sole production mutation boundary for
  relationship creation and registration; the example uses it.
- Immutable event history is already implemented through `EventManager` and
  was not reimplemented.
- Repository Layer remains the only open item in `docs/technical_debt.md`.

## Files Changed

- `Makefile`
- `docs/technical_debt.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`

No runner pytest file was added because discovery is implemented directly in
the Makefile and no production discovery helper was needed.

## Validation

- `make examples` passed: all 11 eligible examples ran once, in order.
- Failure propagation passed: overriding `EXAMPLES` with `/bin/false` produced
  FAIL output and a nonzero Make exit status.
- `PYTHONPATH=src .venv/bin/pytest tests/test_entity_manager.py tests/test_relationship_manager.py -q` passed: 2 tests.
- `.venv/bin/ruff check src tests` passed.

## Handoff Blocker

`make check` cannot currently pass without an out-of-scope edit. Black reports
that `src/living_world/perception/llm_perception_engine.py` would be
reformatted. The task boundary excluded LLM code, so that file was deliberately
left unchanged. Resolve that pre-existing formatting issue before treating the
repository as ready for Task 02, whose execution plan requires a passing
`make`.
