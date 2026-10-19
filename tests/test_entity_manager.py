import pytest

from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.state.world_state import WorldState


def test_create_entity():
    state = WorldState()

    definitions = DefinitionManager()

    definitions.register(
        Definition(
            key="location",
        )
    )

    manager = EntityManager(
        state,
        definitions,
    )

    entity = manager.create(
        definition_key="location",
        name="Village",
    )

    assert entity.id == "entity_000001"

    assert entity.definition_key == "location"

    assert entity.name == "Village"

    assert manager.exists(entity.id)


def test_current_tick_destruction_validation_and_consequence_removal_guards() -> None:
    import pytest

    from living_world.needs import ConsumptionPolicy
    from living_world.simulation.simulation_engine import SimulationEngine

    engine = SimulationEngine()
    engine.definitions.register(Definition("location"))
    entity = engine.entities.create(definition_key="location", name="Village")
    with pytest.raises(TypeError):
        engine.entities.mark_destroyed(entity.id, True)
    with pytest.raises(ValueError):
        engine.entities.mark_destroyed(entity.id, 1)
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_village", entity.id, 1, 1)
    )
    with pytest.raises(ValueError, match="consequence policy"):
        engine.entities.remove(entity.id)


def test_work_history_forever_guards_removal_but_release_allows_labor_destruction() -> (
    None
):
    from test_work_orders import _create, _engine

    engine, settlement_id, npc_id = _engine()
    work = _create(engine, settlement_id)
    engine.work.mark_ready(work.id)
    engine.work.assign_and_reserve(work.id, (npc_id,))
    with pytest.raises(ValueError, match="spatial state|work history"):
        engine.entities.remove(npc_id)
    with pytest.raises(ValueError, match="required by nonterminal work"):
        engine.entities.mark_destroyed(npc_id, engine.state.tick)
    engine.work.block(work.id, "Released.")
    engine.spatial.remove(npc_id)
    engine.entities.mark_destroyed(npc_id, engine.state.tick)
    with pytest.raises(ValueError, match="work history"):
        engine.entities.remove(npc_id)
