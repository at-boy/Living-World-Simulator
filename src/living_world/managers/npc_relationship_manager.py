from living_world.core.memory import CognitiveSalience
from living_world.core.npc_relationship import NPCRelationship
from living_world.state.world_state import WorldState


class NPCRelationshipManager:
    """Own the lifecycle of NPC-scoped relationship interpretations."""

    def __init__(self, state: WorldState) -> None:
        self._state = state
        self._next_relationship_id = 1

    def add(self, relationship: NPCRelationship) -> None:
        self._state.npc_relationships[relationship.id] = relationship

    def record(
        self,
        *,
        holder_id: str,
        subject_id: str,
        summary: str,
        salience: CognitiveSalience,
        source_observation_ids: tuple[str, ...] = (),
    ) -> NPCRelationship:
        relationship = NPCRelationship(
            id=self._generate_id(),
            tick=self._state.tick,
            holder_id=holder_id,
            subject_id=subject_id,
            summary=summary,
            salience=salience,
            source_observation_ids=source_observation_ids,
        )
        self.add(relationship)
        return relationship

    def get(self, relationship_id: str) -> NPCRelationship | None:
        return self._state.npc_relationships.get(relationship_id)

    def relationships_for(self, holder_id: str) -> tuple[NPCRelationship, ...]:
        return tuple(
            relationship
            for relationship in self._state.npc_relationships.values()
            if relationship.holder_id == holder_id
        )

    def all(self) -> tuple[NPCRelationship, ...]:
        return tuple(self._state.npc_relationships.values())

    def _generate_id(self) -> str:
        while True:
            relationship_id = f"npc_relationship_{self._next_relationship_id:06d}"
            self._next_relationship_id += 1
            if relationship_id not in self._state.npc_relationships:
                return relationship_id
