from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


def test_trade_uses_roads_and_resource_operations() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="settlement"))
    source = engine.entities.create(
        definition_key="settlement",
        name="Oakstead",
        attributes={"resources": {"wood": 5}},
    )
    target = engine.entities.create(definition_key="settlement", name="Riverford")
    road = engine.relationships.create(
        kind="road", source_id=target.id, target_id=source.id
    )
    trade = engine.relationships.create(
        kind="trade",
        source_id=source.id,
        target_id=target.id,
        attributes={"resource": "wood", "amount": 3},
    )

    engine.step()

    assert source.attributes["resources"] == {"wood": 2}
    assert target.attributes["resources"] == {"wood": 3}
    assert engine.relationships.get(road.id) is road
    assert engine.relationships.get(trade.id) is trade
    event = next(iter(engine.state.events.values()))
    assert event.kind == "trade_completed"
    assert event.attributes["amount"] == 3


def test_trade_without_resources_or_a_road_does_not_mutate_entities() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition(key="settlement"))
    source = engine.entities.create(
        definition_key="settlement",
        name="Oakstead",
        attributes={"resources": {"wood": 1}},
    )
    target = engine.entities.create(definition_key="settlement", name="Riverford")
    engine.relationships.create(
        kind="trade",
        source_id=source.id,
        target_id=target.id,
        attributes={"resource": "wood", "amount": 2},
    )

    engine.step()

    assert source.attributes["resources"] == {"wood": 1}
    assert "resources" not in target.attributes
    assert not engine.state.events
