from typing import Protocol

from living_world.state.world_state import WorldState


class GraphRepository(Protocol):
    """Persistence boundary for complete world snapshots."""

    def load_world(self) -> WorldState:
        """Return the persisted world, or an empty world when none exists."""

    def save_world(self, state: WorldState) -> None:
        """Atomically persist a complete world snapshot."""
