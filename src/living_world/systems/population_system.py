from living_world.core.entity import Entity
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class PopulationSystem(SimulationSystem):
    """Advance bounded population values for opt-in entities."""

    system_name = "population"

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
        """Apply configured population change in stable entity identifier order."""

        for entity in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(entity):
                continue

            population = self._required_int(entity, "population")
            change = self._optional_int(entity, "population_change", default=0)
            minimum = self._optional_int(entity, "population_min", default=0)
            maximum = self._optional_int(entity, "population_max", default=None)

            if maximum is not None and minimum > maximum:
                raise ValueError("'population_min' cannot exceed 'population_max'.")

            next_population = max(minimum, population + change)
            if maximum is not None:
                next_population = min(maximum, next_population)

            if next_population == population:
                continue

            self._entities.set_attribute(
                entity_id=entity.id,
                key="population",
                value=next_population,
            )
            self._events.record(
                kind="population_changed",
                subject_id=entity.id,
                attributes={
                    "previous": population,
                    "population": next_population,
                    "change": next_population - population,
                },
            )

    def _participates(self, entity: Entity) -> bool:
        definition = self._definitions.get(entity.definition_key)
        return self.system_name in definition.systems

    def _required_int(self, entity: Entity, key: str) -> int:
        if key not in entity.attributes:
            raise ValueError(f"Population entity '{entity.id}' requires '{key}'.")

        return self._value_as_int(entity.attributes[key], key)

    def _optional_int(
        self,
        entity: Entity,
        key: str,
        *,
        default: int | None,
    ) -> int | None:
        value = entity.attributes.get(key, default)
        if value is None:
            return None

        return self._value_as_int(value, key)

    def _value_as_int(self, value: object, key: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"'{key}' must be an integer.")

        return value
