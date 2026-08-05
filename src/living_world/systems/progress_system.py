from living_world.managers.entity_manager import EntityManager
from living_world.systems.simulation_system import SimulationSystem


class ProgressSystem(SimulationSystem):
    """Advances entity progress over time."""

    def __init__(
        self,
        entities: EntityManager,
    ) -> None:
        self._entities = entities

    def update(self) -> None:
        for entity in self._entities.all():

            attributes = entity.attributes

            if "progress" not in attributes or "progress_rate" not in attributes:
                continue

            progress = attributes["progress"]
            rate = attributes["progress_rate"]

            if not isinstance(progress, (int, float)):
                continue

            if not isinstance(rate, (int, float)):
                continue

            attributes["progress"] = progress + rate
