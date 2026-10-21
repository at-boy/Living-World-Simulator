"""Exclusive attempt ownership using descriptor-held operating-system locks."""

from __future__ import annotations

import os
import stat
import threading
from pathlib import Path
from typing import BinaryIO, ClassVar, Self
from weakref import WeakValueDictionary

from living_world.archives.model import ArchiveError, ArchiveFormatError, AttemptRef


def safe_path(path: Path, *, regular: bool = False) -> Path:
    """Reject traversal and links before resolving a filesystem name."""
    if not isinstance(path, Path) or ".." in path.parts:
        raise ArchiveFormatError("Unsafe filesystem path.")
    path = path.absolute()
    for component in (*reversed(path.parents), path):
        if component.is_symlink():
            raise ArchiveFormatError("Symlinks are not archive paths.")
    if regular:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ArchiveFormatError("Expected independent regular file.")
    return path


def validate_ref(ref: AttemptRef) -> Path:
    """Validate the fixed nested identity layout; return its catalog root."""
    if not isinstance(ref, AttemptRef):
        raise ArchiveFormatError("Expected AttemptRef.")
    AttemptRef(ref.lineage_id, ref.attempt_id, ref.directory)
    path = safe_path(ref.directory)
    if (
        path != ref.directory
        or path.name != ref.attempt_id
        or path.parent.name != ref.lineage_id
    ):
        raise ArchiveFormatError("Attempt directory identity mismatch.")
    return path.parent.parent


def _lock(handle: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class AttemptLease:
    """A nonblocking lease; forked processes may not reuse its handle."""

    _active: ClassVar[WeakValueDictionary[Path, AttemptLease]] = WeakValueDictionary()

    def __init__(self, ref: AttemptRef) -> None:
        validate_ref(ref)
        self.ref = ref
        self._handle: BinaryIO | None = None
        self._pid = os.getpid()
        self._thread: int | None = None

    def acquire(self) -> None:
        if self._pid != os.getpid() or self._handle is not None:
            raise ArchiveError("Lease handle already acquired or inherited.")
        validate_ref(self.ref)
        path = safe_path(self.ref.directory / "owner.lock")
        if not path.exists():
            # Only a published reservation authorizes recreating a missing lock.
            from living_world.archives.catalog import read_reservation

            read_reservation(self.ref)
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(descriptor, b"0")
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            except FileExistsError:
                pass
        safe_path(path, regular=True)
        handle = path.open("r+b")
        try:
            _lock(handle)
        except OSError as exc:
            handle.close()
            raise ArchiveError("Attempt is already owned or cannot be locked.") from exc
        self._handle = handle
        self._thread = threading.get_ident()
        self._active[self.ref.directory] = self

    def release(self) -> None:
        if self._pid != os.getpid() or (
            self._handle is not None and self._thread != threading.get_ident()
        ):
            raise ArchiveError("Inherited or foreign-thread lease cannot be released.")
        handle, self._handle = self._handle, None
        if self._active.get(self.ref.directory) is self:
            self._active.pop(self.ref.directory, None)
        if handle is not None:
            try:
                if not handle.closed:
                    _unlock(handle)
            finally:
                handle.close()

    @staticmethod
    def owned_by_current_thread(ref: AttemptRef) -> bool:
        validate_ref(ref)
        lease = AttemptLease._active.get(ref.directory)
        return bool(
            lease is not None
            and lease._pid == os.getpid()
            and lease._thread == threading.get_ident()
            and lease._handle is not None
            and not lease._handle.closed
        )

    @staticmethod
    def is_owned(ref: AttemptRef) -> bool:
        validate_ref(ref)
        path = safe_path(ref.directory / "owner.lock")
        if not path.exists():
            return False
        safe_path(path, regular=True)
        # Read-only probing never creates, writes, or updates lock bytes/mtime.
        with path.open("rb") as handle:
            try:
                _lock(handle)
            except (BlockingIOError, PermissionError) as exc:
                if isinstance(exc, BlockingIOError) or (
                    os.name == "nt" and exc.errno in (11, 13, 36)
                ):
                    return True
                raise
            else:
                _unlock(handle)
                return False

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
