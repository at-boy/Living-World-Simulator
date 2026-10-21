"""Atomic publication of exact checkpoints for legacy SQLite consumers."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from living_world.archives.assets import fsync_directory
from living_world.archives.catalog import RunCatalog
from living_world.archives.lease import safe_path, validate_ref
from living_world.archives.model import ArchiveError, AttemptRef, Checkpoint
from living_world.repositories.sqlite_repository import SQLiteRepository


class ArchiveMirrorError(ArchiveError):
    """Compatibility export failed; the committed archive remains authoritative."""

    def __init__(self, attempt: AttemptRef, revision: int, destination: Path) -> None:
        self.attempt = attempt
        self.revision = revision
        self.destination = destination
        super().__init__(
            "Checkpoint mirror publication failed; archive remains authoritative."
        )


def write_checkpoint_mirror(
    checkpoint: Checkpoint, destination: Path, *, attempt: AttemptRef
) -> None:
    """Publish a closed standalone file; never claim cross-file rollback."""
    temporary: Path | None = None
    try:
        root = validate_ref(attempt)
        if not isinstance(checkpoint, Checkpoint):
            raise ArchiveError("Expected Checkpoint.")
        with RunCatalog(root).open_attempt(attempt.attempt_id) as source:
            if (
                source.ref != attempt
                or source.checkpoint(checkpoint.revision) != checkpoint
            ):
                raise ArchiveError("Checkpoint does not belong to source archive.")
        target = safe_path(destination)
        if target.is_relative_to(root):
            raise ArchiveError("Cannot overwrite archive-owned storage.")
        safe_path(target.parent)
        if not target.parent.is_dir():
            raise ArchiveError("Destination directory must exist.")
        if target.exists():
            safe_path(target, regular=True)
        descriptor, name = tempfile.mkstemp(
            prefix=".checkpoint-", suffix=".tmp", dir=target.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        connection = sqlite3.connect(temporary)
        try:
            connection.execute(
                "CREATE TABLE world_snapshots(id INTEGER PRIMARY KEY CHECK(id=1), schema_version INTEGER NOT NULL, payload TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO world_snapshots VALUES(1,?,?)",
                (checkpoint.snapshot.schema_version, checkpoint.snapshot.payload),
            )
            connection.commit()
        finally:
            connection.close()
        SQLiteRepository(str(temporary), read_only=True).load_world()
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        safe_path(target)
        if target.exists():
            safe_path(target, regular=True)
        os.replace(temporary, target)
        temporary = None
        fsync_directory(target.parent)
    except Exception as exc:
        raise ArchiveMirrorError(attempt, checkpoint.revision, destination) from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                # A failed cleanup must not replace the authoritative mirror error.
                pass
