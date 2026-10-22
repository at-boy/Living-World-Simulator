"""Read-only attempt discovery and explicit allocation/fork lifecycle operations."""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from living_world.archives.assets import (
    atomic_document,
    load_retained_inputs,
    private_name,
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
    Checkpoint,
    JournalBoundary,
    canonical,
    digest,
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


SETUP_CODES = frozenset(
    {
        "timeout",
        "transport",
        "http_error",
        "invalid_response",
        "oversized_response",
        "worker_failed",
        "cancelled",
        "model_missing",
        "model_digest_mismatch",
        "invalid_preflight",
        "setup_failed",
    }
)


def normalized_digest(value: object) -> str:
    if not isinstance(value, str):
        raise ArchiveFormatError("Expected model digest.")
    value = value.lower().removeprefix("sha256:")
    if re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ArchiveFormatError("Expected model digest.")
    return value


def validate_setup_config(requested: AttemptConfig, effective: AttemptConfig) -> None:
    if not isinstance(effective, AttemptConfig) or requested.mode != "ollama":
        raise ArchiveFormatError("Invalid setup configuration.")
    if (
        requested.mode,
        requested.scenario_key,
        requested.seed,
        requested.software_revision,
    ) != (
        effective.mode,
        effective.scenario_key,
        effective.seed,
        effective.software_revision,
    ) or {
        k: v for k, v in requested.settings.items() if k != "provider"
    } != {
        k: v for k, v in effective.settings.items() if k != "provider"
    }:
        raise ArchiveFormatError("Setup intent/config mismatch.")
    from living_world.runtime.broker import provider_config

    try:
        original = asdict(provider_config(requested))
        resolved = asdict(provider_config(effective))
    except (ValueError, TypeError) as exc:
        raise ArchiveFormatError("Invalid setup provider configuration.") from exc
    for key in original.keys() - {"model", "model_digest"}:
        if original[key] != resolved[key]:
            raise ArchiveFormatError("Setup provider defaults mismatch.")
    before = cast(Mapping[str, object], requested.settings.get("provider", {}))
    after = cast(Mapping[str, object], effective.settings.get("provider", {}))
    name = before.get("model")
    if not isinstance(name, str) or after.get("model") not in (
        name,
        name + ":latest" if ":" not in name.rsplit("/", 1)[-1] else name,
    ):
        raise ArchiveFormatError("Setup model mismatch.")
    if (
        not isinstance(after.get("model"), str)
        or len(cast(str, after["model"])) > 512
        or any(
            c.isspace() or unicodedata.category(c).startswith("C")
            for c in cast(str, after["model"])
        )
    ):
        raise ArchiveFormatError("Invalid setup model name.")
    actual = normalized_digest(after.get("model_digest"))
    if actual != after.get("model_digest"):
        raise ArchiveFormatError("Expected canonical model digest.")
    for key, value in before.items():
        if key == "model":
            continue
        other = after.get(key)
        if key == "model_digest":
            value = normalized_digest(value)
        if key == "base_url" and isinstance(value, str) and isinstance(other, str):
            value, other = value.rstrip("/"), other.rstrip("/")
        if value != other:
            raise ArchiveFormatError("Setup provider option mismatch.")


def _config_hash(config: AttemptConfig) -> str:
    return hashlib.sha256(canonical(config_document(config)).encode()).hexdigest()


def _checkpoint_hash(checkpoint: Checkpoint) -> str:
    return hashlib.sha256(
        canonical(
            {
                "snapshot": {
                    "schema_version": checkpoint.snapshot.schema_version,
                    "payload": checkpoint.snapshot.payload,
                },
                "driver_cursor": checkpoint.driver_cursor,
                "feedback_cursor": checkpoint.feedback_cursor,
            }
        ).encode()
    ).hexdigest()


def _fork_document(ref: AttemptRef, value: object) -> Mapping[str, object]:
    data = document(
        value,
        {
            "parent",
            "parent_journal",
            "checkpoint_sha256",
            "source_config_sha256",
            "input_hashes",
        },
    )
    pair = parent_pair(data["parent"])
    if pair is None or pair[0] == ref.attempt_id:
        raise ArchiveFormatError("Invalid setup parent.")
    if parent_boundary(data["parent_journal"], pair) is None:
        raise ArchiveFormatError("Missing setup parent boundary.")
    digest(data["checkpoint_sha256"])
    digest(data["source_config_sha256"])
    hashes = data["input_hashes"]
    if not isinstance(hashes, Mapping):
        raise ArchiveFormatError("Expected setup input hashes.")
    for name, expected in hashes.items():
        private_name(name)
        digest(expected)
    return data


def validate_setup_inputs(ref: AttemptRef, hashes: Mapping[str, str]) -> None:
    """Bind retained bytes to the immutable fork intent, including during setup."""
    data = _setup_document(ref)
    if "fork" in data:
        fork = cast(Mapping[str, object], data["fork"])
        if fork["input_hashes"] != hashes:
            raise ArchiveFormatError("Setup retained input mismatch.")


def _setup_document(ref: AttemptRef, failure: bool = False) -> Mapping[str, object]:
    validate_ref(ref)
    try:
        name = "setup_failure.json" if failure else "setup.json"
        fields = {"format", "lineage_id", "attempt_id"} | (
            {"code", "ended_at"} if failure else {"requested_config", "reserved_at"}
        )
        data = document(
            loads(safe_path(ref.directory / name, regular=True).read_text()),
            fields,
            set() if failure else {"fork"},
        )
        if (
            type(data["format"]) is not int
            or data["format"] != 1
            or (data["lineage_id"], data["attempt_id"])
            != (ref.lineage_id, ref.attempt_id)
        ):
            raise ArchiveFormatError("Setup identity mismatch.")
        timestamp(data["ended_at" if failure else "reserved_at"])
        if failure:
            if not isinstance(data["code"], str) or data["code"] not in SETUP_CODES:
                raise ArchiveFormatError("Invalid setup failure code.")
        else:
            config = AttemptConfig(
                **document(
                    data["requested_config"],
                    {"mode", "scenario_key", "seed", "software_revision", "settings"},
                )
            )
            if config.mode != "ollama":
                raise ArchiveFormatError("Setup requires Ollama mode.")
            if "fork" in data:
                _fork_document(ref, data["fork"])
        return data
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ArchiveFormatError("Invalid setup metadata.") from exc


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


def validate_setup_reservation(
    ref: AttemptRef, requested: AttemptConfig
) -> AttemptConfig:
    config, parent, reserved_at, error, boundary = _read_reservation(ref)
    validate_setup_config(requested, config)
    data = _setup_document(ref)
    fork = cast(Mapping[str, object], data.get("fork", {}))
    expected_parent = parent_pair(fork.get("parent"))
    expected_boundary = parent_boundary(fork.get("parent_journal"), expected_parent)
    if (
        parent != expected_parent
        or boundary != expected_boundary
        or error is not None
        or reserved_at != data["reserved_at"]
    ):
        raise ArchiveFormatError("Setup reservation mismatch.")
    return config


def _validate_setup_complete(ref: AttemptRef, config: AttemptConfig) -> None:
    try:
        data = document(
            loads(
                safe_path(
                    ref.directory / "setup_complete.json", regular=True
                ).read_text()
            ),
            {"format", "lineage_id", "attempt_id", "config_sha256"},
        )
        if (
            type(data["format"]) is not int
            or data["format"] != 1
            or (data["lineage_id"], data["attempt_id"])
            != (ref.lineage_id, ref.attempt_id)
            or digest(data["config_sha256"])
            != hashlib.sha256(canonical(config_document(config)).encode()).hexdigest()
        ):
            raise ArchiveFormatError("Setup completion marker mismatch.")
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ArchiveFormatError("Invalid setup completion marker.") from exc


def _publish_archive(
    ref: AttemptRef,
    config: AttemptConfig,
    payload: Mapping[str, object],
    parent: tuple[str, int] | None = None,
    boundary: JournalBoundary | None = None,
) -> None:
    atomic_document(ref.directory / "attempt.json", payload)
    AttemptArchive.create(
        ref, config, parent=parent, parent_journal_boundary=boundary
    ).close()


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

    def _allocate(self, lineage: str) -> AttemptRef:
        safe_path(self.root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        lineage_path = safe_path(self.root / identifier(lineage))
        lineage_path.mkdir(mode=0o700, exist_ok=True)
        path = lineage_path / uuid4().hex
        path.mkdir(mode=0o700)
        ref = AttemptRef(lineage, path.name, path)
        return ref

    @staticmethod
    def _create_lock(ref: AttemptRef) -> None:
        descriptor = os.open(
            ref.directory / "owner.lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"0")
            handle.flush()
            os.fsync(handle.fileno())

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
        ref = self._allocate(lineage)
        path = ref.directory
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
            self._create_lock(ref)
            with AttemptLease(ref):
                _publish_archive(ref, config, payload, parent, parent_journal_boundary)
        except (ArchiveError, OSError) as exc:
            payload["reservation_error"] = "archive_initialization_failed"
            try:
                atomic_document(path / "attempt.json", payload)
            except (ArchiveError, OSError):
                pass
            raise ArchiveReservationError(ref) from exc
        return ref

    def _setup_ref(self, ref: AttemptRef) -> None:
        if validate_ref(ref) != self.root:
            raise ArchiveFormatError("Foreign setup reference.")

    def setup_config(self, ref: AttemptRef) -> AttemptConfig:
        self._setup_ref(ref)
        data = _setup_document(ref)
        return AttemptConfig(**cast(dict[str, object], data["requested_config"]))

    def reserve_setup(self, requested: AttemptConfig) -> AttemptRef:
        if not isinstance(requested, AttemptConfig) or requested.mode != "ollama":
            raise ArchiveFormatError("Setup requires Ollama configuration.")
        ref = self._allocate(uuid4().hex)
        self._create_lock(ref)
        with AttemptLease(ref):
            atomic_document(
                ref.directory / "setup.json",
                {
                    "format": 1,
                    "lineage_id": ref.lineage_id,
                    "attempt_id": ref.attempt_id,
                    "requested_config": config_document(requested),
                    "reserved_at": datetime.now(UTC).isoformat(),
                },
            )
        return ref

    def reserve_fork_setup(
        self,
        attempt_id: str,
        revision: int | None,
        *,
        requested: AttemptConfig | None = None,
    ) -> AttemptRef:
        with self.open_attempt(attempt_id) as parent:
            if parent.config.mode != "ollama":
                raise ArchiveFormatError("Fork setup requires Ollama parent.")
            point = parent.fork_point(revision)
            source_config = parent.config
            if requested is None:
                requested = source_config
            if (
                not isinstance(requested, AttemptConfig)
                or (
                    requested.mode,
                    requested.scenario_key,
                    requested.seed,
                    requested.software_revision,
                )
                != (
                    source_config.mode,
                    source_config.scenario_key,
                    source_config.seed,
                    source_config.software_revision,
                )
                or canonical(
                    {
                        k: v
                        for k, v in requested.settings.items()
                        if k not in {"provider", "limits"}
                    }
                )
                != canonical(
                    {
                        k: v
                        for k, v in source_config.settings.items()
                        if k not in {"provider", "limits"}
                    }
                )
            ):
                raise ArchiveFormatError("Invalid fork setup configuration.")
            inputs = load_retained_inputs(parent.ref)
            fork = {
                "parent": (attempt_id, point.checkpoint.revision),
                "parent_journal": asdict(point.journal_boundary),
                "checkpoint_sha256": _checkpoint_hash(point.checkpoint),
                "source_config_sha256": _config_hash(source_config),
                "input_hashes": dict(inputs.hashes),
            }
            ref = self._allocate(parent.ref.lineage_id)
            intent = {
                "format": 1,
                "lineage_id": ref.lineage_id,
                "attempt_id": ref.attempt_id,
                "requested_config": config_document(requested),
                "reserved_at": datetime.now(UTC).isoformat(),
                "fork": fork,
            }
            try:
                # This unique allocation has not escaped to a caller. Persist its
                # captured linkage before attempting to create the ownership lock.
                atomic_document(ref.directory / "setup.json", intent)
                self._create_lock(ref)
                with AttemptLease(ref):
                    retain_inputs(ref, inputs.scenario_path, tape_path=inputs.tape_path)
            except (ArchiveError, OSError) as exc:
                try:
                    self._fail_fork_allocation(ref, intent)
                except (ArchiveError, OSError):
                    pass
                raise ArchiveReservationError(ref) from exc
        return ref

    def _fail_fork_allocation(
        self, ref: AttemptRef, intent: Mapping[str, object]
    ) -> None:
        """Best effort evidence for this unique, still-unreturned allocation only."""
        self._setup_ref(ref)
        if any(
            safe_path(ref.directory / name).exists()
            for name in ("attempt.json", "archive.sqlite3", "setup_complete.json")
        ):
            raise ArchiveError("Final setup publication already begun.")

        def preserve_intent() -> None:
            path = safe_path(ref.directory / "setup.json")
            if not path.exists():
                atomic_document(path, intent)
            if canonical(_setup_document(ref)) != canonical(intent):
                raise ArchiveFormatError("Allocated setup intent mismatch.")

        lock = safe_path(ref.directory / "owner.lock")
        if lock.exists():
            # Never bypass another owner, even during private allocation failure.
            with AttemptLease(ref):
                preserve_intent()
                self.fail_setup(ref, "setup_failed")
            return

        # No normal setup lease can be acquired without this lock or an ordinary
        # published reservation. Only this private creation path owns the directory.
        preserve_intent()
        failure = safe_path(ref.directory / "setup_failure.json")
        if failure.exists():
            if _setup_document(ref, True)["code"] != "setup_failed":
                raise ArchiveError("Divergent setup failure.")
            return
        atomic_document(
            failure,
            {
                "format": 1,
                "lineage_id": ref.lineage_id,
                "attempt_id": ref.attempt_id,
                "code": "setup_failed",
                "ended_at": datetime.now(UTC).isoformat(),
            },
        )

    def _setup_checkpoint(
        self, ref: AttemptRef, fork: Mapping[str, object]
    ) -> Checkpoint:
        pair = parent_pair(fork["parent"])
        assert pair is not None
        boundary = parent_boundary(fork["parent_journal"], pair)
        assert boundary is not None
        with self.open_attempt(pair[0]) as parent:
            if parent.ref.lineage_id != ref.lineage_id:
                raise ArchiveFormatError("Setup parent lineage mismatch.")
            checkpoint = parent.checkpoint(pair[1])
            if (
                _config_hash(parent.config) != fork["source_config_sha256"]
                or load_retained_inputs(parent.ref).hashes != fork["input_hashes"]
                or _checkpoint_hash(checkpoint) != fork["checkpoint_sha256"]
                or parent.journal_boundary(through_sequence=boundary.sequence)
                != boundary
            ):
                raise ArchiveFormatError("Setup parent evidence mismatch.")
            return checkpoint

    def _pending_setup(self, ref: AttemptRef) -> AttemptConfig:
        requested = self.setup_config(ref)
        if not AttemptLease.owned_by_current_thread(ref):
            raise ArchiveError("Setup publication requires current thread lease.")
        if any(
            safe_path(ref.directory / name).exists()
            for name in ("attempt.json", "archive.sqlite3", "setup_complete.json")
        ):
            raise ArchiveError("Final setup publication already begun.")
        return requested

    def complete_setup(self, ref: AttemptRef, effective: AttemptConfig) -> None:
        requested = self._pending_setup(ref)
        if safe_path(ref.directory / "setup_failure.json").exists():
            _setup_document(ref, True)
            raise ArchiveError("Setup already failed.")
        validate_setup_config(requested, effective)
        load_retained_inputs(ref)
        data = _setup_document(ref)
        fork = cast(Mapping[str, object] | None, data.get("fork"))
        checkpoint = None if fork is None else self._setup_checkpoint(ref, fork)
        parent = None if fork is None else parent_pair(fork["parent"])
        boundary = (
            None if fork is None else parent_boundary(fork["parent_journal"], parent)
        )
        payload = {
            "format": 1,
            "lineage_id": ref.lineage_id,
            "attempt_id": ref.attempt_id,
            "config": config_document(effective),
            "parent": parent,
            "parent_journal": None if boundary is None else asdict(boundary),
            "reserved_at": data["reserved_at"],
            "reservation_error": None,
        }
        try:
            _publish_archive(ref, effective, payload, parent, boundary)
            if checkpoint is not None:
                with AttemptArchive.open(ref, read_only=False) as child:
                    child.commit(
                        checkpoint.snapshot,
                        expected_revision=None,
                        driver_cursor=checkpoint.driver_cursor,
                        feedback_cursor=checkpoint.feedback_cursor,
                        entries=(),
                    )
            atomic_document(
                ref.directory / "setup_complete.json",
                {
                    "format": 1,
                    "lineage_id": ref.lineage_id,
                    "attempt_id": ref.attempt_id,
                    "config_sha256": hashlib.sha256(
                        canonical(config_document(effective)).encode()
                    ).hexdigest(),
                },
            )
        except (ArchiveError, OSError) as exc:
            raise ArchiveReservationError(ref) from exc

    def fail_setup(self, ref: AttemptRef, code: str) -> None:
        self._pending_setup(ref)
        if not isinstance(code, str) or code not in SETUP_CODES:
            raise ArchiveFormatError("Invalid setup failure code.")
        path = safe_path(ref.directory / "setup_failure.json")
        if path.exists():
            if _setup_document(ref, True)["code"] != code:
                raise ArchiveError("Divergent setup failure.")
            return
        atomic_document(
            path,
            {
                "format": 1,
                "lineage_id": ref.lineage_id,
                "attempt_id": ref.attempt_id,
                "code": code,
                "ended_at": datetime.now(UTC).isoformat(),
            },
        )

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
        setup = safe_path(ref.directory / "setup.json")
        requested = self.setup_config(ref) if setup.exists() else None
        if (
            requested is not None
            and safe_path(ref.directory / "setup_failure.json").exists()
        ):
            _setup_document(ref, True)
            raise ArchiveError("Setup failed.")
        if requested is not None:
            config = validate_setup_reservation(ref, requested)
            _validate_setup_complete(ref, config)
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
                    requested is not None
                    or archive.latest_revision is not None
                    or (ref.directory / "inputs.json").exists()
                ):
                    load_retained_inputs(ref)
                if requested is not None:
                    data = _setup_document(ref)
                    if "fork" in data:
                        fork = cast(Mapping[str, object], data["fork"])
                        if (
                            _checkpoint_hash(archive.checkpoint(0))
                            != fork["checkpoint_sha256"]
                        ):
                            raise ArchiveFormatError(
                                "Setup initial checkpoint mismatch."
                            )
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
                if ref.attempt_id in duplicates:
                    raise ArchiveFormatError("Duplicate attempt identity.")
                setup = safe_path(ref.directory / "setup.json")
                if setup.exists():
                    config = self.setup_config(ref)
                    data = _setup_document(ref)
                    started = cast(str, data["reserved_at"])
                    if "fork" in data:
                        parent = parent_pair(
                            cast(Mapping[str, object], data["fork"])["parent"]
                        )
                    reservation = safe_path(ref.directory / "attempt.json")
                    effective = (
                        validate_setup_reservation(ref, config)
                        if reservation.exists()
                        else None
                    )
                    complete = safe_path(ref.directory / "setup_complete.json").exists()
                    if complete:
                        if effective is None:
                            raise ArchiveFormatError(
                                "Completed setup lacks reservation."
                            )
                        _validate_setup_complete(ref, effective)
                    if safe_path(ref.directory / "inputs.json").exists():
                        load_retained_inputs(ref)
                    final = [
                        safe_path(ref.directory / n).exists()
                        for n in ("attempt.json", "archive.sqlite3")
                    ]
                    failed = safe_path(ref.directory / "setup_failure.json").exists()
                    if failed:
                        data = _setup_document(ref, True)
                        if any(final) or complete:
                            raise ArchiveFormatError(
                                "Failure/final publication conflict."
                            )
                        lifecycle, failure, ended = (
                            "failed",
                            cast(str, data["code"]),
                            cast(str, data["ended_at"]),
                        )
                    elif not complete:
                        owned = AttemptLease.is_owned(ref)
                        lifecycle = (
                            "initializing"
                            if owned
                            else ("failed" if any(final) else "interrupted")
                        )
                        failure = (
                            "archive_incomplete" if any(final) and not owned else None
                        )
                    else:
                        lifecycle = ""
                    if lifecycle:
                        result.append(
                            AttemptSummary(
                                ref,
                                config.mode,
                                config.scenario_key,
                                parent,
                                started,
                                ended,
                                lifecycle,
                                None,
                                None,
                                failure,
                            )
                        )
                        continue
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
                failure = (
                    "archive_incomplete"
                    if missing and not (ref.directory / "setup.json").exists()
                    else "archive_invalid"
                )
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
            try:
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
            except Exception as exc:
                raise ArchiveReservationError(ref) from exc
            return ref
