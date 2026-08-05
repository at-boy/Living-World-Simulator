from living_world.core.relationship import Relationship


class RelationshipManager:
    """Owns lifecycle of relationships."""

    def __init__(self) -> None:
        self._relationships: dict[str, Relationship] = {}

    def add(self, relationship: Relationship) -> None:
        self._relationships[relationship.id] = relationship

    def get(self, relationship_id: str) -> Relationship | None:
        return self._relationships.get(relationship_id)
