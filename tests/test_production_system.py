from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_production_consumes_inputs_and_never_makes_resources_negative() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="workshop", systems=("production",)))
    workshop = engine.entities.create(
        definition_key="workshop",
        name="Sawmill",
        attributes={
            "production_inputs": {"wood": 2},
            "production_outputs": {"plank": 1},
            "resources": {"wood": 2},
        },
    )

    engine.step()
    engine.step()

    assert workshop.attributes["resources"] == {"wood": 0, "plank": 1}
    events = tuple(engine.state.events.values())
    assert len(events) == 1
    assert events[0].kind == "production_completed"


def test_production_is_deterministic_for_identical_worlds() -> None:
    def run_once() -> tuple[dict[str, object], tuple[tuple[str, object], ...]]:
        engine = SimulationEngine()
        engine.definitions.register(Definition(key="farm", systems=("production",)))
        farm = engine.entities.create(
            definition_key="farm",
            name="Farm",
            attributes={
                "production_inputs": {"seed": 1},
                "production_outputs": {"grain": 3},
                "resources": {"seed": 1},
            },
        )
        engine.step()
        return (
            farm.attributes,
            tuple(
                (event.kind, event.attributes) for event in engine.state.events.values()
            ),
        )

    assert run_once() == run_once()
