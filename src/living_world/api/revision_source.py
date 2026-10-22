"""Privileged detached inspection of exact retained archive revisions."""

from collections import OrderedDict
from threading import Lock
from typing import Literal

from living_world.api.inspection import EngineWorldInspector, WorldInspector
from living_world.archives import ArchiveError, RunCatalog
from living_world.archives.catalog import SETUP_CODES
from living_world.archives.model import identifier, integer
from living_world.runtime.controller import RunController
from living_world.runtime.entrypoints import load_archived_inspection


class RevisionSourceError(LookupError):
    """A safe source failure without archive paths or underlying diagnostics."""

    def __init__(self, code: Literal["not_found", "archive_invalid"]) -> None:
        self.code = code
        super().__init__(code)


class RevisionSource:
    """Serialize reconstruction and cache up to eight immutable-by-convention views."""

    def __init__(
        self, catalog: RunCatalog, *, controller: RunController | None = None
    ) -> None:
        if not isinstance(catalog, RunCatalog):
            raise TypeError("Expected RunCatalog.")
        if controller is not None and not isinstance(controller, RunController):
            raise TypeError("Expected RunController.")
        self._catalog = catalog
        self._lock = Lock()
        self._cache: OrderedDict[tuple[str, int], WorldInspector] = OrderedDict()

    def open(self, attempt_id: str, revision: int) -> WorldInspector:
        """Return the exact checkpoint, without acquiring ownership or writing storage."""
        try:
            identifier(attempt_id)
            integer(revision, minimum=0)
        except ArchiveError:
            raise RevisionSourceError("not_found") from None
        with self._lock:
            key = (attempt_id, revision)
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            try:
                matches = [
                    item
                    for item in self._catalog.attempts()
                    if item.ref.attempt_id == attempt_id
                ]
                if not matches:
                    raise RevisionSourceError("not_found")
                if len(matches) != 1:
                    raise RevisionSourceError("archive_invalid")
                summary = matches[0]
                if summary.failure_code in {"archive_invalid", "archive_incomplete"}:
                    raise RevisionSourceError("archive_invalid")
                # Catalog validates this reservation marker without opening a world.
                if (
                    summary.lifecycle == "failed"
                    and summary.last_revision is None
                    and summary.failure_code == "archive_initialization_failed"
                ):
                    raise RevisionSourceError("not_found")
                # Setup-only identities have no published world to reconstruct.
                if (
                    summary.last_revision is None
                    and summary.mode == "ollama"
                    and (
                        summary.failure_code in SETUP_CODES
                        or (
                            summary.failure_code is None
                            and summary.lifecycle in {"initializing", "interrupted"}
                        )
                    )
                ):
                    raise RevisionSourceError("not_found")
                with self._catalog.open_attempt(attempt_id, read_only=True) as archive:
                    latest = archive.latest_revision
                    if latest is None or revision > latest:
                        raise RevisionSourceError("not_found")
                inspector = EngineWorldInspector(
                    load_archived_inspection(self._catalog, attempt_id, revision)
                )
            except RevisionSourceError:
                raise
            except Exception:  # noqa: BLE001 - safe boundary for archive/load failures
                raise RevisionSourceError("archive_invalid") from None
            self._cache[key] = inspector
            if len(self._cache) > 8:
                self._cache.popitem(last=False)
            return inspector
