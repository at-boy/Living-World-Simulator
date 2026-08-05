from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager


def test_register_definition():
    manager = DefinitionManager()

    manager.register(
        Definition(
            key="bridge",
        )
    )

    assert manager.exists("bridge")
