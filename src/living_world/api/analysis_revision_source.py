"""Selected-only, detached checkpoint views for offline analysis."""

import stat
from collections import OrderedDict
from threading import Lock

from living_world.api.inspection import EngineWorldInspector, WorldInspector
from living_world.api.revision_source import RevisionSourceError
from living_world.archives import ArchiveError, RunCatalog
from living_world.archives.model import identifier, integer
from living_world.archives.trace_catalog import (
    TraceAttemptNotFoundError,
    resolve_trace_attempt,
)
from living_world.runtime.entrypoints import load_archived_inspection


class AnalysisRevisionSource:
    """Serialize selected reconstruction and retain eight detached historical views."""

    def __init__(self, catalog: RunCatalog) -> None:
        if not isinstance(catalog, RunCatalog):
            raise TypeError("Expected RunCatalog.")
        self._catalog = catalog
        self._lock = Lock()
        self._cache: OrderedDict[tuple[str, int], WorldInspector] = OrderedDict()

    def open(self, attempt_id: str, revision: int) -> WorldInspector:
        """Validate a cache miss; cached views intentionally outlive source changes."""
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
                ref = resolve_trace_attempt(self._catalog, attempt_id)
                try:
                    mode = (ref.directory / "archive.sqlite3").lstat().st_mode
                except FileNotFoundError:
                    raise RevisionSourceError("not_found") from None
                if not stat.S_ISREG(mode):
                    raise RevisionSourceError("archive_invalid")
                with self._catalog.open_attempt(attempt_id, read_only=True) as archive:
                    latest = archive.latest_revision
                    if latest is None or revision > latest:
                        raise RevisionSourceError("not_found")
                inspector = EngineWorldInspector(
                    load_archived_inspection(self._catalog, attempt_id, revision)
                )
            except TraceAttemptNotFoundError:
                raise RevisionSourceError("not_found") from None
            except RevisionSourceError:
                raise
            except Exception:  # noqa: BLE001 - sanitize storage/reconstruction failures
                raise RevisionSourceError("archive_invalid") from None
            self._cache[key] = inspector
            if len(self._cache) > 8:
                self._cache.popitem(last=False)
            return inspector
