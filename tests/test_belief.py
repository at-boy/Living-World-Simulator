import pytest

from living_world.core.belief import Belief, BeliefHistoryEntry, BeliefStatus


def test_belief_is_created_with_valid_defaults() -> None:
    belief = Belief(
        id="belief_000001",
        tick=42,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The old oak is healthy and suitable for harvesting.",
        confidence=0.82,
        importance=0.65,
        status=BeliefStatus.ACTIVE,
        supporting_observations=("observation_000001",),
        supporting_memories=("memory_000001",),
        metadata={"source": "deterministic_perception"},
    )

    assert belief.id == "belief_000001"
    assert belief.holder_id == "entity_000001"
    assert belief.subject_id == "entity_000002"
    assert belief.proposition == "The old oak is healthy and suitable for harvesting."
    assert belief.confidence == 0.82
    assert belief.importance == 0.65
    assert belief.status is BeliefStatus.ACTIVE
    assert belief.supporting_observations == ("observation_000001",)
    assert belief.supporting_memories == ("memory_000001",)
    assert belief.metadata["source"] == "deterministic_perception"


def test_belief_rejects_empty_holder() -> None:
    with pytest.raises(ValueError, match="Belief holder_id cannot be empty."):
        Belief(
            id="belief_000001",
            tick=1,
            holder_id="",
            subject_id="entity_000002",
            proposition="The river is safe.",
            confidence=0.7,
            importance=0.5,
            status=BeliefStatus.ACTIVE,
        )


def test_belief_rejects_invalid_confidence() -> None:
    with pytest.raises(
        ValueError, match="Belief confidence must be between 0.0 and 1.0."
    ):
        Belief(
            id="belief_000001",
            tick=1,
            holder_id="entity_000001",
            subject_id="entity_000002",
            proposition="The river is safe.",
            confidence=1.5,
            importance=0.5,
            status=BeliefStatus.ACTIVE,
        )


def test_belief_rejects_invalid_status() -> None:
    with pytest.raises(
        ValueError, match="Belief status must be a valid BeliefStatus value."
    ):
        Belief(
            id="belief_000001",
            tick=1,
            holder_id="entity_000001",
            subject_id="entity_000002",
            proposition="The river is safe.",
            confidence=0.8,
            importance=0.5,
            status="unknown",
        )


def test_belief_is_immutable_after_creation() -> None:
    belief = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The river is safe.",
        confidence=0.8,
        importance=0.6,
        status=BeliefStatus.ACTIVE,
    )

    with pytest.raises(AttributeError):
        belief.confidence = 0.9


def test_belief_strengthen_adds_history_and_updates_confidence() -> None:
    belief = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The river is safe.",
        confidence=0.6,
        importance=0.5,
        status=BeliefStatus.ACTIVE,
    )

    strengthened = belief.strengthen(
        tick=2,
        reason="Repeated direct observation confirmed the river remains safe.",
    )

    assert strengthened.confidence > belief.confidence
    assert strengthened.status is BeliefStatus.ACTIVE
    assert (
        strengthened.history[-1].reason
        == "Repeated direct observation confirmed the river remains safe."
    )


def test_belief_weaken_records_reduction() -> None:
    belief = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The river is safe.",
        confidence=0.9,
        importance=0.7,
        status=BeliefStatus.ACTIVE,
    )

    weakened = belief.weaken(
        tick=3,
        reason="Recent contradictory observations undermined confidence.",
    )

    assert weakened.confidence < belief.confidence
    assert weakened.status is BeliefStatus.WEAKENED


def test_belief_confirm_sets_active_status() -> None:
    belief = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The trader is honest.",
        confidence=0.5,
        importance=0.8,
        status=BeliefStatus.WEAKENED,
    )

    confirmed = belief.confirm(
        tick=4,
        reason="Repeated trustworthy behavior confirmed the prior assessment.",
    )

    assert confirmed.status is BeliefStatus.ACTIVE
    assert confirmed.confidence >= 0.75


def test_belief_disprove_marks_status_disproven() -> None:
    belief = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The trader is honest.",
        confidence=0.8,
        importance=0.9,
        status=BeliefStatus.ACTIVE,
    )

    disproven = belief.disprove(
        tick=5,
        reason="Direct evidence showed the trader lied about the shipment.",
    )

    assert disproven.status is BeliefStatus.DISPROVEN
    assert disproven.confidence <= 0.2


def test_belief_history_entry_tracks_change() -> None:
    original = Belief(
        id="belief_000001",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The village is safe.",
        confidence=0.7,
        importance=0.8,
        status=BeliefStatus.ACTIVE,
    )

    revised = original.strengthen(
        tick=2,
        reason="More sightings confirmed the village remains safe.",
    )

    assert isinstance(revised.history[0], BeliefHistoryEntry)
    assert revised.history[0].tick == 2
    assert revised.history[0].old_confidence == 0.7
    assert revised.history[0].new_confidence == 1.0
    assert revised.history[0].old_status is BeliefStatus.ACTIVE
    assert revised.history[0].new_status is BeliefStatus.ACTIVE


def test_belief_status_policy_requires_valid_important_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="Important beliefs must have an importance score of at least 0.6.",
    ):
        Belief(
            id="belief_000002",
            tick=1,
            holder_id="entity_000001",
            subject_id="entity_000002",
            proposition="The path is risky.",
            confidence=0.8,
            importance=0.5,
            status=BeliefStatus.IMPORTANT,
        )


def test_belief_status_policy_requires_valid_core_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="Core beliefs must have importance >= 0.8 and confidence >= 0.7.",
    ):
        Belief(
            id="belief_000003",
            tick=1,
            holder_id="entity_000001",
            subject_id="entity_000002",
            proposition="The clan is my family.",
            confidence=0.6,
            importance=0.9,
            status=BeliefStatus.CORE,
        )


def test_belief_mark_important_and_core_update_status() -> None:
    belief = Belief(
        id="belief_000004",
        tick=1,
        holder_id="entity_000001",
        subject_id="entity_000002",
        proposition="The old guard can be trusted.",
        confidence=0.8,
        importance=0.5,
        status=BeliefStatus.ACTIVE,
    )

    important = belief.mark_important(
        tick=2,
        reason="The guard kept the village safe during the raid.",
    )
    core = important.mark_core(
        tick=3,
        reason="This defines the NPC's core worldview.",
    )

    assert important.status is BeliefStatus.IMPORTANT
    assert core.status is BeliefStatus.CORE
    assert core.importance >= 0.8
    assert core.confidence >= 0.7
