from living_world.core.memory import CognitiveSalience, Memory
from living_world.state.world_state import WorldState


class MemoryManager:
    """Own the lifecycle of immutable NPC memory interpretations."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_memory_id = 1

    def add(self, memory: Memory) -> None:
        self._state.memories[memory.id] = memory

    def record(
        self,
        *,
        holder_id: str,
        subject_id: str,
        summary: str,
        salience: CognitiveSalience,
        source_observation_ids: tuple[str, ...] = (),
    ) -> Memory:
        memory = Memory(
            id=self._generate_id(),
            tick=self._state.tick,
            holder_id=holder_id,
            subject_id=subject_id,
            summary=summary,
            salience=salience,
            source_observation_ids=source_observation_ids,
        )
        self.add(memory)
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._state.memories.get(memory_id)

    def memories_for(self, holder_id: str) -> tuple[Memory, ...]:
        return tuple(
            memory
            for memory in self._state.memories.values()
            if memory.holder_id == holder_id
        )

    def memories_for_observation(
        self, holder_id: str, observation_id: str
    ) -> tuple[Memory, ...]:
        return tuple(
            memory
            for memory in self.memories_for(holder_id)
            if observation_id in memory.source_observation_ids
        )

    def has_observation_provenance(self, holder_id: str, observation_id: str) -> bool:
        return bool(self.memories_for_observation(holder_id, observation_id))

    def all(self) -> tuple[Memory, ...]:
        return tuple(self._state.memories.values())

    def _generate_id(self) -> str:
        while True:
            memory_id = f"memory_{self._next_memory_id:06d}"
            self._next_memory_id += 1
            if memory_id not in self._state.memories:
                return memory_id
