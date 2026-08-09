from collections.abc import Sequence

from living_world.core.entity import Entity
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class WeatherSystem(SimulationSystem):
    """Advance opt-in entities through their configured weather cycles."""

    system_name = "weather"

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
        """Apply each weather cycle in stable entity identifier order."""

        for entity in sorted(self._entities.all(), key=lambda item: item.id):
            if not self._participates(entity):
                continue

            cycle = self._weather_cycle(entity)
            index = self._weather_index(entity)
            weather = cycle[index % len(cycle)]
            previous_weather = entity.attributes.get("weather")

            self._entities.set_attribute(
                entity_id=entity.id,
                key="weather",
                value=weather,
            )
            self._entities.set_attribute(
                entity_id=entity.id,
                key="weather_index",
                value=(index + 1) % len(cycle),
            )

            if previous_weather != weather:
                self._events.record(
                    kind="weather_changed",
                    subject_id=entity.id,
                    attributes={"previous": previous_weather, "weather": weather},
                )

    def _participates(self, entity: Entity) -> bool:
        definition = self._definitions.get(entity.definition_key)
        return self.system_name in definition.systems

    def _weather_cycle(self, entity: Entity) -> tuple[str, ...]:
        cycle = entity.attributes.get("weather_cycle")

        if not isinstance(cycle, Sequence) or isinstance(cycle, (str, bytes)):
            raise TypeError("'weather_cycle' must be a non-empty sequence of strings.")

        if not cycle or any(
            not isinstance(weather, str) or not weather.strip() for weather in cycle
        ):
            raise ValueError("'weather_cycle' must be a non-empty sequence of strings.")

        return tuple(cycle)

    def _weather_index(self, entity: Entity) -> int:
        index = entity.attributes.get("weather_index", 0)

        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("'weather_index' must be an integer.")

        return index
