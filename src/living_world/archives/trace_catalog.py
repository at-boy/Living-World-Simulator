"""Bounded shallow identity discovery and reservation syntax inspection only."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Literal, cast

from living_world.archives.catalog import RunCatalog, parent_pair, timestamp
from living_world.archives.lease import safe_path, validate_ref
from living_world.archives.model import (
    ArchiveFormatError,
    AttemptConfig,
    AttemptRef,
    document,
    identifier,
    integer,
    loads,
    parent_boundary,
)
from living_world.archives.trace_analysis import TraceAnalysisLimitError


@dataclass(frozen=True)
class TraceCatalogLimits:
    max_entries: int = 10000
    max_header_bytes: int = 1048576

    def __post_init__(self) -> None:
        integer(self.max_entries, minimum=1)
        integer(self.max_header_bytes, minimum=1)


DEFAULT_CATALOG_LIMITS = TraceCatalogLimits()


class TraceAttemptNotFoundError(ArchiveFormatError):
    """An invalid, unknown, ambiguous or unsafe attempt identity."""

    def __init__(self) -> None:
        super().__init__("Trace attempt unavailable.")


@dataclass(frozen=True)
class TraceAttemptSummary:
    lineage_id: str
    attempt_id: str
    metadata_state: Literal["available", "missing", "invalid"]
    has_database: bool
    mode: str | None = None
    scenario_key: str | None = None
    reserved_at: str | None = None
    parent: tuple[str, int] | None = None
    reservation_error: str | None = None


@dataclass(frozen=True)
class TraceAttemptPage:
    attempts: tuple[TraceAttemptSummary, ...]
    next_after: tuple[str, str] | None
    integrity: Literal["reservation_metadata_checked"] = "reservation_metadata_checked"


def _references(catalog: RunCatalog, limits: TraceCatalogLimits) -> list[AttemptRef]:
    if not isinstance(limits, TraceCatalogLimits):
        raise ArchiveFormatError("Expected catalog limits.")
    limits.__post_init__()
    root = safe_path(catalog.root)
    refs: list[AttemptRef] = []
    inspected = 0

    def count() -> None:
        nonlocal inspected
        inspected += 1
        if inspected > limits.max_entries:
            raise TraceAnalysisLimitError()

    def valid(name: str) -> bool:
        try:
            identifier(name)
            return True
        except ArchiveFormatError:
            return False

    try:
        if not root.exists():
            return refs
        with os.scandir(root) as lineages:
            for lineage in lineages:
                count()
                if not valid(lineage.name) or not lineage.is_dir(follow_symlinks=False):
                    continue
                try:
                    directory = safe_path(root / lineage.name)
                except ArchiveFormatError:
                    continue
                with os.scandir(directory) as attempts:
                    for attempt in attempts:
                        count()
                        if valid(attempt.name):
                            refs.append(
                                AttemptRef(
                                    lineage.name, attempt.name, directory / attempt.name
                                )
                            )
    except OSError as exc:
        raise ArchiveFormatError("Trace catalog unavailable.") from exc
    return sorted(refs, key=lambda ref: (ref.lineage_id, ref.attempt_id))


def _summary(ref: AttemptRef, limits: TraceCatalogLimits) -> TraceAttemptSummary:
    def blank(
        state: Literal["missing", "invalid"], has_database: bool = False
    ) -> TraceAttemptSummary:
        return TraceAttemptSummary(ref.lineage_id, ref.attempt_id, state, has_database)

    has_database = False
    try:
        validate_ref(ref)
        if not ref.directory.is_dir():
            return blank("invalid")
        database = safe_path(ref.directory / "archive.sqlite3")
        if database.exists():
            safe_path(database, regular=True)
            has_database = True
        header = safe_path(ref.directory / "attempt.json")
        try:
            safe_path(header, regular=True)
            with header.open("rb") as handle:
                raw = handle.read(limits.max_header_bytes + 1)
        except FileNotFoundError:
            return blank("missing", has_database)
        if len(raw) > limits.max_header_bytes:
            return blank("invalid", has_database)
        data = document(
            loads(raw.decode("utf-8")),
            {
                "format",
                "lineage_id",
                "attempt_id",
                "config",
                "parent",
                "reserved_at",
                "reservation_error",
            },
            {"parent_journal"},
        )
        if (
            type(data["format"]) is not int
            or data["format"] != 1
            or data["lineage_id"] != ref.lineage_id
            or data["attempt_id"] != ref.attempt_id
        ):
            return blank("invalid", has_database)
        config = AttemptConfig(
            **document(
                data["config"],
                {"mode", "scenario_key", "seed", "software_revision", "settings"},
            )
        )
        parent = parent_pair(data["parent"])
        parent_boundary(data.get("parent_journal"), parent)
        reserved = timestamp(data["reserved_at"])
        error = data["reservation_error"]
        if error not in (None, "archive_initialization_failed"):
            return blank("invalid", has_database)
        summary = TraceAttemptSummary(
            ref.lineage_id,
            ref.attempt_id,
            "available",
            has_database,
            config.mode,
            config.scenario_key,
            reserved,
            parent,
            cast(str | None, error),
        )
        # Validate every projected string, including text in the parent pair.
        # Timestamp parsing permits arbitrary Unicode date/time separators and
        # therefore does not itself establish UTF-8 encodability.
        for field in fields(summary):
            value = getattr(summary, field.name)
            for item in value if isinstance(value, tuple) else (value,):
                if isinstance(item, str):
                    item.encode("utf-8")
        return summary
    except (
        ArchiveFormatError,
        OSError,
        ValueError,
        TypeError,
        UnicodeError,
        RecursionError,
    ):
        return blank("invalid", has_database)


def list_trace_attempts(
    catalog: RunCatalog,
    *,
    after: tuple[str, str] | None = None,
    limit: int = 50,
    limits: TraceCatalogLimits = DEFAULT_CATALOG_LIMITS,
) -> TraceAttemptPage:
    """List current identities; inspect reservation metadata only on this page."""
    if integer(limit, minimum=1) > 100:
        raise ArchiveFormatError("Invalid catalog query.")
    if after is not None:
        if type(after) is not tuple or len(after) != 2:
            raise ArchiveFormatError("Invalid catalog query.")
        identifier(after[0])
        identifier(after[1])
    refs = [
        ref
        for ref in _references(catalog, limits)
        if after is None or (ref.lineage_id, ref.attempt_id) > after
    ]
    selected = refs[:limit]
    next_after = (
        (selected[-1].lineage_id, selected[-1].attempt_id)
        if len(refs) > limit
        else None
    )
    return TraceAttemptPage(
        tuple(_summary(ref, limits) for ref in selected), next_after
    )


def resolve_trace_attempt(
    catalog: RunCatalog,
    attempt_id: str,
    *,
    limits: TraceCatalogLimits = DEFAULT_CATALOG_LIMITS,
) -> AttemptRef:
    """Resolve a unique safe identity without opening a header or database."""
    try:
        identifier(attempt_id)
    except ArchiveFormatError:
        raise TraceAttemptNotFoundError() from None
    matches = [
        ref for ref in _references(catalog, limits) if ref.attempt_id == attempt_id
    ]
    if len(matches) != 1:
        raise TraceAttemptNotFoundError()
    ref = matches[0]
    try:
        validate_ref(ref)
        if not ref.directory.is_dir():
            raise TraceAttemptNotFoundError()
    except (ArchiveFormatError, OSError):
        raise TraceAttemptNotFoundError() from None
    return ref
