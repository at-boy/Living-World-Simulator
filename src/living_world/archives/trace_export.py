"""Private deterministic exports of a bounded saved trace prefix, never worlds."""

from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, fields
from pathlib import Path
from typing import BinaryIO, Literal, TypeVar, cast

from living_world.archives.catalog import RunCatalog
from living_world.archives.lease import safe_path
from living_world.archives.model import (
    ArchiveFormatError,
    JournalBoundary,
    canonical,
    identifier,
    plain,
)
from living_world.archives.trace_analysis import (
    TraceAnalysisLimitError,
    TraceCall,
    read_trace_body,
    read_trace_page,
)
from living_world.archives.trace_catalog import resolve_trace_attempt

ExportCode = Literal[
    "export_invalid",
    "trace_unavailable",
    "export_limit_exceeded",
    "export_cancelled",
    "export_failed",
    "export_published_uncertain",
]
_CODES = {
    "export_invalid": 2,
    "trace_unavailable": 4,
    "export_limit_exceeded": 4,
    "export_cancelled": 130,
    "export_failed": 4,
    "export_published_uncertain": 4,
}
_CHUNK = 65536
_T = TypeVar("_T")


class TraceExportError(Exception):
    """Closed public errors without source or output diagnostics."""

    def __init__(self, code: ExportCode) -> None:
        if code not in _CODES:
            raise ValueError("Unknown export error code.")
        self.code = code
        self.exit_code = _CODES[code]
        super().__init__(code)


@dataclass(frozen=True)
class TraceExportLimits:
    max_calls: int = 1000
    max_output_bytes: int = 134217728

    def __post_init__(self) -> None:
        if (
            type(self.max_calls) is not int
            or not 1 <= self.max_calls <= 10000
            or type(self.max_output_bytes) is not int
            or not 1024 <= self.max_output_bytes <= 1073741824
        ):
            raise TraceExportError("export_invalid")


@dataclass(frozen=True)
class TraceExportResult:
    call_count: int
    body_count: int
    boundary: JournalBoundary
    byte_length: int


_DEFAULT_LIMITS = TraceExportLimits()


def _source(operation: Callable[[], _T]) -> _T:
    try:
        return operation()
    except TraceAnalysisLimitError:
        raise TraceExportError("export_limit_exceeded") from None
    except (ArchiveFormatError, OSError, ValueError, TypeError):
        raise TraceExportError("trace_unavailable") from None


def _check(stop: Callable[[], bool]) -> None:
    if stop():
        raise TraceExportError("export_cancelled")


def _info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100600 << 16
    info.compress_type = zipfile.ZIP_STORED
    return info


def _validate(
    handle: BinaryIO,
    inventory: list[dict[str, object]],
    manifest: bytes,
    stop: Callable[[], bool],
) -> None:
    handle.seek(0)
    with zipfile.ZipFile(handle) as archive:
        names = [str(entry["name"]) for entry in inventory] + ["manifest.json"]
        if archive.namelist() != names or archive.comment:
            raise TraceExportError("export_failed")
        for info in archive.infolist():
            if (
                info.date_time != (1980, 1, 1, 0, 0, 0)
                or info.compress_type != zipfile.ZIP_STORED
                or info.external_attr >> 16 != 0o100600
                or info.extra
                or info.comment
            ):
                raise TraceExportError("export_failed")
        for entry in inventory + [
            {
                "name": "manifest.json",
                "byte_length": len(manifest),
                "sha256": hashlib.sha256(manifest).hexdigest(),
            }
        ]:
            digest = hashlib.sha256()
            length = 0
            with archive.open(str(entry["name"])) as member:
                while True:
                    _check(stop)
                    chunk = member.read(_CHUNK)
                    if not chunk:
                        break
                    length += len(chunk)
                    digest.update(chunk)
            if length != entry["byte_length"] or digest.hexdigest() != entry["sha256"]:
                raise TraceExportError("export_failed")


