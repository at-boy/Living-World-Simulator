from dataclasses import FrozenInstanceError

import pytest

from living_world.core.memory import CognitiveSalience
from living_world.core.npc_relationship import NPCRelationship
from living_world.managers.npc_relationship_manager import NPCRelationshipManager
from living_world.state.world_state import WorldState


def test_npc_relationship_is_immutable_holder_scoped_interpretation() -> None:
    relationship = NPCRelationship(
        id="npc_relationship_000001",
        tick=10,
        holder_id="npc_1",
        subject_id="npc_2",
        summary="I find the trader dependable.",
        salience=CognitiveSalience(importance=0.7),
        source_observation_ids=("observation_000001",),
    )

    with pytest.raises(FrozenInstanceError):
        relationship.summary = "changed"
    assert relationship.holder_id == "npc_1"


def test_npc_relationship_manager_keeps_interpretations_separate_from_graph() -> None:
    state = WorldState()
    manager = NPCRelationshipManager(state)

    relationship = manager.record(
        holder_id="npc_1",
        subject_id="npc_2",
        summary="I find the trader dependable.",
        salience=CognitiveSalience(importance=0.7),
    )

    assert manager.relationships_for("npc_1") == (relationship,)
    assert not state.relationships
