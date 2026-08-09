import pytest

from living_world.managers.observation_manager import ObservationManager
from living_world.state.world_state import WorldState


def test_record_creates_and_registers_observation() -> None:
    state = WorldState(tick=42)
    manager = ObservationManager(state)

    observation = manager.record(
        observer="entity_000001",
        subject="entity_000002",
        description="The tree appears healthy.",
        confidence=0.85,
        evidence={
            "health": 92,
        },
        metadata={
            "engine": "deterministic",
        },
    )

    assert observation.id == "observation_000001"
    assert observation.tick == 42
    assert observation.observer == "entity_000001"
    assert observation.subject == "entity_000002"
    assert observation.description == "The tree appears healthy."
    assert observation.confidence == 0.85

    assert manager.get("observation_000001") is observation
    assert state.observations["observation_000001"] is observation


def test_observation_ids_are_unique() -> None:
    state = WorldState()
    manager = ObservationManager(state)

    first = manager.record(
        observer="entity_000001",
        subject="entity_000002",
        description="The tree appears healthy.",
        confidence=0.8,
    )

    second = manager.record(
        observer="entity_000001",
        subject="entity_000003",
        description="The river is flowing.",
        confidence=0.9,
    )

    assert first.id == "observation_000001"
    assert second.id == "observation_000002"


def test_observations_for_returns_observer_history() -> None:
    state = WorldState()
    manager = ObservationManager(state)

    first = manager.record(
        observer="entity_000001",
        subject="entity_000002",
        description="The tree appears healthy.",
        confidence=0.8,
    )

    second = manager.record(
        observer="entity_000001",
        subject="entity_000003",
        description="The river is flowing.",
        confidence=0.9,
    )

    manager.record(
        observer="entity_000004",
        subject="entity_000002",
        description="The tree appears mature.",
        confidence=0.7,
    )

    assert manager.observations_for("entity_000001") == (
        first,
        second,
    )


def test_all_returns_all_observations() -> None:
    state = WorldState()
    manager = ObservationManager(state)

    first = manager.record(
        observer="entity_000001",
        subject="entity_000002",
        description="The tree appears healthy.",
        confidence=0.8,
    )

    second = manager.record(
        observer="entity_000002",
        subject="entity_000001",
        description="Erik is nearby.",
        confidence=0.9,
    )

    assert manager.all() == (
        first,
        second,
    )


def test_record_rejects_empty_observer() -> None:
    manager = ObservationManager(WorldState())

    with pytest.raises(ValueError, match="Observation observer cannot be empty."):
        manager.record(
            observer="",
            subject="entity_000002",
            description="The tree appears healthy.",
            confidence=0.8,
        )


def test_record_rejects_empty_subject() -> None:
    manager = ObservationManager(WorldState())

    with pytest.raises(ValueError, match="Observation subject cannot be empty."):
        manager.record(
            observer="entity_000001",
            subject="",
            description="The tree appears healthy.",
            confidence=0.8,
        )


def test_record_rejects_empty_description() -> None:
    manager = ObservationManager(WorldState())

    with pytest.raises(
        ValueError,
        match="Observation description cannot be empty.",
    ):
        manager.record(
            observer="entity_000001",
            subject="entity_000002",
            description="",
            confidence=0.8,
        )


def test_record_rejects_confidence_below_zero() -> None:
    manager = ObservationManager(WorldState())

    with pytest.raises(
        ValueError,
        match="Observation confidence must be between 0.0 and 1.0.",
    ):
        manager.record(
            observer="entity_000001",
            subject="entity_000002",
            description="The tree appears healthy.",
            confidence=-0.1,
        )


def test_record_rejects_confidence_above_one() -> None:
    manager = ObservationManager(WorldState())

    with pytest.raises(
        ValueError,
        match="Observation confidence must be between 0.0 and 1.0.",
    ):
        manager.record(
            observer="entity_000001",
            subject="entity_000002",
            description="The tree appears healthy.",
            confidence=1.1,
        )


def test_observation_is_immutable_after_recording() -> None:
    manager = ObservationManager(WorldState())

    observation = manager.record(
        observer="entity_000001",
        subject="entity_000002",
        description="The tree appears healthy.",
        confidence=0.8,
    )

    with pytest.raises(AttributeError):
        observation.description = "Something else"
