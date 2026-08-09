import pytest

from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_weather_cycle_is_deterministic_and_records_material_changes() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="region", systems=("weather",)))
    region = engine.entities.create(
        definition_key="region",
        name="Northreach",
        attributes={"weather": "clear", "weather_cycle": ["clear", "rain"]},
    )

    engine.run(3)

    assert region.attributes["weather"] == "clear"
    assert region.attributes["weather_index"] == 1
    assert [
        (event.kind, event.attributes) for event in engine.state.events.values()
    ] == [
        ("weather_changed", {"previous": "clear", "weather": "rain"}),
        ("weather_changed", {"previous": "rain", "weather": "clear"}),
    ]


def test_weather_ignores_definitions_without_weather_opt_in() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="terrain"))
    terrain = engine.entities.create(
        definition_key="terrain",
        name="Granite Ridge",
        attributes={"weather": "still", "weather_cycle": ["wind"]},
    )

    engine.step()

    assert terrain.attributes == {"weather": "still", "weather_cycle": ["wind"]}
    assert not engine.state.events


@pytest.mark.parametrize(
    ("attributes", "exception"),
    [
        ({"weather_cycle": []}, ValueError),
        ({"weather_cycle": "rain"}, TypeError),
        ({"weather_cycle": ["rain"], "weather_index": "zero"}, TypeError),
    ],
)
def test_weather_rejects_invalid_configuration(
    attributes: dict[str, object], exception: type[Exception]
) -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="region", systems=("weather",)))
    engine.entities.create(
        definition_key="region", name="Northreach", attributes=attributes
    )

    with pytest.raises(exception):
        engine.step()
