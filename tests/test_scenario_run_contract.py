import json
import sqlite3
from collections.abc import MutableMapping
from pathlib import Path
from typing import cast

import pytest

from living_world.api.inspection import EngineWorldInspector
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.scenarios import (
    LoadedScenario,
    ScenarioEntity,
    ScenarioRelationship,
    ScenarioRuntimeManager,
)
from living_world.scenarios.scenario import (
    ScenarioCompatibilityError,
    ScenarioLoadError,
    YAMLScenarioLoader,
)
from living_world.simulation.simulation_engine import SimulationEngine


def _scenario(tmp_path: Path, *, seed: int = 7) -> Path:
    (tmp_path / "world.yaml").write_text(
        "definitions:\n  - key: settlement\n  - key: person\n",
        encoding="utf-8",
    )
    path = tmp_path / "scenario.yaml"
    path.write_text(
        f"""schema_version: 1
key: oakford
seed: {seed}
definitions: world.yaml
run:
  max_ticks: 12
  terminal_conditions: [tick_limit]
entities:
  - label: town
    definition: settlement
    name: Oakford
    attributes:
      nested:
        value: 1
  - label: founder
    definition: person
    name: Rhea
relationships:
  - kind: member_of
    source: founder
    target: town
""",
        encoding="utf-8",
    )
    return path


def test_scenario_loads_and_instantiates_deterministically(tmp_path: Path) -> None:
    engine = SimulationEngine()

    scenario = engine.load_scenario(_scenario(tmp_path))

    assert scenario.key == "oakford"
    assert scenario.default_max_ticks == 12
    assert engine.state.run_metadata == scenario.run_metadata
    assert tuple(engine.state.entities) == ("entity_000001", "entity_000002")
    assert tuple(engine.state.relationships) == ("relationship_000001",)
    assert EngineWorldInspector(engine).run_metadata() == {
        "scenario_key": "oakford",
        "schema_version": 1,
        "seed": 7,
        "configuration_fingerprint": scenario.configuration_fingerprint,
    }
    nested = cast(
        MutableMapping[str, object], scenario.entities[0].attributes["nested"]
    )
    with pytest.raises(TypeError):
        nested["value"] = 99
    assert engine.state.entities["entity_000001"].attributes["nested"] == {"value": 1}
    context = NPCContextAssembler(engine.state).assemble(holder_id="entity_000002")
    assert context.identity == "Rhea"
    assert scenario.configuration_fingerprint not in repr(context)
    assert str(scenario.seed) not in repr(context)


def test_loading_same_scenario_is_idempotent(tmp_path: Path) -> None:
    engine = SimulationEngine()
    path = _scenario(tmp_path)
    first = engine.load_scenario(path)

    second = engine.load_scenario(path)

    assert len(engine.state.entities) == 2
    assert len(engine.state.relationships) == 1
    assert first.configuration_fingerprint == second.configuration_fingerprint


def test_resume_reloads_definitions_and_rejects_changed_scenario(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    path = _scenario(tmp_path)
    engine = SimulationEngine(repository)
    engine.load_scenario(path)
    engine.save_world()

    resumed = SimulationEngine(repository)
    resumed.load_scenario(path)
    assert resumed.definitions.exists("settlement")

    changed = _scenario(tmp_path, seed=8)
    with pytest.raises(ScenarioCompatibilityError, match="does not match"):
        resumed.load_scenario(changed)


def test_resume_rejects_changed_definition_document(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    path = _scenario(tmp_path)
    engine = SimulationEngine(repository)
    engine.load_scenario(path)
    engine.save_world()
    (tmp_path / "world.yaml").write_text(
        "definitions:\n  - key: settlement\n  - key: person\n  - key: farm\n",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioCompatibilityError, match="does not match"):
        SimulationEngine(repository).load_scenario(path)


def test_loader_rejects_escaping_definition_path(tmp_path: Path) -> None:
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "schema_version: 1\nkey: bad\nseed: 1\ndefinitions: ../world.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioLoadError, match="escape"):
        YAMLScenarioLoader().load(path)

    path.write_text(
        "schema_version: 1\nkey: bad\nseed: 1\ndefinitions: /tmp/world.yaml\n",
        encoding="utf-8",
    )
    with pytest.raises(ScenarioLoadError, match="must be relative"):
        YAMLScenarioLoader().load(path)


def test_loader_rejects_duplicate_labels_and_boolean_seed(tmp_path: Path) -> None:
    path = _scenario(tmp_path)
    text = path.read_text(encoding="utf-8").replace("seed: 7", "seed: true")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="seed must be an integer"):
        YAMLScenarioLoader().load(path)


def test_loader_rejects_duplicate_labels_unknown_fields_and_internal_ids(
    tmp_path: Path,
) -> None:
    path = _scenario(tmp_path)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("label: founder", "label: town"), encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="Duplicate entity label"):
        YAMLScenarioLoader().load(path)

    path.write_text(text + "unknown: true\n", encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="Unknown scenario field"):
        YAMLScenarioLoader().load(path)

    path.write_text(text.replace("name: Rhea", "name: entity_000001"), encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="internal record ID"):
        YAMLScenarioLoader().load(path)


