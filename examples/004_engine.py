from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.systems.progress_system import ProgressSystem

engine = SimulationEngine()

engine.definitions.register(
    Definition(
        key="field",
    )
)

field = engine.entities.create(
    definition_key="field",
    name="Wheat Field",
    attributes={
        "progress": 95,
        "progress_rate": 3,
        "progress_max": 100,
    },
)

engine.register_system(
    ProgressSystem(
        engine.entities,
    )
)

print("Simulation Engine")

for _ in range(10):
    print(
        f"Tick {engine.state.tick}: "
        f"progress={field.attributes['progress']} "
        f"progress_rate={field.attributes['progress_rate']} "
        f"progress_max={field.attributes['progress_max']}"
    )

    engine.step()