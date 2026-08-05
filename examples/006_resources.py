from living_world.core.definition import Definition
from living_world.core.resource_definition import ResourceDefinition
from living_world.simulation.simulation_engine import (
    SimulationEngine,
)


engine = SimulationEngine()

engine.resource_definitions.register(
    ResourceDefinition(
        key="wood",
    )
)

engine.resource_definitions.register(
    ResourceDefinition(
        key="water",
    )
)

engine.definitions.register(
    Definition(
        key="tree",
    )
)

tree = engine.entities.create(
    definition_key="tree",
    name="Oak",
    attributes={
        "resources": {
            "wood": 120,
            "water": 35,
        }
    },
)

print(tree.name)
print()

print("Resources")

resources = tree.attributes["resources"]

if not isinstance(resources, dict):
    raise TypeError("'resources' must be a dictionary.")

resource_map: dict[str, object] = resources

for resource, quantity in resource_map.items():
    print(resource, quantity)