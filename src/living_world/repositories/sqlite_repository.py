"""SQLite persistence for generic Living World records."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from living_world.repositories.world_snapshot import (
    _SUPPORTED_SCHEMA_VERSIONS,
    UnsupportedWorldSchemaError,
    WorldSnapshot,
    WorldSnapshotError,
    _deserialize_world,  # noqa: F401 -- compatibility re-export
    _serialize_world,  # noqa: F401 -- compatibility re-export
    decode_world,
    encode_world,
)
from living_world.state.world_state import WorldState


class RepositoryError(RuntimeError):
    """Base error for a repository persistence failure."""


class RepositoryLoadError(RepositoryError):
    """Raised when persisted data cannot be loaded safely."""


class RepositorySaveError(RepositoryError):
    """Raised when a world snapshot cannot be saved."""


class SQLiteRepository:
    """Store an atomic, versioned WorldState snapshot in a SQLite database."""

    def __init__(self, database_path: str, *, read_only: bool = False) -> None:
        if not database_path:
            raise RepositoryError("SQLite database path cannot be empty.")

        if type(read_only) is not bool:
            raise TypeError("read_only must be a boolean.")
        self._read_only = read_only
        self._database_path = Path(database_path)

    def load_world(self) -> WorldState:
        """Load and validate a full world snapshot without mutating callers."""

        try:
            with self._connect() as connection:
                if not self._read_only:
                    self._create_schema(connection)
                row = connection.execute(
                    "SELECT schema_version, payload FROM world_snapshots WHERE id = 1"
                ).fetchone()
        except sqlite3.Error as exc:
            raise RepositoryLoadError(
                f"Could not load SQLite world at '{self._database_path}'."
            ) from exc

        if row is None:
            if self._read_only:
                raise RepositoryLoadError("Saved world snapshot is required.")
            return WorldState()

        schema_version, payload = row
        if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            raise RepositoryLoadError(
                f"Unsupported world schema version {schema_version!r}."
            )
        try:
            return decode_world(WorldSnapshot(schema_version, payload))
        except UnsupportedWorldSchemaError as exc:
            raise RepositoryLoadError(str(exc)) from None
        except WorldSnapshotError as exc:
            raise RepositoryLoadError("Persisted world data is malformed.") from (
                exc.__cause__ or exc
            )

    def save_world(self, state: WorldState) -> None:
        """Serialize and atomically replace the persisted world snapshot."""

        if self._read_only:
            raise RepositorySaveError("Read-only repository cannot save.")
        try:
            snapshot = encode_world(state)
        except WorldSnapshotError as exc:
            raise RepositorySaveError("World state is not JSON serializable.") from (
                exc.__cause__ or exc
            )

        try:
            with self._connect() as connection:
                self._create_schema(connection)
                connection.execute(
                    """
                    INSERT INTO world_snapshots (id, schema_version, payload)
                    VALUES (1, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        schema_version = excluded.schema_version,
                        payload = excluded.payload
                    """,
                    (snapshot.schema_version, snapshot.payload),
                )
        except sqlite3.Error as exc:
            raise RepositorySaveError(
                f"Could not save SQLite world at '{self._database_path}'."
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        if self._read_only:
            return sqlite3.connect(
                self._database_path.resolve().as_uri() + "?mode=ro", uri=True
            )
        return sqlite3.connect(self._database_path)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS world_snapshots (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                schema_version INTEGER NOT NULL,
                payload TEXT NOT NULL
            )
            """)
