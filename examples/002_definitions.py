from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager

manager = DefinitionManager()

manager.register(
    Definition(
        name="bridge",
        properties={
            "completion": 0,
            "durability": 100,
        },
        systems=("construction", "maintenance"),
    )
)

bridge = manager.get("bridge")
print(bridge)
