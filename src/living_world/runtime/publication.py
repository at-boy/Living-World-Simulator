"""Complete immutable publications without read-side archive access."""

from collections import OrderedDict
from threading import Lock

from living_world.archives import Checkpoint

from .contracts import RuntimeStatus


class Publication:
    def __init__(self, status: RuntimeStatus) -> None:
        self._lock = Lock()
        self._status = status
        self._checkpoints: OrderedDict[int, Checkpoint] = OrderedDict()

    def update(
        self, status: RuntimeStatus, checkpoint: Checkpoint | None = None
    ) -> None:
        with self._lock:
            if checkpoint is not None:
                self._checkpoints[checkpoint.revision] = checkpoint
                while len(self._checkpoints) > 8:
                    self._checkpoints.popitem(last=False)
            self._status = status

    def status(self) -> RuntimeStatus:
        with self._lock:
            return self._status

    def checkpoint(self, revision: int | None = None) -> Checkpoint:
        with self._lock:
            selected = self._status.revision if revision is None else revision
            if type(selected) is not int or selected not in self._checkpoints:
                raise LookupError("Complete checkpoint is not cached.")
            return self._checkpoints[selected]
