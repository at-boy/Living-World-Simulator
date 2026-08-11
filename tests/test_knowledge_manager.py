from living_world.core.memory import CognitiveSalience
from living_world.managers.knowledge_manager import KnowledgeManager
from living_world.state.world_state import WorldState


def test_knowledge_manager_records_holder_scoped_claims() -> None:
    state = WorldState(tick=12)
    manager = KnowledgeManager(state)

    first = manager.record(
        holder_id="npc_1",
        subject_id="east_bridge",
        statement="The east bridge is closed.",
        source_description="The miller told me.",
        salience=CognitiveSalience(importance=0.7),
        supporting_observations=("observation_000001",),
    )
    second = manager.record(
        holder_id="npc_2",
        subject_id="east_bridge",
        statement="The bridge may be difficult to cross.",
        source_description="A traveller mentioned it.",
        salience=CognitiveSalience(importance=0.5),
    )

    assert first.id == "knowledge_000001"
    assert first.tick == 12
    assert manager.get(first.id) is first
    assert manager.knowledge_for("npc_1") == (first,)
    assert manager.knowledge_for("npc_2") == (second,)
    assert manager.knowledge_for("npc_3") == ()
