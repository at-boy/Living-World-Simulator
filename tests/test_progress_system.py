from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def create_engine() -> SimulationEngine:
    engine = SimulationEngine()

    engine.definitions.register(
        Definition(
            key="progress_test",
        )
    )

    return engine


def create_entity(
    engine: SimulationEngine,
    *,
    progress: int,
    progress_rate: int,
    progress_min: int | None = None,
    progress_max: int | None = None,
):
    attributes: dict[str, object] = {
        "progress": progress,
        "progress_rate": progress_rate,
    }

    if progress_min is not None:
        attributes["progress_min"] = progress_min

    if progress_max is not None:
        attributes["progress_max"] = progress_max

    return engine.entities.create(
        definition_key="progress_test",
        name="Progress Test",
        attributes=attributes,
    )


def test_progress_advances_without_bounds():
    engine = create_engine()

    entity = create_entity(
        engine,
        progress=95,
        progress_rate=10,
    )

    engine.step()

    assert entity.attributes["progress"] == 105


def test_progress_clamps_to_maximum():
    engine = create_engine()

    entity = create_entity(
        engine,
        progress=95,
        progress_rate=10,
        progress_max=100,
    )

    engine.step()

    assert entity.attributes["progress"] == 100


def test_progress_clamps_to_minimum():
    engine = create_engine()

    entity = create_entity(
        engine,
        progress=3,
        progress_rate=-10,
        progress_min=0,
    )

    engine.step()

    assert entity.attributes["progress"] == 0


def test_progress_stays_at_maximum():
    engine = create_engine()

    entity = create_entity(
        engine,
        progress=100,
        progress_rate=5,
        progress_max=100,
    )

    engine.step()

    assert entity.attributes["progress"] == 100


def test_progress_stays_at_minimum():
    engine = create_engine()

    entity = create_entity(
        engine,
        progress=0,
        progress_rate=-5,
        progress_min=0,
    )

    engine.step()

    assert entity.attributes["progress"] == 0
