# 05 — Organizations and settlement foundations

## Task Description

Model organizations and settlements through the property graph and provide the
minimal deterministic systems required for later settlement simulation.

## Context Needed

- Create: `docs/subagent_execution_plan/05_organizations_and_settlements-report.md`.
- Create: `src/living_world/systems/organization_system.py`,
  `src/living_world/systems/settlement_system.py`,
  `tests/test_organization_system.py`, `tests/test_settlement_system.py`,
  `examples/014_settlement_foundations.py`.
- Edit: `src/living_world/simulation/simulation_engine.py`, relevant YAML
  example definitions, and `Makefile`.
- Edit docs: `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`,
  `docs/project_journal.md`.
- Know: property-graph ADR, `EntityManager`, `RelationshipManager`,
  `ResourceSystem`, and the Task 04 world entities.

## Interface Contract

```python
class OrganizationSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...

class SettlementSystem(SimulationSystem):
    def step(self, state: WorldState) -> None: ...
```

- Organizations and settlements are entities. Membership, ownership, and
  location are relationships with documented `kind` values.
- Systems may interpret those graph structures but may not mutate
  `WorldState` collections directly.
- No bespoke kingdom, village, or group runtime class is introduced.

## Test Criteria

- Valid membership/ownership relationships are created via
  `RelationshipManager`.
- Systems ignore incomplete or invalid graph patterns without corrupting
  state.
- Material changes create immutable events.
- The example uses only public engine/manager APIs and `make` passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/05_organizations_and_settlements-report.md`.
Report graph conventions, manager-only mutation evidence, event behavior,
example result, and validation results.

## Boundary

- Touch only stated organization/settlement systems, tests, examples, engine
  registration, fixtures, and docs, plus the approved report artifact.
- Do not implement construction, roads, housing, economy, or NPC behavior.
