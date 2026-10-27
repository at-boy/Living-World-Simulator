"""Bounded privileged trace inspection, independent of full archive validation.

Only local trace metadata and explicitly selected evidence are checked. No world,
checkpoint, reservation, parent, or lifecycle consistency is certified here.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal, cast

from living_world.archives.lease import safe_path, validate_ref
from living_world.archives.model import (
    ArchiveFormatError,
    AttemptConfig,
    AttemptRef,
    JournalBoundary,
    JournalEntry,
    JournalRecord,
    canonical,
    digest,
    document,
    frozen_map,
    identifier,
    integer,
    loads,
    parent_boundary,
    text,
    validate_offered,
)

ResponseKind = Literal["response_validated", "response_failed", "response_reused"]


class TraceAnalysisLimitError(ArchiveFormatError):
    """A trusted caller's finite resource budget was exceeded."""

    def __init__(self) -> None:
        super().__init__("Trace analysis limit exceeded.")


@dataclass(frozen=True)
class TraceReadLimits:
    max_journal_rows: int = 100000
    max_journal_bytes: int = 67108864
    max_row_bytes: int = 2097152
    max_body_bytes: int = 8388608

    def __post_init__(self) -> None:
        for value in (
            self.max_journal_rows,
            self.max_journal_bytes,
            self.max_row_bytes,
            self.max_body_bytes,
        ):
            integer(value, minimum=1)


_DEFAULT_LIMITS = TraceReadLimits()


@dataclass(frozen=True)
class TraceCall:
    request_id: str
    sequence: int
    base_revision: int
    source_tick: int
    actor_label: str
    response_kind: ResponseKind | None
    error_code: str | None
    outcome: str | None
    request_trace: Mapping[str, object] | None
    response_trace: Mapping[str, object] | None
    content_digest: str | None
    elapsed_seconds: float | int | None
    source: Mapping[str, object] | None

    def __post_init__(self) -> None:
        for name in ("request_trace", "response_trace", "source"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, frozen_map(value))


@dataclass(frozen=True)
class TracePage:
    archive_format: int
    boundary: JournalBoundary
    calls: tuple[TraceCall, ...]
    next_after_sequence: int | None
    integrity: Literal["trace_metadata_checked"] = "trace_metadata_checked"

    def __post_init__(self) -> None:
        if type(self.calls) is not tuple or any(
            not isinstance(call, TraceCall) for call in self.calls
        ):
            raise ArchiveFormatError("Expected immutable trace calls.")


@dataclass(frozen=True)
class TraceBody:
    boundary: JournalBoundary
    body: bytes
    sha256: str
    byte_length: int
    integrity: Literal["selected_body_verified"] = "selected_body_verified"

    def __post_init__(self) -> None:
        if type(self.body) is not bytes:
            raise ArchiveFormatError("Expected exact trace bytes.")


@contextmanager
def _snapshot(ref: AttemptRef) -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection | None = None
    try:
        validate_ref(ref)
        directory = safe_path(ref.directory)
        if not directory.is_dir():
            raise ArchiveFormatError("Missing archive directory.")
        path = safe_path(directory / "archive.sqlite3", regular=True)
        # WAL mode=ro can still create coordination files. Product archives use
        # rollback journals; reject externally converted sources before SQLite.
        with path.open("rb") as handle:
            header = handle.read(100)
        if (
            len(header) != 100
            or header[:16] != b"SQLite format 3\x00"
            or header[18:20] != b"\x01\x01"
            or any(
                sidecar.exists() or sidecar.is_symlink()
                for sidecar in (
                    directory / "archive.sqlite3-wal",
                    directory / "archive.sqlite3-shm",
                )
            )
        ):
            raise ArchiveFormatError(
                "Trace analysis requires rollback-journal archives."
            )
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        yield connection
    except (
        OSError,
        sqlite3.Error,
        UnicodeError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
    ) as exc:
        raise ArchiveFormatError("Could not read trace analysis archive.") from exc
    finally:
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()


