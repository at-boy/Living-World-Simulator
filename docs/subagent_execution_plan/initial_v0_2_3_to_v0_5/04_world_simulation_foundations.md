# 04 — Regions, terrain, weather, and population

## Task Description

Deliver the remaining v0.2 world-simulation capabilities as deterministic
systems over generic entities, relationships, resources, and events.

## Context Needed

- Create: `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`.
- Create: `src/living_world/systems/weather_system.py`,
  `src/living_world/systems/population_system.py`,
  `tests/test_weather_system.py`, `tests/test_population_system.py`,
  `examples/014_world_simulation.py`.
- Edit: `src/living_world/systems/simulation_system.py`,
  `src/living_world/simulation/simulation_scheduler.py`,
  `src/living_world/systems/progress_system.py`,
  `src/living_world/systems/resource_system.py`,
  `src/living_world/managers/entity_manager.py`,
  `src/living_world/simulation/simulation_engine.py`,
  `tests/test_simulation_engine.py`, `tests/test_simulation_scheduler.py`, and
  YAML fixtures under `examples/` as needed.
- Edit docs: `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`,
  `docs/project_journal.md`.
- Know: entity definitions represent regions and terrain; `Relationship`
  represents containment/adjacency; `SimulationSystem`, `EventManager`, and
  manager-only mutation rules.

## Interface Contract

```python
class WeatherSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...

class PopulationSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
```

- Migrate the system contract from `update()` to
  `step(state: WorldState) -> None`. `SimulationScheduler` passes its
  authoritative state to systems in registration order; existing generic
  systems and their scheduler/engine tests are migrated in the same batch.
- Add `EntityManager.set_attribute(*, entity_id: str, key: str, value: object)
  -> None` as the manager-owned mutation path for system-written entity
  attributes. `ProgressSystem`, `WeatherSystem`, and `PopulationSystem` use
  this path rather than mutating entity attribute dictionaries directly.
- Regions and terrain are entities defined by YAML archetypes, not new engine
  primitives.
- Weather and population use documented entity attributes and deterministic
  rules; they mutate through managers/approved system APIs and record material
  changes through `EventManager.record()`.
- Systems are generic enough to work for any definition that opts in through
  `Definition.systems`.

## Test Criteria

- Registration order yields repeatable weather/population results.
- Non-participating entities are unchanged.
- Bounds, invalid configuration, and event recording are tested.
- Existing progress, resource, scheduler, and engine behavior remains covered
  after the `step(state)` protocol migration.
- Example exercises regions, terrain, weather, and population through public
  APIs; `make` passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/04_world_simulation_foundations-report.md`.
Report entity/relationship conventions, deterministic-system behavior, event
evidence, example output, and validation results.

## Boundary

- Touch only the files listed above plus directly required fixtures/docs and
  the approved report artifact.
- `Makefile` is not part of this task's implementation scope. If a prior
  in-progress change touched it solely to update an example comment, restore
  that comment rather than expanding the task scope.
- Do not add a `Region`, `Terrain`, `Weather`, or `Population` runtime class.
- Ignore settlement, economy, and cognition features.
