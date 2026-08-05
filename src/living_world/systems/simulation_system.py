from abc import ABC, abstractmethod


class SimulationSystem(ABC):
    """Base class for all simulation systems."""

    @abstractmethod
    def update(self) -> None:
        """Execute one simulation tick."""