def export_trace_bundle(
    catalog: RunCatalog,
    attempt_id: str,
    output: Path,
    *,
    limits: TraceExportLimits = _DEFAULT_LIMITS,
    stop_requested: Callable[[], bool] = lambda: False,
) -> TraceExportResult:
    """Export selected evidence; successful exclusive publication never overwrites."""
    try:
        if (
            not isinstance(catalog, RunCatalog)
            or not isinstance(limits, TraceExportLimits)
            or not callable(stop_requested)
        ):
            raise TraceExportError("export_invalid")
        limits.__post_init__()
        identifier(attempt_id)
        target = safe_path(output)
        root = catalog.root.absolute()
        if (
            target == root
            or target.is_relative_to(root)
            or root.is_relative_to(target)
            or target.exists()
            or not target.parent.is_dir()
        ):
            raise TraceExportError("export_invalid")
    except (ArchiveFormatError, OSError, TypeError, ValueError):
        raise TraceExportError("export_invalid") from None
    temporary: Path | None = None
    published = False
    identity: tuple[int, int] | None = None
    error: TraceExportError | None = None
    result: TraceExportResult | None = None
    try:
        _check(stop_requested)
        ref = _source(lambda: resolve_trace_attempt(catalog, attempt_id))
        page = _source(lambda: read_trace_page(ref, limit=100))
        boundary = page.boundary
        version = page.archive_format
        calls: list[TraceCall] = []
        bodies: dict[str, int] = {}
        while True:
            _check(stop_requested)
            if len(calls) + len(page.calls) > limits.max_calls:
                raise TraceExportError("export_limit_exceeded")
            calls.extend(page.calls)
            for call in page.calls:
                for trace in (call.request_trace, call.response_trace):
                    if trace is not None and trace["body_digest"] is not None:
                        bodies[str(trace["body_digest"])] = cast(
                            int, trace["body_length"]
                        )
            after = page.next_after_sequence
            if after is None:
                break
            if len(calls) >= limits.max_calls:
                raise TraceExportError("export_limit_exceeded")
            page = _source(
                lambda after=after: read_trace_page(
                    ref, boundary=boundary, after_sequence=after, limit=100
                )
            )
        descriptor, name = tempfile.mkstemp(prefix=".trace-export-", dir=target.parent)
        temporary = Path(name)
        try:
            owned = os.fstat(descriptor)
            identity = (owned.st_dev, owned.st_ino)
            staged = os.fdopen(descriptor, "w+b")
        except BaseException:
            os.close(descriptor)
            raise
        with staged as handle:
            inventory: list[dict[str, object]] = []

            def budget(extra: int = 0) -> None:
                if handle.tell() + extra > limits.max_output_bytes:
                    raise TraceExportError("export_limit_exceeded")

            with zipfile.ZipFile(
                handle, "w", compression=zipfile.ZIP_STORED, allowZip64=False
            ) as archive:

                def write(name: str, chunks: Iterator[bytes]) -> None:
                    digest = hashlib.sha256()
                    length = 0
                    with archive.open(_info(name), "w") as member:
                        for raw in chunks:
                            for offset in range(0, len(raw), _CHUNK):
                                _check(stop_requested)
                                chunk = raw[offset : offset + _CHUNK]
                                budget(len(chunk))
                                member.write(chunk)
                                digest.update(chunk)
                                length += len(chunk)
                    budget()
                    inventory.append(
                        {
                            "name": name,
                            "byte_length": length,
                            "sha256": digest.hexdigest(),
                        }
                    )

                write(
                    "calls.jsonl",
                    (
                        (
                            canonical(
                                plain(
                                    {
                                        f.name: getattr(call, f.name)
                                        for f in fields(call)
                                    }
                                )
                            )
                            + "\n"
                        ).encode("utf-8")
                        for call in calls
                    ),
                )
                for digest in sorted(bodies):
                    _check(stop_requested)
                    budget(bodies[digest])
                    body = _source(
                        lambda digest=digest: read_trace_body(
                            ref, digest, boundary=boundary
                        )
                    )
                    write("bodies/" + digest + ".bin", iter((body.body,)))
                manifest = canonical(
                    {
                        "format": "living-world-trace-evidence-v1",
                        "lineage_id": ref.lineage_id,
                        "attempt_id": ref.attempt_id,
                        "archive_format": version,
                        "boundary": {
                            "sequence": boundary.sequence,
                            "digest": boundary.digest,
                        },
                        "call_count": len(calls),
                        "body_count": len(bodies),
                        "integrity_scope": "local_trace_prefix_and_selected_bodies",
                        "omitted": [
                            "world_validation",
                            "ancestor_closure",
                            "uncommitted_spool",
                            "model_weights",
                            "session_credentials",
                        ],
                        "files": sorted(
                            inventory, key=lambda entry: str(entry["name"])
                        ),
                    }
                ).encode("utf-8")
                entries = list(inventory)
                write("manifest.json", iter((manifest,)))
            budget()
            byte_length = handle.tell()
            _validate(handle, entries, manifest, stop_requested)
            handle.flush()
            os.fsync(handle.fileno())
            _check(stop_requested)
            _source(lambda: read_trace_page(ref, boundary=boundary, limit=1))
            _check(stop_requested)
            current = temporary.lstat()
            if (current.st_dev, current.st_ino) != identity:
                raise TraceExportError("export_failed")
            os.link(temporary, target)
            published = True
            directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            result = TraceExportResult(len(calls), len(bodies), boundary, byte_length)
    except KeyboardInterrupt:
        error = TraceExportError(
            "export_published_uncertain" if published else "export_cancelled"
        )
    except TraceExportError as exc:
        error = TraceExportError("export_published_uncertain") if published else exc
    except Exception:  # noqa: BLE001 - closed local export boundary
        error = TraceExportError(
            "export_published_uncertain" if published else "export_failed"
        )
    finally:
        if temporary is not None:
            try:
                current = temporary.lstat()
                if (current.st_dev, current.st_ino) != identity:
                    raise OSError("Temporary custody changed.")
                temporary.unlink()
            except OSError:
                error = TraceExportError(
                    "export_published_uncertain" if published else "export_failed"
                )
    if error is not None:
        raise error from None
    assert result is not None
    return result
