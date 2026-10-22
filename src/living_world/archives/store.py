"""Atomic SQLite checkpoints and validated append-only attempt audit storage."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from living_world.archives.model import (
    STATES,
    ArchiveError,
    ArchiveFormatError,
    ArchiveRevisionConflict,
    AttemptConfig,
    AttemptRef,
    Checkpoint,
    CommandReceipt,
    ForkPoint,
    JournalBoundary,
    JournalEntry,
    JournalRecord,
    canonical,
    document,
    envelope,
    frozen_map,
    identifier,
    integer,
    loads,
    parent_boundary,
    receipt,
    text,
    validate_offered,
)
from living_world.repositories.world_snapshot import (
    WorldSnapshot,
    decode_world,
    encode_world,
)
from living_world.state.world_state import WorldState

_SCHEMA = """
CREATE TABLE archive_meta(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
CREATE TABLE world_snapshots(id INTEGER PRIMARY KEY CHECK(id=1), schema_version INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE checkpoints(revision INTEGER PRIMARY KEY CHECK(revision>=0), schema_version INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, driver_cursor TEXT NOT NULL, feedback_cursor TEXT NOT NULL, operation TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE);
CREATE TABLE journal(sequence INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL, checkpoint_revision INTEGER REFERENCES checkpoints(revision), revision_context INTEGER REFERENCES checkpoints(revision));
CREATE TABLE commands(command_id TEXT PRIMARY KEY, envelope TEXT NOT NULL, envelope_hash TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE lifecycle(sequence INTEGER PRIMARY KEY AUTOINCREMENT, state TEXT NOT NULL, reason TEXT, timestamp TEXT NOT NULL, journal_sequence INTEGER UNIQUE REFERENCES journal(sequence));
"""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _validate_timestamp(value: object) -> None:
    try:
        parsed = datetime.fromisoformat(text(value))
        if parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError()
    except ValueError as exc:
        raise ArchiveFormatError("Expected UTC timestamp.") from exc


def _path(ref: AttemptRef) -> Path:
    if not isinstance(ref, AttemptRef):
        raise ArchiveFormatError("Expected AttemptRef.")
    directory = ref.directory.absolute()
    for part in (directory, *directory.parents):
        if part.is_symlink():
            raise ArchiveFormatError("Archive directory cannot traverse symlinks.")
    result = directory / "archive.sqlite3"
    if result.is_symlink():
        raise ArchiveFormatError("Archive database cannot be a symlink.")
    return result


class AttemptArchive:
    """An engine-only archive handle; every write owns one explicit transaction."""

    def __init__(self, ref: AttemptRef, *, read_only: bool) -> None:
        if type(read_only) is not bool:
            raise ArchiveFormatError("read_only must be boolean.")
        self._ref = ref
        self._database_path = _path(ref)
        self._read_only = read_only
        self._owner = threading.get_ident()
        self._closed = False

    @classmethod
    def create(
        cls,
        ref: AttemptRef,
        config: AttemptConfig,
        *,
        parent: tuple[str, int] | None = None,
        parent_journal_boundary: JournalBoundary | None = None,
    ) -> AttemptArchive:
        archive = cls(ref, read_only=False)
        if not isinstance(config, AttemptConfig):
            raise ArchiveFormatError("Expected AttemptConfig.")
        if parent is not None:
            if not isinstance(parent, tuple) or len(parent) != 2:
                raise ArchiveFormatError("Expected parent attempt/revision pair.")
            identifier(parent[0])
            integer(parent[1])
        if parent_journal_boundary is not None:
            if not isinstance(parent_journal_boundary, JournalBoundary):
                raise ArchiveFormatError("Expected JournalBoundary.")
            parent_boundary(asdict(parent_journal_boundary), parent)
        try:
            descriptor = os.open(
                archive.database_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
            os.close(descriptor)
            with archive._connect() as connection:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.executescript(_SCHEMA)
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO archive_meta VALUES(1,?)",
                    (
                        canonical(
                            {
                                "format": 1,
                                "lineage_id": ref.lineage_id,
                                "attempt_id": ref.attempt_id,
                                "config": {
                                    "mode": config.mode,
                                    "scenario_key": config.scenario_key,
                                    "seed": config.seed,
                                    "software_revision": config.software_revision,
                                    "settings": config.settings,
                                },
                                "parent": parent,
                                "parent_journal": (
                                    None
                                    if parent_journal_boundary is None
                                    else asdict(parent_journal_boundary)
                                ),
                                "created_at": _timestamp(),
                            }
                        ),
                    ),
                )
                connection.commit()
        except (OSError, sqlite3.Error) as exc:
            raise ArchiveError("Could not create new archive.") from exc
        archive._read_metadata()
        return archive

    @classmethod
    def open(cls, ref: AttemptRef, *, read_only: bool = False) -> AttemptArchive:
        archive = cls(ref, read_only=read_only)
        archive._read_metadata()
        with archive._connect() as connection:
            archive._validate(connection)
        return archive

    @property
    def database_path(self) -> Path:
        return self._database_path

    @property
    def ref(self) -> AttemptRef:
        return self._ref

    @property
    def config(self) -> AttemptConfig:
        return self._config

    @property
    def parent(self) -> tuple[str, int] | None:
        return self._parent

    @property
    def parent_journal_boundary(self) -> JournalBoundary | None:
        return self._parent_journal_boundary

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def latest_revision(self) -> int | None:
        with self._connect() as connection:
            checkpoints = self._validate(connection)
            return checkpoints[-1].revision if checkpoints else None

    @contextmanager
    def _connect(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        if self._closed:
            raise ArchiveError("Archive is closed.")
        if write and (self._read_only or self._owner != threading.get_ident()):
            raise ArchiveError("Archive writer ownership violation.")
        _path(self.ref)
        connection: sqlite3.Connection | None = None
        try:
            mode = "ro" if self._read_only else "rw"
            connection = sqlite3.connect(
                self.database_path.as_uri() + "?mode=" + mode,
                uri=True,
                isolation_level=None,
            )
            connection.execute("PRAGMA foreign_keys=ON")
            if write:
                connection.execute("BEGIN IMMEDIATE")
            else:
                connection.execute("BEGIN")
            yield connection
            if write:
                connection.commit()
        except sqlite3.Error as exc:
            raise ArchiveError("Archive SQLite operation failed.") from exc
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise ArchiveFormatError("Malformed archive data.") from exc
        finally:
            if connection is not None:
                if connection.in_transaction:
                    connection.rollback()
                connection.close()

    def _read_metadata(self) -> None:
        with self._connect() as connection:
            self._metadata(connection)

    def _metadata(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute("SELECT id,payload FROM archive_meta").fetchall()
        if len(rows) != 1 or rows[0][0] != 1:
            raise ArchiveFormatError("Missing archive metadata.")
        meta = document(
            loads(rows[0][1]),
            {"format", "lineage_id", "attempt_id", "config", "parent", "created_at"},
            {"parent_journal"},
        )
        if type(meta["format"]) is not int or meta["format"] != 1:
            raise ArchiveFormatError("Unsupported archive format.")
        if (
            meta["lineage_id"] != self.ref.lineage_id
            or meta["attempt_id"] != self.ref.attempt_id
        ):
            raise ArchiveFormatError("Archive identity mismatch.")
        self._config = AttemptConfig(
            **document(
                meta["config"],
                {"mode", "scenario_key", "seed", "software_revision", "settings"},
            )
        )
        parent = meta["parent"]
        if parent is not None:
            if not isinstance(parent, tuple) or len(parent) != 2:
                raise ArchiveFormatError("Malformed parent.")
            self._parent = (identifier(parent[0]), integer(parent[1]))
        else:
            self._parent = None
        self._parent_journal_boundary = parent_boundary(
            meta.get("parent_journal"), self._parent
        )
        _validate_timestamp(meta["created_at"])
        self._created_at = meta["created_at"]

    @staticmethod
    def _journal(
        connection: sqlite3.Connection,
    ) -> tuple[tuple[int, JournalEntry, int | None, int | None], ...]:
        result = []
        for sequence, kind, payload, revision, context in connection.execute(
            "SELECT sequence,kind,payload,checkpoint_revision,revision_context FROM journal ORDER BY sequence"
        ):
            integer(sequence, minimum=1)
            if revision is not None:
                integer(revision)
            if context is not None:
                integer(context)
            result.append(
                (sequence, JournalEntry(kind, loads(payload)), revision, context)
            )
        return tuple(result)

    @staticmethod
    def _audit(
        rows: tuple[tuple[int, JournalEntry, int | None, int | None], ...],
    ) -> dict[str, tuple[str, CommandReceipt]]:
        requests: dict[str, JournalEntry] = {}
        responses: set[str] = set()
        validated: dict[str, Mapping[str, object]] = {}
        resolved: set[str] = set()
        slots: set[tuple[object, object, object]] = set()
        commands: dict[str, tuple[str, CommandReceipt]] = {}
        identities: set[tuple[str, str]] = set()
        for _, entry, checkpoint_revision, revision_context in rows:
            p = entry.payload
            kind = entry.kind
            identity = AttemptArchive._identity(entry)
            if identity is not None:
                if identity in identities:
                    raise ArchiveFormatError("Duplicate journal identity.")
                identities.add(identity)
            if kind in ("request_started", "response_reused"):
                requests[p["request_id"]] = entry
                if kind == "response_reused":
                    responses.add(p["request_id"])
                    validated[p["request_id"]] = p["decision"]
            elif kind in ("response_validated", "response_failed", "action_resolved"):
                request_id = p["request_id"]
                if request_id not in requests:
                    raise ArchiveFormatError("Unknown inference request.")
                started = requests[request_id].payload
                if kind == "action_resolved":
                    slot = (p["base_revision"], p["source_tick"], p["actor_label"])
                    if (
                        any(
                            p[key] != started[key]
                            for key in ("base_revision", "source_tick", "actor_label")
                        )
                        or request_id not in validated
                        or checkpoint_revision is None
                        or checkpoint_revision != p["base_revision"] + 1
                        or (p["outcome"] == "no_action")
                        != (validated.get(request_id, {}).get("action_request") is None)
                        or request_id in resolved
                        or slot in slots
                    ):
                        raise ArchiveFormatError(
                            "Mismatching or duplicate action slot."
                        )
                    resolved.add(request_id)
                    slots.add(slot)
                else:
                    if request_id in responses:
                        raise ArchiveFormatError("Contradictory inference response.")
                    responses.add(request_id)
                    if kind == "response_validated":
                        validate_offered(p["decision"], started["request"])
                        validated[request_id] = p["decision"]
            elif kind == "control_requested":
                command = envelope(p["envelope"])
                if command.command_id in commands:
                    raise ArchiveFormatError("Duplicate command.")
                commands[command.command_id] = (
                    canonical(p["envelope"]),
                    CommandReceipt(
                        command.command_id,
                        "queued",
                        p.get("admitted_state_version", command.expected_state_version),
                        revision_context or 0,
                        None,
                    ),
                )
            elif kind == "control_resolved":
                result = receipt(p["receipt"])
                if result.command_id not in commands:
                    raise ArchiveFormatError("Unknown command resolution.")
                encoded, previous = commands[result.command_id]
                if (
                    previous.status != "queued"
                    or result.status == "queued"
                    or result.state_version < previous.state_version
                    or result.revision < previous.revision
                ):
                    raise ArchiveFormatError("Invalid command settlement.")
                command = envelope(loads(encoded))
                if (
                    command.action == "step"
                    and result.status == "applied"
                    and result.revision != checkpoint_revision
                ):
                    raise ArchiveFormatError(
                        "Applied step requires its checkpoint transaction."
                    )
                commands[result.command_id] = (encoded, result)
        return commands

    @staticmethod
    def _identity(entry: JournalEntry) -> tuple[str, str] | None:
        if entry.kind in ("request_started", "response_reused"):
            return ("request_started", entry.payload["request_id"])
        if entry.kind == "action_resolved":
            return (entry.kind, entry.payload["request_id"])
        if entry.kind.startswith("response_"):
            return ("response", entry.payload["request_id"])
        if entry.kind == "control_requested":
            return (entry.kind, entry.payload["envelope"]["command_id"])
        if entry.kind == "control_resolved":
            return (entry.kind, entry.payload["receipt"]["command_id"])
        return None

    def _validate(self, connection: sqlite3.Connection) -> tuple[Checkpoint, ...]:
        self._metadata(connection)
        result: list[Checkpoint] = []
        operations: list[Mapping[str, object]] = []
        for row in connection.execute(
            "SELECT revision,schema_version,payload,digest,driver_cursor,feedback_cursor,operation,fingerprint FROM checkpoints ORDER BY revision"
        ):
            (
                revision,
                schema,
                payload,
                saved_digest,
                driver,
                feedback,
                operation,
                fingerprint,
            ) = row
            if integer(revision) != len(result):
                raise ArchiveFormatError("Noncontiguous checkpoint revisions.")
            snapshot = WorldSnapshot(schema, payload)
            decode_world(snapshot)
            checkpoint = Checkpoint(revision, snapshot, loads(driver), loads(feedback))
            op = document(
                loads(operation),
                {
                    "expected_revision",
                    "schema_version",
                    "payload",
                    "driver_cursor",
                    "feedback_cursor",
                    "entries",
                },
            )
            if (
                canonical(op) != operation
                or _hash(operation) != fingerprint
                or saved_digest != snapshot.digest
                or op["expected_revision"] != (revision - 1 if revision else None)
                or type(op["schema_version"]) is not int
                or op["schema_version"] != schema
                or op["payload"] != payload
                or op["driver_cursor"] != checkpoint.driver_cursor
                or op["feedback_cursor"] != checkpoint.feedback_cursor
            ):
                raise ArchiveFormatError("Checkpoint digest or operation mismatch.")
            if op["expected_revision"] is not None:
                integer(op["expected_revision"])
            operations.append(op)
            result.append(checkpoint)
        worlds = connection.execute(
            "SELECT id,schema_version,payload FROM world_snapshots"
        ).fetchall()
        if result:
            latest = result[-1].snapshot
            if worlds != [(1, latest.schema_version, latest.payload)]:
                raise ArchiveFormatError("Current world/checkpoint mismatch.")
        elif worlds:
            raise ArchiveFormatError("World without checkpoint.")
        rows = self._journal(connection)
        if any(
            revision is not None and revision >= len(result)
            for _, _, revision, _ in rows
        ):
            raise ArchiveFormatError("Journal references missing checkpoint.")
        for _, _, revision, context in rows:
            if context is not None and context >= len(result):
                raise ArchiveFormatError(
                    "Journal context references missing checkpoint."
                )
            if revision is not None and revision != context:
                raise ArchiveFormatError("Checkpoint journal context mismatch.")
        for revision, operation in enumerate(operations):
            entries = operation["entries"]
            if not isinstance(entries, tuple):
                raise ArchiveFormatError("Malformed checkpoint operation entries.")
            remaining = [entry for _, entry, owner, _ in rows if owner == revision]
            for item in entries:
                item = document(item, {"kind", "payload"})
                entry = JournalEntry(item["kind"], item["payload"])
                if entry in remaining:
                    remaining.remove(entry)
                elif (
                    entry.kind in ("control_resolved", "action_resolved")
                    or self._identity(entry) is None
                    or not any(
                        old == entry and (owner is None or owner < revision)
                        for _, old, owner, _ in rows
                    )
                ):
                    raise ArchiveFormatError("Checkpoint audit entry missing.")
            if remaining:
                raise ArchiveFormatError("Unexpected checkpoint audit entry.")
        for _, entry, revision, _ in rows:
            if entry.kind == "action_resolved":
                base = entry.payload["base_revision"]
                tick = entry.payload["source_tick"]
                if (
                    revision is None
                    or base >= len(result)
                    or revision != base + 1
                    or decode_world(result[base].snapshot).tick != tick
                    or decode_world(result[revision].snapshot).tick != tick + 1
                ):
                    raise ArchiveFormatError(
                        "Action resolution tick/checkpoint mismatch."
                    )
        commands = self._audit(rows)
        stored = {}
        for command_id, encoded, envelope_hash, encoded_result in connection.execute(
            "SELECT command_id,envelope,envelope_hash,result FROM commands"
        ):
            if _hash(encoded) != envelope_hash:
                raise ArchiveFormatError("Command envelope hash mismatch.")
            parsed = receipt(loads(encoded_result))
            if command_id != parsed.command_id:
                raise ArchiveFormatError("Command identity mismatch.")
            stored[command_id] = (encoded, parsed)
        if commands != stored:
            raise ArchiveFormatError("Command ledger/journal mismatch.")
        self._lifecycle(connection)
        terminal_entries = {
            sequence: entry
            for sequence, entry, _, _ in rows
            if entry.kind == "attempt_finished"
        }
        effects = {}
        for state, reason, journal_sequence in connection.execute(
            "SELECT state,reason,journal_sequence FROM lifecycle WHERE journal_sequence IS NOT NULL"
        ):
            integer(journal_sequence, minimum=1)
            if journal_sequence not in terminal_entries or journal_sequence in effects:
                raise ArchiveFormatError("Invalid terminal lifecycle journal link.")
            effects[journal_sequence] = (state, reason)
        expected_effects = {
            sequence: (entry.payload["lifecycle"], entry.payload["outcome"])
            for sequence, entry in terminal_entries.items()
        }
        if effects != expected_effects:
            raise ArchiveFormatError("Terminal journal/lifecycle mismatch.")
        return tuple(result)

    def checkpoint(self, revision: int | None = None) -> Checkpoint:
        if revision is not None:
            integer(revision)
        with self._connect() as connection:
            checkpoints = self._validate(connection)
            if not checkpoints or (
                revision is not None and revision >= len(checkpoints)
            ):
                raise ArchiveError("Complete checkpoint does not exist.")
            return checkpoints[-1] if revision is None else checkpoints[revision]

    @staticmethod
    def _prefix(
        rows: tuple[tuple[int, JournalEntry, int | None, int | None], ...],
        through_sequence: int | None,
    ) -> tuple[JournalRecord, ...]:
        if through_sequence is not None:
            integer(through_sequence)
            if through_sequence != 0 and not any(
                row[0] == through_sequence for row in rows
            ):
                raise ArchiveFormatError("Journal boundary sequence does not exist.")
        return tuple(
            JournalRecord(*row)
            for row in rows
            if through_sequence is None or row[0] <= through_sequence
        )

    @staticmethod
    def _boundary(records: tuple[JournalRecord, ...]) -> JournalBoundary:
        payload = tuple(
            {
                "sequence": record.sequence,
                "kind": record.entry.kind,
                "payload": record.entry.payload,
                "checkpoint_revision": record.checkpoint_revision,
                "revision_context": record.revision_context,
            }
            for record in records
        )
        return JournalBoundary(
            records[-1].sequence if records else 0, _hash(canonical(payload))
        )

    def journal_records(
        self, *, through_sequence: int | None = None
    ) -> tuple[JournalRecord, ...]:
        with self._connect() as connection:
            self._validate(connection)
            return self._prefix(self._journal(connection), through_sequence)

    def journal_boundary(
        self, *, through_sequence: int | None = None
    ) -> JournalBoundary:
        with self._connect() as connection:
            self._validate(connection)
            return self._boundary(
                self._prefix(self._journal(connection), through_sequence)
            )

    def fork_point(self, revision: int | None = None) -> ForkPoint:
        if revision is not None:
            integer(revision)
        with self._connect() as connection:
            checkpoints = self._validate(connection)
            if not checkpoints or (
                revision is not None and revision >= len(checkpoints)
            ):
                raise ArchiveError("Complete checkpoint does not exist.")
            checkpoint = checkpoints[-1] if revision is None else checkpoints[revision]
            return ForkPoint(
                checkpoint,
                self._boundary(self._prefix(self._journal(connection), None)),
            )

    def load_world(self) -> WorldState:
        return decode_world(self.checkpoint().snapshot)

    def save_world(self, state: WorldState) -> None:
        if self.config.mode != "recorded":
            raise ArchiveError("Compatibility save_world requires recorded mode.")
        latest = self.latest_revision
        old = self.checkpoint(latest) if latest is not None else None
        try:
            snapshot = encode_world(state)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ArchiveFormatError("Invalid world state.") from exc
        self.commit(
            snapshot,
            expected_revision=latest,
            driver_cursor={} if old is None else old.driver_cursor,
            feedback_cursor={} if old is None else old.feedback_cursor,
            entries=(),
        )

    def commit(
        self,
        snapshot: WorldSnapshot,
        *,
        expected_revision: int | None,
        driver_cursor: Mapping[str, object],
        feedback_cursor: Mapping[str, object],
        entries: tuple[JournalEntry, ...],
    ) -> Checkpoint:
        if expected_revision is not None:
            integer(expected_revision)
        try:
            decode_world(snapshot)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ArchiveFormatError("Invalid world snapshot.") from exc
        candidate = Checkpoint(
            0 if expected_revision is None else expected_revision + 1,
            snapshot,
            driver_cursor,
            feedback_cursor,
        )
        self._validate_entries(entries)
        operation = canonical(
            {
                "expected_revision": expected_revision,
                "schema_version": snapshot.schema_version,
                "payload": snapshot.payload,
                "driver_cursor": candidate.driver_cursor,
                "feedback_cursor": candidate.feedback_cursor,
                "entries": tuple(
                    {"kind": entry.kind, "payload": entry.payload} for entry in entries
                ),
            }
        )
        fingerprint = _hash(operation)
        with self._connect(write=True) as connection:
            checkpoints = self._validate(connection)
            previous = connection.execute(
                "SELECT revision FROM checkpoints WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
            if previous is not None:
                return checkpoints[previous[0]]
            latest = checkpoints[-1].revision if checkpoints else None
            if latest != expected_revision:
                raise ArchiveRevisionConflict("Expected checkpoint revision changed.")
            connection.execute(
                "INSERT INTO world_snapshots VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version,payload=excluded.payload",
                (snapshot.schema_version, snapshot.payload),
            )
            connection.execute(
                "INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?,?)",
                (
                    candidate.revision,
                    snapshot.schema_version,
                    snapshot.payload,
                    snapshot.digest,
                    canonical(candidate.driver_cursor),
                    canonical(candidate.feedback_cursor),
                    operation,
                    fingerprint,
                ),
            )
            self._record(connection, entries, revision=candidate.revision)
            self._validate(connection)
        return candidate

    @staticmethod
    def _validate_entries(entries: tuple[JournalEntry, ...]) -> None:
        if not isinstance(entries, tuple) or any(
            not isinstance(entry, JournalEntry) for entry in entries
        ):
            raise ArchiveFormatError("Expected tuple of JournalEntry values.")
        for entry in entries:
            JournalEntry(entry.kind, entry.payload)

    def _record(
        self,
        connection: sqlite3.Connection,
        entries: tuple[JournalEntry, ...],
        *,
        revision: int | None,
    ) -> tuple[int, ...]:
        rows = list(self._journal(connection))
        sequences = []
        latest = connection.execute("SELECT MAX(revision) FROM checkpoints").fetchone()[
            0
        ]
        for entry in entries:
            if entry.kind == "action_resolved" and revision is None:
                raise ArchiveFormatError(
                    "Action resolution requires a checkpoint transaction."
                )
            identity = self._identity(entry)
            duplicate = next(
                (
                    (sequence, old, owner)
                    for sequence, old, owner, _ in rows
                    if identity is not None and self._identity(old) == identity
                ),
                None,
            )
            if duplicate is not None:
                sequence, old, owner = duplicate
                if (
                    entry.kind in ("control_resolved", "action_resolved")
                    and revision is not None
                    and owner != revision
                ):
                    raise ArchiveRevisionConflict(
                        "Settlement belongs to another checkpoint."
                    )
                if old.kind != entry.kind or canonical(old.payload) != canonical(
                    entry.payload
                ):
                    raise ArchiveRevisionConflict("Divergent journal identity reuse.")
                sequences.append(sequence)
                continue
            cursor = connection.execute(
                "INSERT INTO journal(kind,payload,checkpoint_revision,revision_context) VALUES(?,?,?,?)",
                (entry.kind, canonical(entry.payload), revision, latest),
            )
            sequence = cursor.lastrowid
            rows.append((sequence, entry, revision, latest))
            sequences.append(sequence)
            if entry.kind == "attempt_finished":
                self._insert_lifecycle(
                    connection,
                    entry.payload["lifecycle"],
                    entry.payload["outcome"],
                    journal_sequence=sequence,
                )
        commands = self._audit(tuple(rows))
        for command_id, (encoded, result) in commands.items():
            connection.execute(
                "INSERT INTO commands VALUES(?,?,?,?) ON CONFLICT(command_id) DO UPDATE SET result=excluded.result",
                (command_id, encoded, _hash(encoded), canonical(asdict(result))),
            )
        return tuple(sequences)

    def append(self, entry: JournalEntry) -> int:
        return self.record((entry,))[0]

    def record(
        self,
        entries: tuple[JournalEntry, ...],
        *,
        lifecycle: str | None = None,
        reason: str | None = None,
    ) -> tuple[int, ...]:
        self._validate_entries(entries)
        if lifecycle is not None:
            self._validate_lifecycle(lifecycle, reason)
        elif reason is not None:
            raise ArchiveFormatError("Lifecycle reason requires state.")
        with self._connect(write=True) as connection:
            self._validate(connection)
            sequences = self._record(connection, entries, revision=None)
            if lifecycle is not None:
                self._insert_lifecycle(connection, lifecycle, reason)
            self._validate(connection)
            return sequences

    def entries(self) -> tuple[JournalEntry, ...]:
        with self._connect() as connection:
            self._validate(connection)
            return tuple(entry for _, entry, _, _ in self._journal(connection))

    def command(self, command_id: str) -> CommandReceipt | None:
        text(command_id)
        with self._connect() as connection:
            self._validate(connection)
            row = connection.execute(
                "SELECT result FROM commands WHERE command_id=?", (command_id,)
            ).fetchone()
            return None if row is None else receipt(loads(row[0]))

    @staticmethod
    def _validate_lifecycle(state: object, reason: object) -> None:
        if not isinstance(state, str) or state not in STATES:
            raise ArchiveFormatError("Unknown lifecycle state.")
        if reason is not None:
            text(reason)

    @classmethod
    def _insert_lifecycle(
        cls,
        connection: sqlite3.Connection,
        state: str,
        reason: str | None,
        *,
        journal_sequence: int | None = None,
    ) -> None:
        cls._validate_lifecycle(state, reason)
        connection.execute(
            "INSERT INTO lifecycle(state,reason,timestamp,journal_sequence) VALUES(?,?,?,?)",
            (state, reason, _timestamp(), journal_sequence),
        )

    @classmethod
    def _lifecycle(
        cls, connection: sqlite3.Connection
    ) -> tuple[Mapping[str, object], ...]:
        result = []
        for sequence, state, reason, timestamp in connection.execute(
            "SELECT sequence,state,reason,timestamp FROM lifecycle ORDER BY sequence"
        ):
            integer(sequence, minimum=1)
            cls._validate_lifecycle(state, reason)
            _validate_timestamp(timestamp)
            result.append(
                frozen_map(
                    {
                        "sequence": sequence,
                        "state": state,
                        "reason": reason,
                        "timestamp": timestamp,
                    }
                )
            )
        return tuple(result)

    def lifecycle(self) -> tuple[Mapping[str, object], ...]:
        with self._connect() as connection:
            self._validate(connection)
            return self._lifecycle(connection)

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> Self:
        if self._closed:
            raise ArchiveError("Archive is closed.")
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