# Names are fixed internal constants, never caller-controlled SQL identifiers.
_SCHEMAS = {
    "archive_meta": [("id", "INTEGER", 0, 1), ("payload", "TEXT", 1, 0)],
    "journal": [
        ("sequence", "INTEGER", 0, 1),
        ("kind", "TEXT", 1, 0),
        ("payload", "TEXT", 1, 0),
        ("checkpoint_revision", "INTEGER", 0, 0),
        ("revision_context", "INTEGER", 0, 0),
    ],
    "inference_blobs": [("sha256", "TEXT", 0, 1), ("body", "BLOB", 1, 0)],
}


def _schema(connection: sqlite3.Connection, name: str) -> None:
    tables = connection.execute("PRAGMA table_list").fetchall()
    if not any(
        row[0] == "main" and row[1] == name and row[2] == "table" for row in tables
    ):
        raise ArchiveFormatError("Missing or malformed trace analysis table.")
    rows = connection.execute(f"PRAGMA main.table_xinfo({name})").fetchall()
    if [(row[1], row[2].upper(), row[3], row[5]) for row in rows] != _SCHEMAS[
        name
    ] or any(row[6] != 0 for row in rows):
        raise ArchiveFormatError("Missing or malformed trace analysis schema.")
    # A true INTEGER PRIMARY KEY aliases rowid and has no separate PK
    # index. PRIMARY KEY DESC is SQLite's exception, and WITHOUT ROWID
    # also does not enforce the required scalar rowid identity.
    if name in ("archive_meta", "journal") and (
        any(row[1] == name and row[4] != 0 for row in tables)
        or any(
            row[3] == "pk"
            for row in connection.execute(f"PRAGMA main.index_list({name})")
        )
    ):
        raise ArchiveFormatError("Missing or malformed trace analysis schema.")


def _metadata(
    connection: sqlite3.Connection, ref: AttemptRef, limits: TraceReadLimits
) -> int:
    _schema(connection, "archive_meta")
    _schema(connection, "journal")
    rows = connection.execute(
        "SELECT typeof(id),id=1,typeof(payload),length(CAST(payload AS BLOB)) FROM archive_meta"
    ).fetchmany(2)
    if (
        len(rows) != 1
        or rows[0][0] != "integer"
        or rows[0][1] != 1
        or rows[0][2] != "text"
    ):
        raise ArchiveFormatError("Invalid trace analysis metadata.")
    if rows[0][3] > limits.max_row_bytes:
        raise TraceAnalysisLimitError()
    meta = document(
        loads(
            connection.execute(
                "SELECT payload FROM archive_meta WHERE id=1"
            ).fetchone()[0]
        ),
        {"format", "lineage_id", "attempt_id", "config", "parent", "created_at"},
        {"parent_journal"},
    )
    version = integer(meta["format"])
    if version not in (1, 2):
        raise ArchiveFormatError("Unsupported archive format.")
    if meta["lineage_id"] != ref.lineage_id or meta["attempt_id"] != ref.attempt_id:
        raise ArchiveFormatError("Archive identity mismatch.")
    AttemptConfig(
        **document(
            meta["config"],
            {"mode", "scenario_key", "seed", "software_revision", "settings"},
        )
    )
    parent = meta["parent"]
    if parent is not None:
        if not isinstance(parent, tuple) or len(parent) != 2:
            raise ArchiveFormatError("Malformed parent.")
        identifier(parent[0])
        integer(parent[1])
    parent_boundary(meta.get("parent_journal"), parent)
    parsed = datetime.fromisoformat(text(meta["created_at"]))
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ArchiveFormatError("Expected UTC timestamp.")
    if version == 2:
        _schema(connection, "inference_blobs")
    return version


def _budget(
    connection: sqlite3.Connection, sequence: int, limits: TraceReadLimits
) -> None:
    # SQL computes byte sizes and SQLite storage classes without returning TEXT/BLOBs.
    count, total, largest, invalid = connection.execute(
        "SELECT count(*),coalesce(sum(length(CAST(kind AS BLOB))+length(CAST(payload AS BLOB))),0),"
        "coalesce(max(length(CAST(kind AS BLOB))+length(CAST(payload AS BLOB))),0),"
        "coalesce(max(typeof(sequence)!='integer' OR sequence<1 OR typeof(kind)!='text' "
        "OR typeof(payload)!='text' OR typeof(checkpoint_revision) NOT IN ('integer','null') "
        "OR typeof(revision_context) NOT IN ('integer','null')),0) "
        "FROM journal WHERE sequence<=?",
        (sequence,),
    ).fetchone()
    if invalid:
        raise ArchiveFormatError("Invalid trace analysis journal types.")
    if (
        count > limits.max_journal_rows
        or total > limits.max_journal_bytes
        or largest > limits.max_row_bytes
    ):
        raise TraceAnalysisLimitError()


