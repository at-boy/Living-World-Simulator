# 04 — World Simulation Foundations Report

## Conventions

Regions and terrain are ordinary entities created from YAML definitions.
Definitions opt into `weather` and/or `population` through `systems`.
`contains` denotes region-to-terrain containment and `adjacent` denotes a
peer connection; both remain ordinary relationships.

## Deterministic behavior

`WeatherSystem` processes opt-in entities in entity-id order, applies the
current item from a non-empty `weather_cycle`, and advances the bounded
`weather_index` modulo the cycle length. `PopulationSystem` likewise uses
entity-id order, applies `population_change`, then clamps to configured bounds.
Non-opt-in entities are untouched. Invalid attributes fail explicitly.

The scheduler calls `step(state)` in registration order. The engine registers
weather then population, producing repeatable outcomes.

## Event evidence and example

Material weather changes emit `weather_changed`; population changes emit
`population_changed`, both via `EventManager.record()`. `014_world_simulation.py`
loads YAML archetypes, creates a region and terrain via public APIs, links them
with `contains`, runs two ticks, and prints their resulting values and events.

## Validation

`tests/test_weather_system.py` covers deterministic cycles, opt-in isolation,
invalid configuration, and events. `tests/test_population_system.py` covers
bounds, invalid configuration, opt-in isolation, events, and registration-order
repeatability. The full pytest suite passes (152 tests), and `make examples`
passes all 14 numbered examples, including `014_world_simulation.py`. `make`
completed successfully (exit status 0): Ruff linting, Black formatting and
format checking, 152 pytest tests, and all 14 numbered examples passed.

## Exact Files Changed

- `CHANGELOG.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`
- `examples/014_world_simulation.py`
- `src/living_world/managers/entity_manager.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/simulation/simulation_scheduler.py`
- `src/living_world/systems/population_system.py`
- `src/living_world/systems/progress_system.py`
- `src/living_world/systems/resource_system.py`
- `src/living_world/systems/simulation_system.py`
- `src/living_world/systems/weather_system.py`
- `tests/test_population_system.py`
- `tests/test_simulation_engine.py`
- `tests/test_simulation_scheduler.py`
- `tests/test_weather_system.py`

The scheduler/system-protocol migration files are `simulation_engine.py`,
`simulation_scheduler.py`, `simulation_system.py`, `progress_system.py`,
`resource_system.py`, `test_simulation_engine.py`, and
`test_simulation_scheduler.py`.

## Boundary Compliance

The scheduler/system-protocol migration is authorized by the amended Task 04
boundary. No location-specific runtime model was added: regions and terrain
remain generic entities, and containment or adjacency remains a relationship
convention.

## Blockers and Deferred Work

None.
