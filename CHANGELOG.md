# Changelog

## v0.2.2 (Unreleased)

### Added

- `make` now performs the complete development validation workflow.
- `make examples` executes every example in a defined order.
- Snapshot creation helper (`tools/create_snapshot.sh`).

### Changed

- Examples are now treated as executable documentation.
- Development workflow documentation updated to reflect the new tooling.

## v0.2.1 (Unreleased)

### Added

- Development workflow documentation.
- Standardized Architecture Decision Record format.

### Changed

- Architecture Decision Records now follow a consistent naming convention
  and structure.
- Development practices are formally documented.

## v0.1.5 (Unreleased)

### Added

- `SimulationEngine` façade for composing the runtime.
- Engine-level system registration.
- Engine-level simulation execution.
- SimulationEngine test coverage.
- Public API example (`004_engine.py`).

### Changed

- Runtime components can now be accessed through `SimulationEngine`.

## v0.1.4 (Unreleased)

### Added

- `SimulationScheduler` for deterministic execution of simulation systems.
- Abstract `SimulationSystem` base class.
- Initial `ProgressSystem`.
- Scheduler test coverage.
- Scheduler example demonstrating world evolution.

### Changed

- Simulation tick now advances through the scheduler.

## v0.1.3 (Unreleased)

### Added

- Immutable `Event` runtime object.
- `EventManager` for recording world history.
- Event identifier generation.
- Event timestamps based on simulation ticks.
- EventManager test coverage.

### Changed

- `WorldState` now stores events by identifier.
- Examples demonstrate recording world history.

## v0.1.3 (Unreleased)

### Added

- Relationship lifecycle managed by `RelationshipManager.create()`.
- Automatic relationship identifier generation.
- Relationship validation during creation.
- RelationshipManager test coverage.

### Changed

- Runtime relationships are now created exclusively through `RelationshipManager`.
- Examples no longer mutate `WorldState` directly.
- Managers are now the exclusive mutation boundary of the simulation runtime.

## v0.1.3 (Unreleased)

### Added

- Entity lifecycle managed by `EntityManager.create()`.
- Dependency injection between `EntityManager` and `DefinitionManager`.
- Automatic entity ID generation.
- Initial attribute application from definitions.

### Changed

- `Definition.attributes` renamed to `Definition.initial_attributes`.
- Examples now demonstrate entity lifecycle through `EntityManager`.
- Tests updated to validate entity creation instead of direct insertion.

## v0.1.3 (Unreleased)

### Changed

- Replaced Location with Entity.
- Replaced Connection with Relationship.
- WorldState now stores entities and relationships.
- Introduced EntityManager.

### Removed

- GraphManager
- Location
- Connection

## v0.1.2

### Added
- ADR-0001: World is a Property Graph
- ADR-0002: Simulation Owns Truth
- ADR-0003: Core Runtime Model
- docs/core_model.md
- Definition class
- DefinitionManager skeleton
- Relationship class
- RelationshipManager skeleton

### Changed
- Architecture documentation aligned with property graph model.
