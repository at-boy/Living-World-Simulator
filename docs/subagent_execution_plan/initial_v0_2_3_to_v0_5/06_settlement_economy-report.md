# Task 06 — Construction, Roads, Housing, Economy, Production, and Trade Report

## Outcome

Implemented the v0.3 settlement-economy milestone with generic entities,
relationships, resource attributes, progress values, deterministic systems,
and immutable material-outcome events. No specialized settlement, housing, or
road runtime model was introduced.

## Exact Files Changed

- `src/living_world/systems/resource_system.py`
- `src/living_world/systems/construction_system.py`
- `src/living_world/systems/housing_system.py`
- `src/living_world/systems/production_system.py`
- `src/living_world/systems/trade_system.py`
- `src/living_world/simulation/simulation_engine.py`
- `tests/test_resource_system.py`
- `tests/test_construction_system.py`
- `tests/test_progress_system.py`
- `tests/test_housing_system.py`
- `tests/test_production_system.py`
- `tests/test_trade_system.py`
- `examples/016_settlement_economy.py`
- `CHANGELOG.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/06_settlement_economy-report.md`

## Public Interfaces Added or Changed

- Added `ConstructionSystem(SimulationSystem)`, `HousingSystem(SimulationSystem)`,
  `ProductionSystem(SimulationSystem)`, and `TradeSystem(SimulationSystem)`.
  Each exposes `step(self, state: WorldState) -> None`.
- `SimulationEngine` registers `ProgressSystem` before `ConstructionSystem`,
  followed by `HousingSystem`, `ProductionSystem`, and `TradeSystem`, after
  the existing weather, population, organization, and settlement systems.
- `ResourceSystem.set`, `add`, `remove`, and `transfer` now reject negative
  quantities or amounts. `remove` and `transfer` reject insufficient source
  quantity before mutation, preserving non-negativity and transfer atomicity.

## Behavior and Invariant Evidence

- Construction interprets completed generic progress (`progress >= progress_max`)
  and consumes entity-held `construction_requirements` only when all resources
  are available. The engine-level construction test proves that one
  `SimulationEngine.step()` advances bounded progress, completes construction,
  consumes requirements, records exactly one `construction_completed` event,
  and leaves an unrelated road relationship intact.
- Housing interprets only completed opt-in dwellings. It derives distinct
  incoming `housed_in` residents and clamps `housing_allocated` to
  `housing_capacity`, recording `housing_allocation_changed` on a material
  change.
- Production consumes `production_inputs` and adds `production_outputs` only
  when all inputs are available, recording `production_completed`.
- Trade interprets a `trade` relationship only when both endpoints are linked
  by an existing `road` relationship. It transfers via `ResourceSystem` and
  records `trade_completed`; systems never create or edit road relationships.
- Tests cover bounded construction progress, insufficient construction
  resources, capacity-bounded housing, preservation of unrelated graph edges,
  production non-negativity, insufficient transfer atomicity, road-gated
  trade, and identical-world deterministic production output and event data.

## Example and Documentation

`examples/016_settlement_economy.py` loads settlement vocabulary from YAML,
then creates runtime entities and relationships only through engine managers.
It demonstrates construction, housing allocation, production, a manager-created
road, and road-gated trade.

`Makefile` was intentionally unchanged: its existing
`examples/[0-9][0-9][0-9]_*.py` discovery ran the new `016` example
automatically, as shown by the validation result below.

Updated `CHANGELOG.md`, `docs/backlog.md`, `docs/core_model.md`,
`docs/engine_glossary.md`, and `docs/project_journal.md` with the completed
v0.3 conventions and lifecycle guarantees.

## Validation Results

```text
make
  PASS: Ruff, Black, pytest (168 passed), and examples 001 through 016.

make examples
  PASS: examples 001 through 016, including 016_settlement_economy.py.

git diff --check
  PASS: no whitespace errors.
```

## Boundary Compliance

The correction changed only its permitted engine, construction-test,
progress-system-test, and report files. The original Task 06 changes remain
within its documented boundary. No NPC cognition, LLM integration, or NPC
information-boundary behavior was added or changed.

## Blockers or Deferred Work

None.
