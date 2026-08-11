# Task 05 — Organizations and Settlement Foundations Report

## Outcome

Task 05 adds deterministic property-graph interpretation for organizations
and settlements without introducing domain-specific runtime classes.

## Graph Conventions

- `member_of` points from a member entity to an organization entity.
- `owns` points from an owner entity to a settlement entity.
- `located_in` points from a settlement entity to its location entity.

`OrganizationSystem` derives a unique `member_count` from valid incoming
`member_of` relationships. `SettlementSystem` requires exactly one valid
outgoing `located_in` relationship before deriving `is_located` and a unique
`owner_count` from incoming `owns` relationships. Invalid, incomplete, or
ambiguous graph patterns are ignored.

## Public Interfaces Added or Changed

- `OrganizationSystem(SimulationSystem)` with
  `step(self, state: WorldState) -> None`.
- `SettlementSystem(SimulationSystem)` with
  `step(self, state: WorldState) -> None`.
- `SimulationEngine` registers organization then settlement systems after the
  existing weather and population systems.

## Manager and Event Evidence

Both systems read graph structure but write entity attributes only through
`EntityManager.set_attribute()`. They record material summary changes only
through `EventManager.record()`: `organization_membership_changed`,
`settlement_location_changed`, and `settlement_ownership_changed`. Tests
assert field-level immutability of the resulting events.

## Tests and Validation

- `tests/test_organization_system.py` covers manager-created memberships,
  unique-member derivation, field-level event immutability, and ignored invalid
  patterns.
- `tests/test_settlement_system.py` covers manager-created location and
  ownership relationships, derived summaries, field-level event immutability,
  and ignored ambiguous/incomplete patterns.
- `examples/015_settlement_foundations.py` uses only public engine and manager
  APIs and prints the graph-derived organization and settlement summaries.

Commands run successfully:

```text
make
make examples
git diff --check
```

`make` completed Ruff, Black, pytest (**156 passed**), and all fifteen
numbered examples. `make examples` also completed all fifteen examples.

## Documentation Updated

- `docs/core_model.md`
- `docs/engine_glossary.md`
- `CHANGELOG.md`
- `docs/project_journal.md`

## Exact Files Changed

- `CHANGELOG.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/05_organizations_and_settlements-report.md`
- `examples/015_settlement_foundations.py`
- `src/living_world/simulation/simulation_engine.py`
- `src/living_world/systems/organization_system.py`
- `src/living_world/systems/settlement_system.py`
- `tests/test_organization_system.py`
- `tests/test_settlement_system.py`

## Boundary Compliance

Only Task 05 implementation, test, example, engine-registration,
documentation, and approved report files were changed. No bespoke
organization, settlement, kingdom, village, group, or location runtime class
was added. Construction, roads, housing, economy, and NPC behavior remain
deferred.

## Blockers and Deferred Work

Runtime `Event.attributes` remains mutable, including the attributes of
manager-created events. This task tested field-level immutability only. A
separate corrective task is required before historical event attributes can be
treated as truly immutable.
