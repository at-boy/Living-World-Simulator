from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import (
    SimulationEngine,
)
from living_world.systems.resource_system import ResourceSystem


engine = SimulationEngine()

engine.definitions.register(
    Definition(
        key="container",
    )
)

source = engine.entities.create(
    definition_key="container",
    name="Warehouse",
)

target = engine.entities.create(
    definition_key="container",
    name="Cart",
)

resources = ResourceSystem()

resources.add(
    source,
    "wood",
    100,
)

resources.transfer(
    source,
    target,
    "wood",
    25,
)

print(source.name)
print(resources.get(source, "wood"))
print()

print(target.name)
print(resources.get(target, "wood"))