def _map(value: object) -> Mapping[str, object] | None:
    return None if value is None else cast(Mapping[str, object], value)


def _scan(
    connection: sqlite3.Connection,
    ref: AttemptRef,
    boundary: JournalBoundary | None,
    limits: TraceReadLimits,
) -> tuple[int, JournalBoundary, tuple[TraceCall, ...], dict[str, int]]:
    version = _metadata(connection, ref, limits)
    if boundary is None:
        # Only scalar type predicates escape before MAX returns any identity.
        if connection.execute(
            "SELECT EXISTS(SELECT 1 FROM journal WHERE typeof(sequence)!='integer' OR sequence<1)"
        ).fetchone()[0]:
            raise ArchiveFormatError("Invalid trace analysis journal identity.")
        sequence = connection.execute(
            "SELECT coalesce(max(sequence),0) FROM journal"
        ).fetchone()[0]
        integer(sequence)
    else:
        if not isinstance(boundary, JournalBoundary):
            raise ArchiveFormatError("Expected journal boundary.")
        JournalBoundary(boundary.sequence, boundary.digest)
        sequence = boundary.sequence
        if (
            sequence
            and connection.execute(
                "SELECT 1 FROM journal WHERE sequence=?", (sequence,)
            ).fetchone()
            is None
        ):
            raise ArchiveFormatError("Unknown journal boundary.")
    _budget(connection, sequence, limits)
    calls: dict[str, TraceCall] = {}
    requests: dict[str, Mapping[str, object]] = {}
    decisions: dict[str, bool] = {}
    references: dict[str, int] = {}
    hasher = hashlib.sha256(b"[")
    first = True
    for seq, kind, raw, revision, context in connection.execute(
        "SELECT sequence,kind,payload,checkpoint_revision,revision_context "
        "FROM journal WHERE sequence<=? ORDER BY sequence",
        (sequence,),
    ):
        p = cast(Mapping[str, object], loads(raw))
        entry = JournalEntry(kind, p)
        JournalRecord(seq, entry, revision, context)
        encoded = canonical(
            {
                "sequence": seq,
                "kind": kind,
                "payload": p,
                "checkpoint_revision": revision,
                "revision_context": context,
            }
        ).encode("utf-8")
        if not first:
            hasher.update(b",")
        hasher.update(encoded)
        first = False
        if version == 1 and ("request_trace" in p or "response_trace" in p):
            raise ArchiveFormatError("Inference traces require archive format two.")
        for key in ("request_trace", "response_trace"):
            trace = _map(p.get(key))
            if trace is not None and trace["body_digest"] is not None:
                sha, length = cast(str, trace["body_digest"]), cast(
                    int, trace["body_length"]
                )
                if sha in references and references[sha] != length:
                    raise ArchiveFormatError("Conflicting trace body lengths.")
                references[sha] = length
        if kind in ("request_started", "response_reused"):
            request_id = cast(str, p["request_id"])
            if request_id in calls:
                raise ArchiveFormatError("Duplicate inference request.")
            # Only the offered vocabulary is needed to check a later decision.
            request = cast(Mapping[str, object], p["request"])
            requests[request_id] = {"actions": request["actions"]}
            calls[request_id] = TraceCall(
                request_id,
                seq,
                cast(int, p["base_revision"]),
                cast(int, p["source_tick"]),
                cast(str, p["actor_label"]),
                None,
                None,
                None,
                _map(p.get("request_trace")),
                None,
                None,
                None,
                _map(p.get("source")),
            )
        if kind in (
            "response_validated",
            "response_failed",
            "response_reused",
            "action_resolved",
        ):
            request_id = cast(str, p["request_id"])
            if request_id not in calls:
                raise ArchiveFormatError("Unknown inference request.")
            call = calls[request_id]
            if kind == "action_resolved":
                if (
                    request_id not in decisions
                    or call.outcome is not None
                    or any(
                        p[key] != getattr(call, key)
                        for key in ("actor_label", "base_revision", "source_tick")
                    )
                    or (p["outcome"] == "no_action") != (not decisions[request_id])
                ):
                    raise ArchiveFormatError("Invalid trace action outcome.")
                calls[request_id] = replace(call, outcome=cast(str, p["outcome"]))
            else:
                if call.response_kind is not None:
                    raise ArchiveFormatError("Contradictory inference response.")
                response = _map(p.get("response_trace"))
                if response is not None:
                    if call.request_trace is None:
                        raise ArchiveFormatError(
                            "Response trace requires request trace."
                        )
                    length = response["body_length"]
                    if (
                        length is not None
                        and cast(int, length)
                        > cast(int, call.request_trace["max_response_bytes"]) + 1
                    ):
                        raise ArchiveFormatError(
                            "Observed response exceeds request limit plus one."
                        )
                if kind != "response_failed":
                    validate_offered(p["decision"], requests[request_id])
                    decisions[request_id] = (
                        cast(Mapping[str, object], p["decision"])["action_request"]
                        is not None
                    )
                requests.pop(request_id)
                calls[request_id] = replace(
                    call,
                    response_kind=cast(ResponseKind, kind),
                    error_code=cast(str | None, p.get("code")),
                    response_trace=response,
                    content_digest=cast(str | None, p.get("content_digest")),
                    elapsed_seconds=cast(float | int | None, p.get("elapsed_seconds")),
                )
    hasher.update(b"]")
    actual = JournalBoundary(sequence, hasher.hexdigest())
    if boundary is not None and actual != boundary:
        raise ArchiveFormatError("Journal prefix digest mismatch.")
    for sha, length in references.items():
        row = connection.execute(
            "SELECT typeof(body),length(body) FROM inference_blobs WHERE sha256=?",
            (sha,),
        ).fetchone()
        if row != ("blob", length):
            raise ArchiveFormatError("Missing or length-mismatched trace body.")
    return version, actual, tuple(calls.values()), references