def test_loader_rejects_duplicate_yaml_invalid_reference_and_version(
    tmp_path: Path,
) -> None:
    path = _scenario(tmp_path)
    text = path.read_text(encoding="utf-8")
    path.write_text("schema_version: 1\n" + text, encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="Duplicate YAML key"):
        YAMLScenarioLoader().load(path)

    path.write_text(text.replace("target: town", "target: absent"), encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="reference entity labels"):
        YAMLScenarioLoader().load(path)

    path.write_text(
        text.replace("schema_version: 1", "schema_version: 2"), encoding="utf-8"
    )
    with pytest.raises(ScenarioLoadError, match="Unsupported scenario schema"):
        YAMLScenarioLoader().load(path)


@pytest.mark.parametrize(
    "nested_mapping",
    ("        1: value", "        1: value\n        '1': other"),
)
def test_loader_rejects_nested_non_string_attribute_keys(
    tmp_path: Path, nested_mapping: str
) -> None:
    path = _scenario(tmp_path)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("        value: 1", nested_mapping),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioLoadError, match="mappings with string keys"):
        YAMLScenarioLoader().load(path)


def test_engine_rejects_unknown_definitions_and_populated_legacy_world(
    tmp_path: Path,
) -> None:
    path = _scenario(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "definition: person", "definition: missing"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ScenarioCompatibilityError, match="unknown definition"):
        SimulationEngine().load_scenario(path)

    path = _scenario(tmp_path)
    engine = SimulationEngine()
    engine.definitions.register(Definition("person"))
    engine.entities.create(definition_key="person", name="Existing")
    with pytest.raises(ScenarioCompatibilityError, match="populated legacy"):
        engine.load_scenario(path)


def test_runtime_binding_is_atomic_when_staging_fails(tmp_path: Path) -> None:
    state = SimulationEngine().state
    definitions = DefinitionManager()
    manager = ScenarioRuntimeManager(state, definitions)
    scenario = LoadedScenario(
        source_path=tmp_path / "scenario.yaml",
        key="atomic",
        schema_version=1,
        seed=1,
        definition_path=tmp_path / "world.yaml",
        default_max_ticks=1,
        terminal_conditions=(),
        entities=(ScenarioEntity("person", "person", "Rhea"),),
        relationships=(ScenarioRelationship("", "person", "person"),),
        configuration_fingerprint="fingerprint",
    )

    with pytest.raises(ValueError, match="kind cannot be empty"):
        manager.bind(scenario, (Definition("person"),))

    assert state.run_metadata is None
    assert state.entities == {}
    assert state.relationships == {}
    assert definitions.all() == ()


def test_schema_one_snapshot_loads_without_run_metadata_and_rewrites(
    tmp_path: Path,
) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    repository.save_world(SimulationEngine().state)
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM world_snapshots WHERE id = 1"
            ).fetchone()[0]
        )
        del payload["run_metadata"]
        connection.execute(
            "UPDATE world_snapshots SET schema_version = 1, payload = ?",
            (json.dumps(payload),),
        )

    state = repository.load_world()
    assert state.run_metadata is None
    repository.save_world(state)
    with sqlite3.connect(database) as connection:
        version = connection.execute(
            "SELECT schema_version FROM world_snapshots WHERE id = 1"
        ).fetchone()[0]
    assert version == 9
