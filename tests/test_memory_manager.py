from living_world.core.memory import CognitiveSalience
from living_world.managers.memory_manager import MemoryManager
from living_world.state.world_state import WorldState


def test_memory_manager_records_and_finds_observation_provenance() -> None:
    state = WorldState(tick=12)
    manager = MemoryManager(state)

    memory = manager.record(
        holder_id="npc_1",
        subject_id="tree_1",
        summary="I remember the old oak looked healthy.",
        salience=CognitiveSalience(importance=0.7),
        source_observation_ids=("observation_000001",),
    )

    assert manager.get(memory.id) is memory
    assert manager.memories_for("npc_1") == (memory,)
    assert manager.has_observation_provenance("npc_1", "observation_000001")
    assert not manager.has_observation_provenance("other_npc", "observation_000001")
