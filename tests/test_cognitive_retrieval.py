from living_world.cognition.retrieval import (
    DeterministicCognitiveRetriever,
    RetrievalQuery,
)
from living_world.core.belief import Belief, BeliefStatus
from living_world.core.experience import Experience
from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.npc_relationship import NPCRelationship
from living_world.state.world_state import WorldState


def _salience(importance: float) -> CognitiveSalience:
    return CognitiveSalience(importance=importance, is_core=True)


def _state_with_core_records() -> WorldState:
    state = WorldState()
    for index in range(11):
        record_id = f"memory_{index:02d}"
        state.memories[record_id] = Memory(
            id=record_id,
            tick=index,
            holder_id="npc_1",
            subject_id="oak",
            summary=f"Memory {index}",
            salience=_salience(0.8 if index < 2 else 0.9),
        )
    state.memories["memory_other"] = Memory(
        id="memory_other",
        tick=100,
        holder_id="npc_2",
        subject_id="oak",
        summary="Other holder memory",
        salience=_salience(1.0),
    )
    state.beliefs["belief_1"] = Belief(
        id="belief_1",
        tick=20,
        holder_id="npc_1",
        subject_id="oak",
        proposition="The oak will endure.",
        confidence=0.9,
        importance=0.9,
        status=BeliefStatus.CORE,
    )
    state.experiences["experience_1"] = Experience(
        id="experience_1",
        tick=21,
        holder_id="npc_1",
        subject_id="oak",
        summary="Years of tending oak trees taught me patience.",
        salience=_salience(0.9),
    )
    return state


def test_retrieval_uses_exact_core_order_and_limit_with_holder_isolation() -> None:
    result = DeterministicCognitiveRetriever(_state_with_core_records()).retrieve(
        RetrievalQuery(holder_id="npc_1")
    )

    assert len(result) == 10
    assert [(item.kind, item.text) for item in result] == [
        ("experience", "Years of tending oak trees taught me patience."),
        ("belief", "The oak will endure."),
        ("memory", "Memory 10"),
        ("memory", "Memory 9"),
        ("memory", "Memory 8"),
        ("memory", "Memory 7"),
        ("memory", "Memory 6"),
        ("memory", "Memory 5"),
        ("memory", "Memory 4"),
        ("memory", "Memory 3"),
    ]
    assert all("Other holder" not in item.text for item in result)
    assert all(not hasattr(item, "id") for item in result)
    assert all(not hasattr(item, "provenance") for item in result)


def test_query_retrieves_only_relevant_holder_scoped_relationships_and_knowledge() -> (
    None
):
    state = WorldState()
    state.npc_relationships["relationship_1"] = NPCRelationship(
        id="relationship_1",
        tick=4,
        holder_id="npc_1",
        subject_id="trader",
        summary="The trader has been dependable at the east bridge.",
        salience=CognitiveSalience(importance=0.7),
    )
    state.knowledge["knowledge_1"] = Knowledge(
        id="knowledge_1",
        tick=5,
        holder_id="npc_1",
        subject_id="bridge",
        statement="The east bridge is closed.",
        source_description="The miller told me.",
        salience=CognitiveSalience(importance=0.8),
        supporting_observations=("observation_1",),
        metadata={"hidden": {"subject_attributes": {"wood": 120}}},
    )
    state.knowledge["knowledge_other"] = Knowledge(
        id="knowledge_other",
        tick=6,
        holder_id="npc_2",
        subject_id="bridge",
        statement="Other NPC knowledge.",
        source_description="A stranger said so.",
        salience=CognitiveSalience(importance=1.0),
    )

    result = DeterministicCognitiveRetriever(state).retrieve(
        RetrievalQuery(holder_id="npc_1", topic="BRIDGE", limit=2)
    )

    assert tuple(item.kind for item in result) == ("knowledge", "relationship")
    assert result[0].kind == "knowledge"
    assert result[0].text == "The east bridge is closed. Source: The miller told me."
    assert result[1].text == "The trader has been dependable at the east bridge."
    assert "observation_1" not in result[0].text
    assert "120" not in result[0].text


def test_retrieval_query_validates_required_fields() -> None:
    import pytest

    with pytest.raises(ValueError, match="cannot be empty"):
        RetrievalQuery(holder_id="")
    with pytest.raises(ValueError, match="cannot be empty"):
        RetrievalQuery(holder_id="npc_1", topic=" ")
    with pytest.raises(ValueError, match="must be positive"):
        RetrievalQuery(holder_id="npc_1", limit=0)
