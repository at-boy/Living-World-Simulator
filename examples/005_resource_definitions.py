from living_world.core.resource_definition import ResourceDefinition
from living_world.simulation.simulation_engine import SimulationEngine


engine = SimulationEngine()

engine.resource_definitions.register(
    ResourceDefinition(
        key="water",
    )
)

engine.resource_definitions.register(
    ResourceDefinition(
        key="wood",
    )
)

engine.resource_definitions.register(
    ResourceDefinition(
        key="food",
    )
)

print("Registered resources")

for key in (
    "water",
    "wood",
    "food",
):
  print(
      engine.resource_definitions.get(key)
  )