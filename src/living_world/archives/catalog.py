"""Read-only attempt discovery and explicit allocation/fork lifecycle operations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from living_world.archives.assets import (
    atomic_document,
    load_retained_inputs,
    retain_inputs,
)
from living_world.archives.lease import AttemptLease, safe_path, validate_ref
from living_world.archives.model import (
    STATES,
    TERMINAL_STATES,
    ArchiveError,
    ArchiveFormatError,
    AttemptConfig,
    AttemptRef,
    JournalBoundary,
    document,
    identifier,
    integer,
    loads,
    parent_boundary,
    text,
)
from living_world.archives.store import AttemptArchive
from living_world.repositories.world_snapshot import decode_world


class ArchiveReservationError(ArchiveError):
    """Archive initialization failed after allocating durable attempt identity."""

    def __init__(self, ref: AttemptRef) -> None:
        self.ref = ref
        super().__init__("Reserved attempt archive initialization failed.")


def timestamp(value: object) -> str:
    value = text(value)
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError()
    except ValueError as exc:
        raise ArchiveFormatError("Expected UTC timestamp.") from exc
    return value


def parent_pair(value: object) -> tuple[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ArchiveFormatError("Expected parent identity/revision pair.")
    return identifier(value[0]), integer(value[1])


def config_document(config: AttemptConfig) -> Mapping[str, object]:
    return {
        "mode": config.mode,
        "scenario_key": config.scenario_key,
        "seed": config.seed,
        "software_revision": config.software_revision,
        "settings": config.settings,
    }


def _read_reservation(
    ref: AttemptRef,
) -> tuple[
    AttemptConfig, tuple[str, int] | None, str, str | None, JournalBoundary | None
]:
    validate_ref(ref)
    try:
        path = safe_path(ref.directory / "attempt.json", regular=True)
        data = document(
            loads(path.read_text()),
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
            raise ArchiveFormatError("Reservation format/identity mismatch.")
        raw = document(
            data["config"],
            {"mode", "scenario_key", "seed", "software_revision", "settings"},
        )
        config = AttemptConfig(**raw)
        error = data["reservation_error"]
        if error not in (None, "archive_initialization_failed"):
            raise ArchiveFormatError("Unknown reservation error.")
        parent = parent_pair(data["parent"])
        return (
            config,
            parent,
            timestamp(data["reserved_at"]),
            cast(str | None, error),
            parent_boundary(data.get("parent_journal"), parent),
        )
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ArchiveFormatError("Invalid reservation metadata.") from exc


def read_reservation(
    ref: AttemptRef,
) -> tuple[AttemptConfig, tuple[str, int] | None, str, str | None]:
    config, parent, reserved_at, error, _ = _read_reservation(ref)
    return config, parent, reserved_at, error


@dataclass(frozen=True)
class AttemptSummary:
    ref: AttemptRef
    mode: Literal["recorded", "ollama", "journal_replay"] | None
    scenario: str | None
    parent: tuple[str, int] | None
    started_at: str | None
    ended_at: str | None
    lifecycle: str
    last_revision: int | None
    tick: int | None
    failure_code: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.ref, AttemptRef):
            raise ArchiveFormatError("Expected attempt reference.")
        AttemptRef(self.ref.lineage_id, self.ref.attempt_id, self.ref.directory)
        if self.mode not in (None, "recorded", "ollama", "journal_replay"):
            raise ArchiveFormatError("Unknown attempt mode.")
        for value in (self.scenario, self.failure_code):
            if value is not None:
                text(value)
        for value in (self.started_at, self.ended_at):
            if value is not None:
                timestamp(value)
        for value in (self.last_revision, self.tick):
            if value is not None:
                integer(value)
        object.__setattr__(self, "parent", parent_pair(self.parent))
        if not isinstance(self.lifecycle, str) or self.lifecycle not in STATES:
            raise ArchiveFormatError("Unknown attempt lifecycle.")


class RunCatalog:
    """A nested UUID catalog whose reads never initialize or repair storage."""

    def __init__(self, root: Path) -> None:
        self._root = safe_path(root)

    @property
    def root(self) -> Path:
        return self._root

    @staticmethod
    def default_root() -> Path:
        configured = os.environ.get("XDG_STATE_HOME")
        base = (
            Path(configured)
            if configured and Path(configured).is_absolute()
            else Path.home() / ".local/state"
        )
        return base / "living-world/runs"

    def _references(self) -> tuple[AttemptRef, ...]:
        safe_path(self.root)
        if not self.root.exists():
            return ()
        result = []
        for lineage in self.root.iterdir():
            if lineage.name == "objects":
                continue
            try:
                identifier(lineage.name)
            except ArchiveFormatError:
                continue
            if lineage.is_symlink() or not lineage.is_dir():
                # There is no safely knowable attempt identity beneath this node.
                continue
            safe_path(lineage)
            for attempt in lineage.iterdir():
                try:
                    identifier(attempt.name)
                except ArchiveFormatError:
                    continue
                result.append(AttemptRef(lineage.name, attempt.name, attempt))
        return tuple(sorted(result, key=lambda ref: (ref.lineage_id, ref.attempt_id)))

    def _find(self, attempt_id: str) -> AttemptRef:
        identifier(attempt_id)
        found = [ref for ref in self._references() if ref.attempt_id == attempt_id]
        if len(found) != 1:
            raise ArchiveFormatError("Unknown or duplicate attempt identity.")
        return found[0]

    def _reserve(
        self,
        config: AttemptConfig,
        parent: tuple[str, int] | None,
        lineage: str,
        parent_journal_boundary: JournalBoundary | None = None,
    ) -> AttemptRef:
        if not isinstance(config, AttemptConfig):
            raise ArchiveFormatError("Expected AttemptConfig.")
        parent = parent_pair(parent)
        if parent_journal_boundary is not None:
            if not isinstance(parent_journal_boundary, JournalBoundary):
                raise ArchiveFormatError("Expected JournalBoundary.")
            parent_boundary(asdict(parent_journal_boundary), parent)
        safe_path(self.root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        lineage_path = safe_path(self.root / identifier(lineage))
        lineage_path.mkdir(mode=0o700, exist_ok=True)
        path = lineage_path / uuid4().hex
        path.mkdir(mode=0o700)
        ref = AttemptRef(lineage, path.name, path)
        payload = {
            "format": 1,
            "lineage_id": ref.lineage_id,
            "attempt_id": ref.attempt_id,
            "config": config_document(config),
            "parent": parent,
            "parent_journal": (
                None
                if parent_journal_boundary is None
                else asdict(parent_journal_boundary)
            ),
            "reserved_at": datetime.now(UTC).isoformat(),
            "reservation_error": None,
        }
        try:
            descriptor = os.open(
                path / "owner.lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"0")
                handle.flush()
                os.fsync(handle.fileno())
            with AttemptLease(ref):
                atomic_document(path / "attempt.json", payload)
                AttemptArchive.create(
                    ref,
                    config,
                    parent=parent,
                    parent_journal_boundary=parent_journal_boundary,
                ).close()
        except (ArchiveError, OSError) as exc:
            payload["reservation_error"] = "archive_initialization_failed"
            try:
                atomic_document(path / "attempt.json", payload)
            except (ArchiveError, OSError):
                pass
            raise ArchiveReservationError(ref) from exc
        return ref

    def reserve(
        self,
        config: AttemptConfig,
        *,
        parent: tuple[str, int] | None = None,
        parent_journal_boundary: JournalBoundary | None = None,
    ) -> AttemptRef:
        pair = parent_pair(parent)
        lineage = uuid4().hex
        if pair is not None:
            with self.open_attempt(pair[0]) as archive:
                archive.checkpoint(pair[1])
                lineage = archive.ref.lineage_id
        return self._reserve(config, pair, lineage, parent_journal_boundary)

    def open_attempt(
        self, attempt_id: str, *, read_only: bool = True
    ) -> AttemptArchive:
        ref = self._find(attempt_id)
        if read_only is False and not AttemptLease.owned_by_current_thread(ref):
            raise ArchiveError("Writer open requires current thread attempt lease.")
        config, parent, _, error, boundary = _read_reservation(ref)
        if error is not None:
            raise ArchiveError("Attempt archive initialization failed.")
        try:
            safe_path(ref.directory / "archive.sqlite3", regular=True)
            archive = AttemptArchive.open(ref, read_only=read_only)
            try:
                if (
                    archive.config != config
                    or archive.parent != parent
                    or archive.parent_journal_boundary != boundary
                ):
                    raise ArchiveFormatError("Reservation/archive metadata mismatch.")
                if (
                    archive.latest_revision is not None
                    or (ref.directory / "inputs.json").exists()
                ):
                    load_retained_inputs(ref)
                return archive
            except BaseException:
                archive.close()
                raise
        except OSError as exc:
            raise ArchiveFormatError("Incomplete attempt archive.") from exc

    def attempts(self) -> tuple[AttemptSummary, ...]:
        references = self._references()
        duplicates = {
            ref.attempt_id
            for ref in references
            if sum(other.attempt_id == ref.attempt_id for other in references) > 1
        }
        result = []
        for ref in references:
            config = None
            parent = None
            started = None
            ended = None
            lifecycle = "initializing"
            revision = tick = None
            failure = None
            try:
                validate_ref(ref)
                config, parent, started, reservation_error = read_reservation(ref)
                if ref.attempt_id in duplicates:
                    raise ArchiveFormatError("Duplicate attempt identity.")
                if reservation_error is not None:
                    failure, lifecycle = reservation_error, "failed"
                else:
                    with self.open_attempt(ref.attempt_id) as archive:
                        started = started or archive.created_at
                        history = archive.lifecycle()
                        if history:
                            lifecycle = cast(str, history[-1]["state"])
                            if lifecycle == "failed":
                                failure = cast(str | None, history[-1]["reason"])
                            terminals = [
                                row
                                for row in history
                                if row["state"] in TERMINAL_STATES
                            ]
                            if terminals:
                                ended = cast(str, terminals[-1]["timestamp"])
                        revision = archive.latest_revision
                        if revision is not None:
                            tick = decode_world(archive.checkpoint().snapshot).tick
                    if lifecycle not in TERMINAL_STATES:
                        try:
                            if not AttemptLease.is_owned(ref):
                                lifecycle = "interrupted"
                        except (OSError, ArchiveError):
                            failure = "owner_probe_unavailable"
            except (ArchiveError, OSError, ValueError, TypeError):
                lifecycle = "failed"
                try:
                    validate_ref(ref)
                    safe_path(ref.directory / "archive.sqlite3", regular=True)
                    with AttemptArchive.open(ref, read_only=True) as available:
                        started = started or available.created_at
                except (ArchiveError, OSError):
                    pass
                missing = False
                try:
                    validate_ref(ref)
                    missing = (
                        not (ref.directory / "attempt.json").exists()
                        or not (ref.directory / "archive.sqlite3").exists()
                    )
                    # A checkpoint requires its retained input publication.
                    if not missing and not (ref.directory / "inputs.json").exists():
                        with AttemptArchive.open(ref, read_only=True) as archive:
                            missing = archive.latest_revision is not None
                except (ArchiveError, OSError, ValueError, TypeError):
                    # Inaccessibility does not establish that publication is absent.
                    # Preserve safely known metadata and continue other attempts.
                    pass
                failure = "archive_incomplete" if missing else "archive_invalid"
            result.append(
                AttemptSummary(
                    ref,
                    None if config is None else config.mode,
                    None if config is None else config.scenario_key,
                    parent,
                    started,
                    ended,
                    lifecycle,
                    revision,
                    tick,
                    failure,
                )
            )
        return tuple(result)

    def fork(
        self, attempt_id: str, revision: int, *, config: AttemptConfig | None = None
    ) -> AttemptRef:
        integer(revision)
        with self.open_attempt(attempt_id) as parent:
            point = parent.fork_point(revision)
            checkpoint = point.checkpoint
            source_config = parent.config
            inputs = load_retained_inputs(parent.ref)
            if config is None:
                config = source_config
            if (
                not isinstance(config, AttemptConfig)
                or config.scenario_key != source_config.scenario_key
                or config.seed != source_config.seed
                or config.mode
                not in {
                    "recorded": ("recorded",),
                    "ollama": ("ollama", "journal_replay"),
                    "journal_replay": ("journal_replay",),
                }[source_config.mode]
            ):
                raise ArchiveFormatError("Invalid fork configuration transition.")
            ref = self._reserve(
                config,
                (attempt_id, revision),
                parent.ref.lineage_id,
                point.journal_boundary,
            )
            retain_inputs(ref, inputs.scenario_path, tape_path=inputs.tape_path)
            with (
                AttemptLease(ref),
                self.open_attempt(ref.attempt_id, read_only=False) as child,
            ):
                child.commit(
                    checkpoint.snapshot,
                    expected_revision=None,
                    driver_cursor=checkpoint.driver_cursor,
                    feedback_cursor=checkpoint.feedback_cursor,
                    entries=(),
                )
            return ref
