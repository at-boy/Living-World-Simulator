from __future__ import annotations

import pytest

from living_world.core.definition import Definition
from living_world.needs import (
    NeedAssessment,
    NeedAssessmentSystem,
    NeedDefinition,
    NeedKind,
    NeedLevel,
)
from living_world.simulation.simulation_engine import SimulationEngine


def _engine(*, population: int | None = 10) -> tuple[SimulationEngine, str]:
    engine = SimulationEngine()
    engine.definitions.register(Definition("settlement", {}))
    attributes: dict[str, object] = {"resources": {"food": 8, "water": 30}}
    if population is not None:
        attributes["population"] = population
    owner = engine.entities.create(
        definition_key="settlement", name="Harbor", attributes=attributes
    )
    return engine, owner.id


def _definition(
    owner_id: str,
    *,
    need_id: str = "need_food",
    kind: NeedKind = NeedKind.FOOD,
    window: int = 3,
) -> NeedDefinition:
    return NeedDefinition(need_id, owner_id, kind, 1, 0.2, 0.5, window)


def test_manager_creation_queries_interpretation_and_removal_guard() -> None:
    engine, owner_id = _engine(population=None)
    definition = engine.needs.create(_definition(owner_id))

    assert engine.needs.get(definition.id) == definition
    assert engine.needs.for_owner(owner_id) == (definition,)
    assert engine.needs.for_owner_kind(owner_id, NeedKind.FOOD) == definition
    assert engine.needs.npc_interpretations(owner_id)[0].label == "Food"
    assert engine.needs.npc_interpretation(definition.id).description == (
        "This need cannot yet be assessed."
    )
    assert [event.kind for event in engine.state.events.values()] == ["need_created"]
    with pytest.raises(ValueError, match="need refers"):
        engine.entities.remove(owner_id)


def test_definition_validation_and_owner_kind_uniqueness() -> None:
    engine, owner_id = _engine()
    engine.needs.create(_definition(owner_id))
    with pytest.raises(ValueError, match="only once"):
        engine.needs.create(_definition(owner_id, need_id="need_second"))
    with pytest.raises((TypeError, ValueError)):
        NeedDefinition("need_bad", owner_id, NeedKind.FOOD, True, 0.2, 0.5, 3)
    with pytest.raises(ValueError):
        NeedDefinition("bad", owner_id, NeedKind.FOOD, 1, 0.2, 0.5, 3)


def test_food_arithmetic_levels_history_and_events() -> None:
    engine, owner_id = _engine()
    definition = engine.needs.create(_definition(owner_id, window=2))
    system = NeedAssessmentSystem(engine.needs)

    system.step(engine.state)
    current = engine.state.need_states[definition.id].current
    assert current == NeedAssessment(0, NeedLevel.SECURE, 8, 10, -2, 0.2)
    assert [event.kind for event in engine.state.events.values()] == [
        "need_created",
        "need_level_changed",
    ]
    system.step(engine.state)
    assert len(engine.state.events) == 2

    engine.state.tick = 1
    engine.entities.set_attribute(
        entity_id=owner_id, key="resources", value={"food": 2}
    )
    system.step(engine.state)
    assert engine.state.need_states[definition.id].current.level is NeedLevel.CRITICAL
    engine.state.tick = 2
    engine.entities.set_attribute(
        entity_id=owner_id, key="resources", value={"food": 20}
    )
    system.step(engine.state)
    state = engine.state.need_states[definition.id]
    assert state.current.level is NeedLevel.SURPLUS
    assert tuple(item.tick for item in state.history) == (1, 2)


def test_missing_population_is_unavailable_then_transition_emits() -> None:
    engine, owner_id = _engine(population=None)
    definition = engine.needs.create(_definition(owner_id))
    system = NeedAssessmentSystem(engine.needs)
    system.step(engine.state)
    assert engine.state.need_states[definition.id].current == NeedAssessment(
        0, NeedLevel.UNAVAILABLE, None, None, None, None
    )
    assert len(engine.state.events) == 1
    engine.state.tick = 1
    engine.entities.set_attribute(entity_id=owner_id, key="population", value=10)
    system.step(engine.state)
    assert len(engine.state.events) == 2
    engine.state.tick = 2
    del engine.state.entities[owner_id].attributes["population"]
    system.step(engine.state)
    assert len(engine.state.events) == 3


