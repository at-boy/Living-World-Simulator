from living_world.core.belief import Belief, BeliefStatus
from living_world.managers.belief_manager import BeliefManager
from living_world.state.world_state import WorldState


def test_belief_records_supporting_observation_links() -> None:
    manager = BeliefManager(WorldState())

    belief = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.82,
        importance=0.65,
        status=BeliefStatus.ACTIVE,
        supporting_observations=("observation_000001", "observation_000003"),
        supporting_memories=("memory_000001",),
    )

    assert belief.supporting_observations == (
        "observation_000001",
        "observation_000003",
    )
    assert manager.beliefs_supporting_observation("observation_000003") == (belief,)


def test_belief_records_supporting_memory_links() -> None:
    manager = BeliefManager(WorldState())

    belief = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The tree is healthy.",
        confidence=0.82,
        importance=0.65,
        status=BeliefStatus.ACTIVE,
        supporting_observations=("observation_000001",),
        supporting_memories=("memory_000001", "memory_000002"),
    )

    assert belief.supporting_memories == ("memory_000001", "memory_000002")
    assert manager.beliefs_supporting_memory("memory_000002") == (belief,)


def test_belief_history_is_preserved_through_updates() -> None:
    belief = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The trader is honest.",
        confidence=0.7,
        importance=0.8,
        status=BeliefStatus.ACTIVE,
    )

    updated = belief.confirm(
        tick=2,
        reason="Repeated behavior confirmed the assessment.",
    )

    updated = updated.weaken(
        tick=3,
        reason="A recent lie changed the NPC's confidence.",
    )

    assert len(updated.history) == 2
    assert updated.history[0].reason == "Repeated behavior confirmed the assessment."
    assert updated.history[1].reason == "A recent lie changed the NPC's confidence."
    assert updated.history[1].new_status is BeliefStatus.WEAKENED


def test_manager_history_for_returns_history_entries() -> None:
    manager = BeliefManager(WorldState())

    belief = manager.record(
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The bridge is safe.",
        confidence=0.5,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    updated = belief.confirm(
        tick=2,
        reason="The bridge held under weight.",
    )
    manager.add(updated)

    assert manager.history_for("belief_000001") == updated.history
