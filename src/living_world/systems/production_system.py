from collections.abc import Mapping

from living_world.core.entity import Entity
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem
from living_world.systems.simulation_system import SimulationSystem


class ProductionSystem(SimulationSystem):
    """Apply resource recipes for opt-in production entities."""

    system_name = "production"

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
        for producer in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(producer):
                continue

            inputs = self._recipe(producer, "production_inputs")
            outputs = self._recipe(producer, "production_outputs")
            if not outputs or not self._can_pay(producer, inputs):
                continue

            for resource, amount in inputs.items():
                self._resources.remove(producer, resource, amount)
            for resource, amount in outputs.items():
                self._resources.add(producer, resource, amount)

            self._events.record(
                kind="production_completed",
                subject_id=producer.id,
                attributes={"inputs": dict(inputs), "outputs": dict(outputs)},
            )

    def _participates(self, entity: Entity) -> bool:
        return self.system_name in self._definitions.get(entity.definition_key).systems

    def _recipe(self, entity: Entity, key: str) -> dict[str, int]:
        value = entity.attributes.get(key, {})
        if not isinstance(value, Mapping):
            raise TypeError(f"'{key}' must be a mapping.")

        recipe: dict[str, int] = {}
        for resource, amount in value.items():
            if not isinstance(resource, str) or not resource.strip():
                raise TypeError("Production resource names must be non-empty strings.")
            if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
                raise TypeError("Production quantities must be non-negative integers.")
            recipe[resource] = amount
        return recipe

    def _can_pay(self, entity: Entity, inputs: Mapping[str, int]) -> bool:
        return all(
            self._resources.get(entity, resource) >= amount
            for resource, amount in inputs.items()
        )
