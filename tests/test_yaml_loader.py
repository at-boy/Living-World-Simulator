from pathlib import Path

import pytest

from living_world.core.definition import Definition
from living_world.definitions.yaml_loader import (
    WorldDefinitionLoadError,
    YAMLWorldDefinitionLoader,
)
from living_world.simulation.simulation_engine import SimulationEngine


def write_definition_file(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "world_definitions.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_yaml_loader_loads_definitions_in_document_order(tmp_path: Path) -> None:
    path = write_definition_file(
        tmp_path,
        """\
definitions:
  - key: tree
    initial_attributes:
      health: 100
      resources:
        wood: 30
    systems:
      - growth
  - key: villager
    initial_attributes:
      energy: 80
""",
    )

    definitions = YAMLWorldDefinitionLoader().load(path)

    assert [definition.key for definition in definitions] == ["tree", "villager"]
    assert definitions[0].initial_attributes == {
        "health": 100,
        "resources": {"wood": 30},
    }
    assert definitions[0].systems == ("growth",)


@pytest.mark.parametrize(
    "content",
    [
        "definitions: [key: tree",
        """\
definitions:
  - key: tree
    initial_attributes:
      health: 100
      health: 50
""",
        """\
definitions:
  - key: tree
    initial_attributes:
      - health
""",
        """\
world_state:
  tick: 4
definitions: []
""",
        """\
definitions:
  - key: tree
  - key: tree
""",
    ],
)
def test_invalid_yaml_does_not_change_definition_registry(
    tmp_path: Path,
    content: str,
) -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="existing"))
    path = write_definition_file(tmp_path, content)

    with pytest.raises(WorldDefinitionLoadError):
        engine.load_definitions(path)

    assert [definition.key for definition in engine.definitions.all()] == ["existing"]


def test_engine_load_definitions_registers_validated_set_atomically(
    tmp_path: Path,
) -> None:
    engine = SimulationEngine()
    path = write_definition_file(
        tmp_path,
        """\
definitions:
  - key: oak
    initial_attributes:
      health: 100
  - key: bridge
    systems:
      - construction
""",
    )

    definitions = engine.load_definitions(path)

    assert definitions == engine.definitions.all()
    assert engine.definitions.get("oak").initial_attributes == {"health": 100}


def test_definition_manager_rejects_duplicate_batch_without_changes() -> None:
    manager = SimulationEngine().definitions
    manager.register(Definition(key="existing"))

    with pytest.raises(ValueError, match="Duplicate definition key 'oak'"):
        manager.register_many((Definition(key="oak"), Definition(key="oak")))

    assert [definition.key for definition in manager.all()] == ["existing"]
