# 03 — YAML world-definition loading

## Task Description

Add validated, atomic loading of YAML definition vocabulary before runtime
entities are created, without treating YAML as a serialized world state.

## Context Needed

- Create: `docs/subagent_execution_plan/03_yaml_world_definition_loader-report.md`.
- Create: `src/living_world/definitions/yaml_loader.py`,
  `src/living_world/definitions/__init__.py`, `tests/test_yaml_loader.py`,
  `examples/012_yaml_world.py`.
- Edit: `src/living_world/core/definition.py`,
  `src/living_world/managers/definition_manager.py`,
  `src/living_world/simulation/simulation_engine.py`, `pyproject.toml`,
  `Makefile`.
- Edit docs: `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`,
  `docs/project_journal.md`; create an ADR if the loader establishes a new
  schema/versioning policy.
- Know: `Definition`, `DefinitionManager`, `EntityManager`, and the repository
  abstraction from Task 02.

## Interface Contract

```python
class WorldDefinitionLoader(Protocol):
    def load(self, path: Path) -> tuple[Definition, ...]: ...

class YAMLWorldDefinitionLoader:
    def load(self, path: Path) -> tuple[Definition, ...]: ...
```

- YAML contains only definition vocabulary and initial attributes; runtime
  entity IDs, ticks, events, and NPC cognitive records are not accepted.
- The loader validates duplicate keys, invalid attribute shapes, and unknown
  top-level schema fields before registering anything.
- `SimulationEngine.load_definitions(path: Path) -> tuple[Definition, ...]`
  registers a fully validated set atomically.

## Test Criteria

- Valid YAML loads definitions in deterministic order.
- Invalid YAML, duplicate keys, and invalid schema leave the registry
  unchanged.
- The example creates runtime entities only through `EntityManager`.
- `make` includes the new example and passes.

## Orchestrator Report

Create `docs/subagent_execution_plan/03_yaml_world_definition_loader-report.md`.
Report the accepted YAML schema, atomicity/error-case evidence, public API,
example result, and validation results.

## Boundary

- Touch only the listed loader, definition, engine, test, example,
  configuration, and documentation files, plus the approved report artifact.
- Ignore domain systems and do not load a complete `WorldState` from YAML.
- Adhere to the architectural flow: YAML definition -> loader -> world state.
