from living_world.managers.entity_manager import EntityManager
from living_world.systems.simulation_system import SimulationSystem


class ProgressSystem(SimulationSystem):
    """Advances entity progress over time."""

    def __init__(
        self,
        entities: EntityManager,
    ) -> None:
        self._entities = entities

    def _attribute_as_int(
        self,
        attributes: dict[str, object],
        key: str,
    ) -> int:
        value = attributes[key]

        if not isinstance(value, int):
            raise TypeError(f"Expected '{key}' to be an int.")

        return value

    def update(self) -> None:
        for entity in self._entities.all():
            attributes = entity.attributes

            if "progress" not in attributes:
                continue

            if "progress_rate" not in attributes:
                continue

            progress = self._attribute_as_int(
                attributes,
                "progress",
            )
            rate = self._attribute_as_int(
                attributes,
                "progress_rate",
            )

            progress += rate

            if "progress_min" in attributes:
                progress = max(
                    self._attribute_as_int(
                        attributes,
                        "progress_min",
                    ),
                    progress,
                )

            if "progress_max" in attributes:
                progress = min(
                    self._attribute_as_int(
                        attributes,
                        "progress_max",
                    ),
                    progress,
                )

            attributes["progress"] = progress
