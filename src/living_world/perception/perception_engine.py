from typing import Protocol

from living_world.core.observation import Observation
from living_world.perception.perception_context import PerceptionContext


class PerceptionEngine(Protocol):
    """Produces observations from an observer's perception of the world."""

    def perceive(
        self,
        context: PerceptionContext,
    ) -> Observation:
        """Produce an observation from the supplied perception context."""
        ...
