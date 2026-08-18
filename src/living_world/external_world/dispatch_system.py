import hashlib

from living_world.core.run_metadata import RunMetadata
from living_world.external_world.dispatch import DispatchStatus
from living_world.external_world.dispatch_manager import ExternalDispatchManager
from living_world.external_world.manager import ExternalWorldReferenceManager
from living_world.state.world_state import WorldState


class ExternalDispatchSystem:
    """Advance dispatches using only persisted identity and anchor policy."""

    def __init__(
        self,
        manager: ExternalDispatchManager,
        references: ExternalWorldReferenceManager,
    ) -> None:
        self._manager = manager
        self._references = references

    def step(self, state: WorldState) -> None:
        for dispatch in self._manager.all():
            if dispatch.status is DispatchStatus.PENDING:
                dispatch = self._manager.depart(dispatch.id)
            if dispatch.status is not DispatchStatus.IN_TRANSIT:
                continue
            reference = self._references.get(dispatch.reference_id)
            if reference is None or dispatch.departure_tick is None:
                continue
            if state.tick < dispatch.departure_tick + reference.delay_ticks:
                continue
            self._manager.resolve(
                dispatch.id,
                arrived=_deterministic_fraction(
                    state.run_metadata, dispatch.id, dispatch.reference_id
                )
                < reference.reliability,
            )


def _deterministic_fraction(
    metadata: RunMetadata | None, dispatch_id: str, reference_id: str
) -> float:
    seed = 0 if metadata is None else metadata.seed
    digest = hashlib.sha256(f"{seed}:{reference_id}:{dispatch_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64
