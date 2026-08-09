import pytest

from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_population_is_bounded_and_records_change() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="region", systems=("population",)))
    region = engine.entities.create(
        definition_key="region",
        name="Northreach",
        attributes={
            "population": 98,
            "population_change": 5,
            "population_min": 0,
            "population_max": 100,
        },
    )

    engine.step()

    assert region.attributes["population"] == 100
    event = next(iter(engine.state.events.values()))
    assert event.kind == "population_changed"
    assert event.subject_id == region.id
    assert event.attributes == {"previous": 98, "population": 100, "change": 2}


def test_population_ignores_non_participating_entities() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="terrain"))
    terrain = engine.entities.create(
        definition_key="terrain",
        name="Granite Ridge",
        attributes={"population": 4, "population_change": 3},
    )

    engine.step()

    assert terrain.attributes["population"] == 4
    assert not engine.state.events


@pytest.mark.parametrize(
    "attributes",
    [
        {"population_change": 1},
        {"population": 1, "population_min": 4, "population_max": 3},
        {"population": 1, "population_change": 0.5},
    ],
)
def test_population_rejects_invalid_configuration(
    attributes: dict[str, object],
) -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="region", systems=("population",)))
    engine.entities.create(
        definition_key="region", name="Northreach", attributes=attributes
    )

    with pytest.raises((TypeError, ValueError)):
        engine.step()


def test_weather_and_population_results_do_not_depend_on_entity_registration_order() -> (
    None
):
    def run(names: tuple[str, str]) -> dict[str, tuple[object, object]]:
        engine = SimulationEngine()
        engine.definitions.register_many(
            (
                Definition(key="region", systems=("weather", "population")),
                Definition(key="terrain", systems=("weather",)),
            )
        )
        for name in names:
            engine.entities.create(
                definition_key="region" if name == "region" else "terrain",
                name=name,
                attributes=(
                    {
                        "weather_cycle": ["clear", "rain"],
                        "population": 10,
                        "population_change": 2,
                    }
                    if name == "region"
                    else {"weather_cycle": ["wind", "calm"]}
                ),
            )
        engine.step()
        return {
            entity.name: (
                entity.attributes["weather"],
                entity.attributes.get("population"),
            )
            for entity in engine.entities.all()
        }

    assert run(("region", "terrain")) == run(("terrain", "region"))
