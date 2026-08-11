from living_world.core.entity import Entity
from living_world.core.relationship import Relationship
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class OrganizationSystem(SimulationSystem):
    """Maintain membership summaries for organization entities."""

    system_name = "organization"
    membership_kind = "member_of"

    def __init__(
        self,
        definitions: DefinitionManager,
        entities: EntityManager,
        events: EventManager,
    ) -> None:
        self._definitions = definitions
        self._entities = entities
        self._events = events

    def step(self, state: WorldState) -> None:
        """Synchronize membership counts in stable organization identifier order."""

        for organization in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(organization):
                continue

            member_count = self._member_count(state, organization)
            previous_count = self._member_count_attribute(organization)

            if previous_count == member_count:
                continue

            self._entities.set_attribute(
                entity_id=organization.id,
                key="member_count",
                value=member_count,
            )
            self._events.record(
                kind="organization_membership_changed",
                subject_id=organization.id,
                attributes={"previous": previous_count, "member_count": member_count},
            )

    def _participates(self, entity: Entity) -> bool:
        definition = self._definitions.get(entity.definition_key)
        return self.system_name in definition.systems

    def _member_count(self, state: WorldState, organization: Entity) -> int:
        members = {
            relationship.source_id
            for relationship in state.relationships.values()
            if self._is_valid_membership(relationship, organization.id)
        }
        return len(members)

    def _is_valid_membership(
        self,
        relationship: Relationship,
        organization_id: str,
    ) -> bool:
        return (
            relationship.kind == self.membership_kind
            and relationship.target_id == organization_id
            and relationship.source_id != organization_id
            and self._entities.exists(relationship.source_id)
        )

    def _member_count_attribute(self, organization: Entity) -> int:
        value = organization.attributes.get("member_count", 0)

        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise TypeError("'member_count' must be a non-negative integer.")

        return value
