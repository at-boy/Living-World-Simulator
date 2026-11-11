"""Filesystem precheck for read-only access to product rollback archives."""

import stat
from pathlib import Path

from living_world.archives.model import ArchiveFormatError


def require_rollback_database(path: Path) -> None:
    """Reject unsupported sources before SQLite can create coordination files.

    This bounded precheck does not protect against hostile filesystem races or
    limit native SQLite parser allocations. Reading may update source atime.
    """
    message = "Read-only access requires rollback-journal archives."
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ArchiveFormatError(message)
        with path.open("rb") as handle:
            header = handle.read(100)
        if (
            len(header) != 100
            or header[:16] != b"SQLite format 3\x00"
            or header[18:20] != b"\x01\x01"
        ):
            raise ArchiveFormatError(message)
        for suffix in ("-wal", "-shm"):
            sidecar = path.with_name(path.name + suffix)
            try:
                sidecar.lstat()
            except FileNotFoundError:
                continue
            raise ArchiveFormatError(message)
    except OSError:
        raise ArchiveFormatError(message) from None
