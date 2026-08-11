from collections.abc import Mapping

from living_world.core.entity import Entity
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem
from living_world.systems.simulation_system import SimulationSystem


class ConstructionSystem(SimulationSystem):
    """Complete opt-in construction after bounded progress and payment."""

    system_name = "construction"

    def __init__(
        self,
        definitions: DefinitionManager,
        entities: EntityManager,
        events: EventManager,
        resources: ResourceSystem,
    ) -> None:
        self._definitions = definitions
        self._entities = entities
        self._events = events
        self._resources = resources

    def step(self, state: WorldState) -> None:
        """Record completed construction in stable entity identifier order."""

        for entity in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(entity) or self._is_constructed(entity):
                continue

            if not self._is_progress_complete(entity):
                continue

            requirements = self._requirements(entity)
            if not self._can_pay(entity, requirements):
                continue

            for resource, amount in requirements.items():
                self._resources.remove(entity, resource, amount)

            self._entities.set_attribute(
                entity_id=entity.id,
                key="is_constructed",
                value=True,
            )
            self._events.record(
                kind="construction_completed",
                subject_id=entity.id,
                attributes={"requirements": dict(requirements)},
            )

    def _participates(self, entity: Entity) -> bool:
        return self.system_name in self._definitions.get(entity.definition_key).systems

    def _is_constructed(self, entity: Entity) -> bool:
        value = entity.attributes.get("is_constructed", False)
        if not isinstance(value, bool):
            raise TypeError("'is_constructed' must be a boolean.")
        return value

    def _is_progress_complete(self, entity: Entity) -> bool:
        progress = self._integer_attribute(entity, "progress")
        progress_max = self._integer_attribute(entity, "progress_max")
        return progress >= progress_max

    def _requirements(self, entity: Entity) -> dict[str, int]:
        value = entity.attributes.get("construction_requirements", {})
        if not isinstance(value, Mapping):
            raise TypeError("'construction_requirements' must be a mapping.")

        requirements: dict[str, int] = {}
        for resource, amount in value.items():
            if not isinstance(resource, str) or not resource.strip():
                raise TypeError(
                    "Construction resource names must be non-empty strings."
                )
            if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
                raise TypeError(
                    "Construction resource requirements must be non-negative integers."
                )
            requirements[resource] = amount
        return requirements

    def _can_pay(self, entity: Entity, requirements: Mapping[str, int]) -> bool:
        return all(
            self._resources.get(entity, resource) >= amount
            for resource, amount in requirements.items()
        )

    def _integer_attribute(self, entity: Entity, key: str) -> int:
        value = entity.attributes.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"'{key}' must be an integer.")
        return value
