import pytest

from living_world.core.belief import BeliefStatus
from living_world.managers.belief_manager import BeliefManager
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


def test_record_creates_and_registers_belief() -> None:
    state = WorldState(tick=42)
    manager = BeliefManager(state)

    belief = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.82,
        importance=0.65,
        status=BeliefStatus.ACTIVE,
        supporting_observations=("observation_000001",),
        supporting_memories=("memory_000001",),
        metadata={"source": "deterministic_perception"},
    )

    assert belief.id == "belief_000001"
    assert belief.tick == 42
    assert belief.holder_id == "entity_000001"
    assert belief.subject_id == "entity_000002"
    assert belief.status is BeliefStatus.ACTIVE
    assert manager.get("belief_000001") is belief
    assert state.beliefs["belief_000001"] is belief


def test_belief_ids_are_unique() -> None:
    manager = BeliefManager(WorldState())

    first = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.8,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    second = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000003",
        proposition="The river is safe.",
        confidence=0.7,
        importance=0.5,
        status=BeliefStatus.ACTIVE,
    )

    assert first.id == "belief_000001"
    assert second.id == "belief_000002"


def test_beliefs_for_returns_holder_history() -> None:
    manager = BeliefManager(WorldState())

    first = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.8,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    second = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000003",
        proposition="The river is safe.",
        confidence=0.7,
        importance=0.5,
        status=BeliefStatus.WEAKENED,
    )

    manager.record(
        holder_id="entity_000004",
        subject_id="entity_000002",
        proposition="The oak is dangerous.",
        confidence=0.3,
        importance=0.7,
        status=BeliefStatus.DISPROVEN,
    )

    assert manager.beliefs_for("entity_000001") == (first, second)


def test_beliefs_about_returns_subject_history() -> None:
    manager = BeliefManager(WorldState())

    first = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.8,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    second = manager.record(
        holder_id="entity_000003",
        subject_id="entity_000002",
        proposition="The tree is old.",
        confidence=0.6,
        importance=0.5,
        status=BeliefStatus.ACTIVE,
    )

    assert manager.beliefs_about("entity_000002") == (first, second)


def test_all_returns_all_beliefs() -> None:
    manager = BeliefManager(WorldState())

    first = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.8,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    second = manager.record(
        holder_id="entity_000003",
        subject_id="entity_000004",
        proposition="The bridge is safe.",
        confidence=0.5,
        importance=0.4,
        status=BeliefStatus.WEAKENED,
    )

    assert manager.all() == (first, second)


def test_record_rejects_empty_holder() -> None:
    manager = BeliefManager(WorldState())

    with pytest.raises(ValueError, match="Belief holder_id cannot be empty."):
        manager.record(
            holder_id="",
            subject_id="entity_000002",
            proposition="The tree is healthy.",
            confidence=0.8,
            importance=0.6,
            status=BeliefStatus.ACTIVE,
        )


def test_record_rejects_invalid_status() -> None:
    manager = BeliefManager(WorldState())

    with pytest.raises((TypeError, ValueError)):
        manager.record(
            holder_id="entity_000001",
            subject_id="entity_000002",
            proposition="The tree is healthy.",
            confidence=0.8,
            importance=0.6,
            status="unknown",
        )


def test_record_rejects_invalid_confidence() -> None:
    manager = BeliefManager(WorldState())

    with pytest.raises(
        ValueError, match="Belief confidence must be between 0.0 and 1.0."
    ):
        manager.record(
            holder_id="entity_000001",
            subject_id="entity_000002",
            proposition="The tree is healthy.",
            confidence=1.4,
            importance=0.6,
            status=BeliefStatus.ACTIVE,
        )


def test_belief_is_immutable_after_recording() -> None:
    manager = BeliefManager(WorldState())

    belief = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.8,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    with pytest.raises(AttributeError):
        belief.confidence = 0.9


def test_simulation_engine_exposes_belief_manager() -> None:
    engine = SimulationEngine()

    assert engine.beliefs is not None
    assert engine.state.beliefs == {}
