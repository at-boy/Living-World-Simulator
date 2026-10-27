"""Private bounded self-contained inference snapshots with explicit retention."""

from __future__ import annotations

import base64
import json
import os
import re
import stat
from pathlib import Path

from living_world.archives.model import canonical

from .inference_trace import InferenceObservation, PreparedInference


class TraceSpoolError(ValueError):
    """Fixed safe capture failure without source data."""

    def __init__(self) -> None:
        super().__init__("Inference capture failed.")


def validate_directory(directory: Path) -> None:
    for path in (*reversed(directory.absolute().parents), directory.absolute()):
        mode = path.lstat().st_mode
        if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            raise TraceSpoolError()
    if directory.stat().st_uid != os.getuid():
        raise TraceSpoolError()


def _sync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create_trace_spool(root: Path, job_id: str) -> Path:
    try:
        if not isinstance(job_id, str) or re.fullmatch("[0-9a-f]{32}", job_id) is None:
            raise TraceSpoolError()
        # Persist each newly created entry before creating its descendants. On
        # failure preserve existing/created paths; never guess at safe cleanup.
        for path in (*reversed(root.absolute().parents), root.absolute()):
            if path.exists() or path.is_symlink():
                if not stat.S_ISDIR(path.lstat().st_mode):
                    raise TraceSpoolError()
            else:
                path.mkdir(mode=0o700)
                _sync_directory(path.parent)
        validate_directory(root)
        root.chmod(0o700)
        directory = root / job_id
        directory.mkdir(mode=0o700)
        _sync_directory(root)
        return directory
    except (OSError, ValueError):
        raise TraceSpoolError() from None


def atomic_publish(directory: Path, filename: str, raw: bytes) -> None:
    """Exclusive partial then file+directory fsync; never follow existing files."""
    try:
        validate_directory(directory)
        if filename not in ("observation.json", "result.json"):
            raise TraceSpoolError()
        path = directory / filename
        if path.is_symlink() or (
            path.exists() and not stat.S_ISREG(path.lstat().st_mode)
        ):
            raise TraceSpoolError()
        partial = path.with_suffix(".partial")
        fd = os.open(
            partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, ValueError):
        raise TraceSpoolError() from None


def read_bounded(directory: Path, filename: str, limit: int) -> bytes:
    validate_directory(directory)
    fd = os.open(directory / filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise TraceSpoolError()
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise TraceSpoolError()
    return raw


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise TraceSpoolError()
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise TraceSpoolError()


def closed_json(raw: bytes) -> object:
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)


def publish_trace_snapshot(
    directory: Path, prepared: PreparedInference, observation: InferenceObservation
) -> None:
    try:
        if (
            observation.body is not None
            and len(observation.body) > prepared.max_response_bytes + 1
        ):
            raise TraceSpoolError()
        raw = canonical(
            {
                "format": 1,
                "request_body_digest": prepared.request_trace["body_digest"],
                "response_trace": observation.response_trace,
                "body_base64": (
                    None
                    if observation.body is None
                    else base64.b64encode(observation.body).decode("ascii")
                ),
            }
        ).encode("ascii")
        if len(raw) > 8 * (prepared.max_response_bytes + 1) + 65536:
            raise TraceSpoolError()
        atomic_publish(directory, "observation.json", raw)
    except Exception:  # noqa: BLE001 - capture failures must be fail-closed
        raise TraceSpoolError() from None


def read_trace_snapshot(
    directory: Path, prepared: PreparedInference
) -> InferenceObservation | None:
    try:
        try:
            raw = read_bounded(
                directory,
                "observation.json",
                8 * (prepared.max_response_bytes + 1) + 65536,
            )
        except FileNotFoundError:
            validate_directory(directory)
            return None
        frame = closed_json(raw)
        if (
            not isinstance(frame, dict)
            or set(frame)
            != {"format", "request_body_digest", "response_trace", "body_base64"}
            or type(frame["format"]) is not int
            or frame["format"] != 1
            or frame["request_body_digest"] != prepared.request_trace["body_digest"]
        ):
            raise TraceSpoolError()
        encoded = frame["body_base64"]
        if encoded is not None and type(encoded) is not str:
            raise TraceSpoolError()
        body = None if encoded is None else base64.b64decode(encoded, validate=True)
        if body is not None and (
            len(body) > prepared.max_response_bytes + 1
            or base64.b64encode(body).decode("ascii") != encoded
        ):
            raise TraceSpoolError()
        return InferenceObservation(frame["response_trace"], body)
    except Exception:  # noqa: BLE001 - capture failures must be fail-closed
        raise TraceSpoolError() from None
