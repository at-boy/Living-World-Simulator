"""Shared local operator credential custody and closed serving failures."""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path


class ServeCLIError(RuntimeError):
    """Closed, sanitized failures belonging to the serving adapter."""

    def __init__(self, exit_code: int, reason: str) -> None:
        if (exit_code, reason) not in {
            (2, "invalid_configuration"),
            (2, "server_unavailable"),
            (4, "credential_file_failed"),
            (5, "server_failed"),
            (5, "service_failed"),
        }:
            raise ValueError("Invalid serving failure.")
        self.exit_code, self.reason = exit_code, reason
        super().__init__(reason)


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


@dataclass
class AdminTokenFile:
    """An anchored parent descriptor and identity of our exclusive credential file."""

    parent: int
    name: str
    identity: tuple[int, int, int] | None = None
    written: bytes = b""
    published: bool = False

    @classmethod
    def open(cls, path: Path, protected: list[Path]) -> AdminTokenFile:
        parent = -1
        try:
            absolute = path.absolute()
            canonical = absolute.resolve()
            if any(_overlaps(canonical, item.resolve()) for item in protected):
                raise ServeCLIError(2, "invalid_configuration")
            parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            for part in absolute.parent.parts[1:]:
                next_fd = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
                )
                previous, parent = parent, next_fd
                try:
                    os.close(previous)
                except OSError:
                    raise ServeCLIError(4, "credential_file_failed") from None
            try:
                os.stat(absolute.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ServeCLIError(2, "invalid_configuration")
            return cls(parent, absolute.name)
        except (OSError, ValueError, RuntimeError) as error:
            failure = (
                error
                if isinstance(error, ServeCLIError)
                else ServeCLIError(2, "invalid_configuration")
            )
            if parent >= 0:
                try:
                    os.close(parent)
                except OSError:
                    failure = ServeCLIError(4, "credential_file_failed")
            raise failure from None

    def _remove_owned(self) -> None:
        if self.identity is None:
            return
        try:
            info = os.stat(self.name, dir_fd=self.parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        if (
            (info.st_dev, info.st_ino, info.st_uid) != self.identity
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or (self.published and stat.S_IMODE(info.st_mode) != 0o600)
        ):
            return
        descriptor = os.open(self.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.parent)
        try:
            current = os.fstat(descriptor)
            if (current.st_dev, current.st_ino, current.st_uid) != self.identity:
                return
            content = bytearray()
            while len(content) <= len(self.written):
                chunk = os.read(descriptor, len(self.written) + 1 - len(content))
                if not chunk:
                    break
                content.extend(chunk)
            if bytes(content) != self.written:
                return
        finally:
            os.close(descriptor)
        # Same-UID check/unlink races are best effort, not atomic inode unlink.
        again = os.stat(self.name, dir_fd=self.parent, follow_symlinks=False)
        if (
            (again.st_dev, again.st_ino, again.st_uid) == self.identity
            and stat.S_ISREG(again.st_mode)
            and again.st_nlink == 1
            and (not self.published or stat.S_IMODE(again.st_mode) == 0o600)
        ):
            os.unlink(self.name, dir_fd=self.parent)

    def publish(self, token: str) -> None:
        descriptor: int | None = None
        try:
            descriptor = os.open(
                self.name,
                os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.parent,
            )
            info = os.fstat(descriptor)
            self.identity = info.st_dev, info.st_ino, info.st_uid
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
            ):
                raise OSError()
            os.fchmod(descriptor, 0o600)
            data = (token + "\n").encode("ascii")
            while len(self.written) < len(data):
                count = os.write(descriptor, data[len(self.written) :])
                if count <= 0:
                    raise OSError()
                self.written += data[len(self.written) : len(self.written) + count]
            os.fsync(descriptor)
            closing, descriptor = descriptor, None
            os.close(closing)
            self.published = True
        except OSError as error:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            try:
                self._remove_owned()
            except OSError:
                pass
            if self.identity is None and error.errno in (errno.EEXIST, errno.ELOOP):
                raise ServeCLIError(2, "invalid_configuration") from None
            raise ServeCLIError(4, "credential_file_failed") from None

    def close(self) -> None:
        failed = False
        try:
            self._remove_owned()
        except OSError:
            failed = True
        finally:
            parent, self.parent = self.parent, -1
            try:
                os.close(parent)
            except OSError:
                failed = True
        if failed:
            raise ServeCLIError(4, "credential_file_failed") from None
