# YAML World-Definition Loader Report

## Accepted YAML Schema

`YAMLWorldDefinitionLoader` accepts a single top-level field:

```yaml
definitions:
  - key: oak_tree
    initial_attributes:
      health: 100
      resources:
        wood: 30
    systems:
      - growth
```

`definitions` is an ordered list. Each item requires a non-empty `key` and may
contain an `initial_attributes` mapping of recursive YAML scalar, mapping, and
list values plus a `systems` list of non-empty strings. Unknown top-level or
definition fields, duplicate YAML mapping keys, duplicate definition keys,
invalid mappings, recursive attributes, and unsupported attribute values are
rejected. The schema intentionally has no world-state serialization or
versioning policy: runtime IDs, ticks, events, and NPC cognitive records are
not accepted.

## Public API and Atomicity

- `WorldDefinitionLoader(Protocol).load(path: Path) -> tuple[Definition, ...]`
- `YAMLWorldDefinitionLoader.load(path: Path) -> tuple[Definition, ...]`
- `SimulationEngine.load_definitions(path: Path) -> tuple[Definition, ...]`
- `DefinitionManager.register_many(definitions)` validates the complete batch
  before updating its registry.

The loader completes all document validation before it returns definitions.
The engine subsequently performs one batch registration. Invalid YAML,
duplicate mapping keys, invalid attribute shapes, unknown schema fields, and
duplicate definition keys therefore leave existing definitions unchanged.

## Example Result

`examples/012_yaml_world.py` writes a temporary definition document, loads its
`oak_tree` vocabulary, and creates `Old Oak` solely through
`engine.entities.create()`. It prints the resulting runtime `Entity`; the YAML
document never supplies a runtime ID or tick.

## Validation

The package retains its established Python compatibility policy: Python 3.11
or newer is supported, and Black targets Python 3.11 syntax. PyYAML remains a
runtime dependency for the YAML definition loader. Python 3.13.5 was used as
the local validation runtime only.

`tests/test_yaml_loader.py` covers deterministic document order, nested initial
attributes, invalid YAML and schema inputs preserving an existing registry,
atomic valid engine loading, and rejected duplicate registration batches.

Validation completed successfully:

- `make` — passed.
- `make examples` — passed all 12 numbered examples, including
  `012_yaml_world.py`.
- `git diff --check` — passed.

## Exact Files Changed

- `CHANGELOG.md`
- `Makefile`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/03_yaml_world_definition_loader-report.md`
- `examples/012_yaml_world.py`
- `pyproject.toml`
- `src/living_world/core/definition.py`
- `src/living_world/definitions/__init__.py`
- `src/living_world/definitions/yaml_loader.py`
- `src/living_world/managers/definition_manager.py`
- `src/living_world/simulation/simulation_engine.py`
- `tests/test_yaml_loader.py`

## Boundary Compliance

All changes are limited to the Task 03-approved loader, definition-manager,
engine, configuration, documentation, example, and test files. No repository
implementation, runtime domain system, or complete `WorldState` YAML loading
was added.

## Blockers and Deferred Work

None.