def _limits(value: TraceReadLimits) -> None:
    if not isinstance(value, TraceReadLimits):
        raise ArchiveFormatError("Expected trace read limits.")
    value.__post_init__()


def read_trace_page(
    ref: AttemptRef,
    *,
    boundary: JournalBoundary | None = None,
    after_sequence: int = 0,
    limit: int = 50,
    limits: TraceReadLimits = _DEFAULT_LIMITS,
) -> TracePage:
    """Check bounded local trace metadata and return a stable prefix page."""
    _limits(limits)
    integer(after_sequence)
    if integer(limit, minimum=1) > 100:
        raise ArchiveFormatError("Trace page limit out of range.")
    with _snapshot(ref) as connection:
        version, actual, calls, _ = _scan(connection, ref, boundary, limits)
        if after_sequence > actual.sequence:
            raise ArchiveFormatError("Trace page cursor outside boundary.")
        eligible = tuple(call for call in calls if call.sequence > after_sequence)
        selected = eligible[:limit]
        next_after = selected[-1].sequence if len(eligible) > limit else None
        return TracePage(version, actual, selected, next_after)


def read_trace_body(
    ref: AttemptRef,
    sha256: str,
    *,
    boundary: JournalBoundary,
    limits: TraceReadLimits = _DEFAULT_LIMITS,
) -> TraceBody:
    """Authorize and verify all selected opaque bytes before returning them."""
    _limits(limits)
    digest(sha256)
    if not isinstance(boundary, JournalBoundary):
        raise ArchiveFormatError("Expected journal boundary.")
    with _snapshot(ref) as connection:
        version, actual, _, references = _scan(connection, ref, boundary, limits)
        if version != 2 or sha256 not in references:
            raise ArchiveFormatError("Body unavailable in selected trace prefix.")
        length = references[sha256]
        if length > limits.max_body_bytes:
            raise TraceAnalysisLimitError()
        row = connection.execute(
            "SELECT body FROM inference_blobs WHERE sha256=?", (sha256,)
        ).fetchone()
        if (
            row is None
            or type(row[0]) is not bytes
            or len(row[0]) != length
            or hashlib.sha256(row[0]).hexdigest() != sha256
        ):
            raise ArchiveFormatError("Selected trace body hash mismatch.")
        return TraceBody(actual, row[0], sha256, length)