def test_zero_population_and_shelter_storage_direct_ownership() -> None:
    engine, owner_id = _engine(population=0)
    engine.definitions.register(Definition("building", {}))
    building = engine.entities.create(
        definition_key="building",
        name="Hall",
        attributes={"housing_allocated": 7, "storage_capacity": 12},
    )
    engine.relationships.create(kind="owns", source_id=owner_id, target_id=building.id)
    engine.relationships.create(kind="owns", source_id=owner_id, target_id=owner_id)
    shelter = engine.needs.create(
        _definition(owner_id, need_id="need_shelter", kind=NeedKind.SHELTER)
    )
    storage = engine.needs.create(
        _definition(owner_id, need_id="need_storage", kind=NeedKind.STORAGE)
    )
    NeedAssessmentSystem(engine.needs).step(engine.state)
    assert engine.state.need_states[shelter.id].current.available == 7
    assert engine.state.need_states[storage.id].current.available == 12
    assert engine.state.need_states[shelter.id].current.pressure == 0


def test_self_ownership_does_not_double_count_owner_capacity() -> None:
    engine, owner_id = _engine(population=1)
    owner = engine.state.entities[owner_id]
    owner.attributes.update({"housing_allocated": 3, "storage_capacity": 4})
    engine.relationships.create(kind="owns", source_id=owner_id, target_id=owner_id)
    shelter = engine.needs.create(
        _definition(owner_id, need_id="need_shelter", kind=NeedKind.SHELTER)
    )
    storage = engine.needs.create(
        _definition(owner_id, need_id="need_storage", kind=NeedKind.STORAGE)
    )

    NeedAssessmentSystem(engine.needs).step(engine.state)

    assert engine.state.need_states[shelter.id].current.available == 3
    assert engine.state.need_states[storage.id].current.available == 4


def test_conflicting_same_tick_and_malformed_inputs_fail_closed() -> None:
    engine, owner_id = _engine()
    definition = engine.needs.create(_definition(owner_id))
    system = NeedAssessmentSystem(engine.needs)
    system.step(engine.state)
    with pytest.raises(ValueError, match="conflicting"):
        engine.needs.record_assessment(
            definition.id, NeedAssessment(0, NeedLevel.CRITICAL, 0, 10, -10, 1.0)
        )
    engine.state.tick = 1
    engine.state.entities[owner_id].attributes["resources"] = []
    with pytest.raises(TypeError, match="resources"):
        system.step(engine.state)
    assert engine.state.need_states[definition.id].current.tick == 0


def test_system_pass_is_atomic_when_later_need_fails() -> None:
    engine, owner_id = _engine()
    first = engine.needs.create(_definition(owner_id))
    engine.needs.create(
        _definition(owner_id, need_id="need_water", kind=NeedKind.WATER)
    )
    engine.state.entities[owner_id].attributes["resources"] = {"food": 8, "water": -1}
    original_events = dict(engine.state.events)
    with pytest.raises(ValueError):
        NeedAssessmentSystem(engine.needs).step(engine.state)
    assert engine.state.need_states[first.id].current is None
    assert engine.state.events == original_events


def test_creation_event_failure_rolls_back_need_and_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, owner_id = _engine()
    original_record = engine.events.record

    def fail_after_record(**values: object) -> object:
        original_record(**values)  # type: ignore[arg-type]
        raise RuntimeError("event sink failed")

    monkeypatch.setattr(engine.events, "record", fail_after_record)
    with pytest.raises(RuntimeError, match="event sink failed"):
        engine.needs.create(_definition(owner_id))
    assert engine.state.need_definitions == {}
    assert engine.state.need_states == {}
    assert engine.state.events == {}


def test_assessment_event_failure_rolls_back_state_and_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, owner_id = _engine()
    definition = engine.needs.create(_definition(owner_id))
    original_state = engine.state.need_states[definition.id]
    original_events = dict(engine.state.events)
    original_record = engine.events.record

    def fail_after_record(**values: object) -> object:
        original_record(**values)  # type: ignore[arg-type]
        raise RuntimeError("event sink failed")

    monkeypatch.setattr(engine.events, "record", fail_after_record)
    with pytest.raises(RuntimeError, match="event sink failed"):
        NeedAssessmentSystem(engine.needs).step(engine.state)
    assert engine.state.need_states[definition.id] == original_state
    assert engine.state.events == original_events


def test_engine_orders_late_system_before_needs_and_goals_last() -> None:
    engine, owner_id = _engine()
    definition = engine.needs.create(_definition(owner_id))

    class Replenish:
        def step(self, state: object) -> None:
            engine.state.entities[owner_id].attributes["resources"] = {"food": 10}

    engine.register_system(Replenish())  # type: ignore[arg-type]
    engine.step()
    assert engine.state.need_states[definition.id].current.available == 10


def test_same_tick_consumption_reduces_food_before_need_assessment() -> None:
    from living_world.needs import ConsumptionPolicy

    engine, owner_id = _engine(population=2)
    definition = engine.needs.create(_definition(owner_id))
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_town", owner_id, 2, 1)
    )
    engine.step()
    assert engine.state.need_states[definition.id].current.available == 4
