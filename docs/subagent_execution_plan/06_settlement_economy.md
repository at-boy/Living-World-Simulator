# 06 — Construction, roads, housing, economy, production, and trade

## Task Description

Complete the v0.3 settlement milestone using composable systems that interpret
generic progress, resources, entities, relationships, and events.

## Context Needed

- Create: `docs/subagent_execution_plan/06_settlement_economy-report.md`.
- Create: `src/living_world/systems/construction_system.py`,
  `src/living_world/systems/housing_system.py`,
  `src/living_world/systems/production_system.py`,
  `src/living_world/systems/trade_system.py`.
- Create tests: `tests/test_construction_system.py`, `tests/test_housing_system.py`,
  `tests/test_production_system.py`, `tests/test_trade_system.py`.
- Create: `examples/016_settlement_economy.py`.
- Edit: `src/living_world/systems/resource_system.py`, engine registration,
  YAML example definitions, `Makefile`, and standard docs.
- Know: `ProgressSystem`, `ResourceSystem`, `RelationshipManager`,
  `EventManager`, and Task 05 graph conventions.

## Interface Contract

```python
class ConstructionSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
class HousingSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
class ProductionSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
class TradeSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
```

- Roads remain `Relationship(kind="road", ...)`, created only through
  `RelationshipManager`.
- Construction composes generic progress and resources; housing interprets
  completed structures; production and trade use `ResourceSystem` operations.
- Each system has one concern and produces events for material outcomes.

## Test Criteria

- No resource quantity can become negative through production/trade.
- Construction respects progress bounds and resource requirements.
- Roads, housing allocation, and trade leave unrelated graph entities intact.
- Repeated runs with the same state and order are deterministic.
- `make` passes including the settlement example.

## Orchestrator Report

Create `docs/subagent_execution_plan/06_settlement_economy-report.md`. Report
resource/progress invariants, deterministic behavior, manager/event evidence,
example result, and validation results.

## Boundary

- Touch only stated systems, their tests/example/fixtures, engine registration,
  resource-system extension, and docs, plus the approved report artifact.
- Do not add NPC cognition or let systems directly modify state dictionaries.
