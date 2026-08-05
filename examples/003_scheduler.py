from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.simulation.simulation_scheduler import SimulationScheduler
from living_world.state.world_state import WorldState
from living_world.systems.progress_system import ProgressSystem

state = WorldState()

definitions = DefinitionManager()

definitions.register(
    Definition(
        key="field",
    )
)

entities = EntityManager(
    state,
    definitions,
)

field = entities.create(
    definition_key="field",
    name="Wheat Field",
    attributes={
        "progress": 95,
        "progress_rate": 3,
        "progress_max": 100,
    },
)

scheduler = SimulationScheduler(state)

scheduler.register(
    ProgressSystem(
        entities,
    )
)

print("Simulation")

for _ in range(10):
    print(
        f"Tick {state.tick}: "
        f"progress={field.attributes['progress']} "
        f"progress_rate={field.attributes['progress_rate']} "
        f"progress_max={field.attributes['progress_max']}"
    )

    scheduler.step()