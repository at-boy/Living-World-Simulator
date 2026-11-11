"""Read-only full-store access rejects unsupported sources before native SQLite."""

import os
import sqlite3
import stat
from pathlib import Path
from uuid import uuid4

import pytest

from living_world.archives import (
    ArchiveFormatError,
    AttemptArchive,
    AttemptConfig,
    AttemptRef,
    JournalEntry,
)
from living_world.archives.sqlite_readonly import require_rollback_database
from living_world.archives.trace_analysis import read_trace_page
from living_world.repositories.world_snapshot import encode_world
from living_world.state.world_state import WorldState

_ERROR = r"^Read-only access requires rollback-journal archives\.$"


def create(directory: Path, *, catalog: bool = False) -> AttemptArchive:
    lineage, attempt = uuid4().hex, uuid4().hex
    if catalog:
        directory = directory / lineage / attempt
        directory.mkdir(parents=True)
    archive = AttemptArchive.create(
        AttemptRef(lineage, attempt, directory),
        AttemptConfig("recorded", "founders", 7, "revision", {}),
    )
    archive.commit(
        encode_world(WorldState()),
        expected_revision=None,
        driver_cursor={},
        feedback_cursor={},
        entries=(),
    )
    return archive


def inventory(root: Path) -> dict[Path, tuple[int, int, bytes | str | None]]:
    result = {}
    for path in (root, *root.rglob("*")):
        info = path.lstat()
        content: bytes | str | None = None
        if stat.S_ISREG(info.st_mode):
            content = path.read_bytes()
        elif stat.S_ISLNK(info.st_mode):
            content = os.readlink(path)
        result[path.relative_to(root)] = (info.st_mode, info.st_mtime_ns, content)
    return result


def forbidden_connect(*args: object, **kwargs: object) -> None:
    raise AssertionError("unsupported source reached sqlite3.connect")


def convert_to_wal(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
    finally:
        connection.close()
    assert not path.with_name(path.name + "-wal").exists()
    assert not path.with_name(path.name + "-shm").exists()
    assert path.read_bytes()[18:20] == b"\x02\x02"


@pytest.mark.parametrize(
    "source",
    [
        "wal",
        "wal_present",
        "shm_present",
        "wal_dangling",
        "shm_dangling",
        "short",
        "magic",
        "read_version",
        "write_version",
        "missing",
        "directory",
        "fifo",
        "symlink",
        "dangling_symlink",
    ],
)
def test_unsupported_store_source_rejects_before_sqlite_and_preserves_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    archive = create(tmp_path)
    identity, path = archive.ref, archive.database_path
    archive.close()
    if source == "wal":
        convert_to_wal(path)
    elif source.endswith(("present", "dangling")):
        suffix, kind = source.split("_")
        sidecar = path.with_name(path.name + "-" + suffix)
        if kind == "present":
            sidecar.write_bytes(b"opaque coordination file")
        else:
            sidecar.symlink_to(tmp_path / "absent-target")
    elif source in ("short", "magic", "read_version", "write_version"):
        if source == "short":
            path.write_bytes(b"SQLite format 3\x00")
        else:
            with path.open("r+b") as handle:
                handle.seek(
                    {"magic": 0, "write_version": 18, "read_version": 19}[source]
                )
                handle.write(b"\x03")
    else:
        path.unlink()
        if source == "directory":
            path.mkdir()
        elif source == "fifo":
            os.mkfifo(path)
        elif source in ("symlink", "dangling_symlink"):
            target = tmp_path / "target"
            if source == "symlink":
                target.write_bytes(b"preserved target")
            path.symlink_to(target)
    before = inventory(tmp_path)
    monkeypatch.setattr(sqlite3, "connect", forbidden_connect)
    message = (
        r"^Archive database cannot be a symlink\.$"
        if source in ("symlink", "dangling_symlink")
        else _ERROR
    )
    with pytest.raises(ArchiveFormatError, match=message):
        AttemptArchive.open(identity, read_only=True)
    assert inventory(tmp_path) == before


@pytest.mark.parametrize("change", ["wal", "wal_sidecar", "shm_sidecar"])
def test_existing_reader_rechecks_each_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    archive = create(tmp_path)
    with AttemptArchive.open(archive.ref, read_only=True) as reader:
        if change == "wal":
            convert_to_wal(archive.database_path)
        else:
            suffix = change.split("_")[0]
            archive.database_path.with_name("archive.sqlite3-" + suffix).write_bytes(
                b"external"
            )
        before = inventory(tmp_path)
        monkeypatch.setattr(sqlite3, "connect", forbidden_connect)
        for operation in (
            lambda: reader.latest_revision,
            reader.checkpoint,
            reader.load_world,
        ):
            with pytest.raises(ArchiveFormatError, match=_ERROR):
                operation()
            assert inventory(tmp_path) == before


def test_standalone_hardlinked_store_and_default_writer_remain_supported(
    tmp_path: Path,
) -> None:
    archive = create(tmp_path)
    os.link(archive.database_path, tmp_path / "hardlink.sqlite3")
    entry = JournalEntry(
        "candidate_aborted", {"base_revision": 0, "reason": "operator"}
    )
    with AttemptArchive.open(archive.ref) as writer:
        writer.append(entry)
    before = inventory(tmp_path)
    with AttemptArchive.open(archive.ref, read_only=True) as reader:
        assert reader.latest_revision == 0
        assert reader.checkpoint().revision == 0
        assert reader.load_world().tick == 0
        assert reader.entries() == (entry,)
    assert inventory(tmp_path) == before


def test_live_rollback_journal_allows_snapshot_and_subsequent_commit(
    tmp_path: Path,
) -> None:
    archive = create(tmp_path, catalog=True)
    archive.record((), lifecycle="paused", reason="operator")
    identity, path = archive.ref, archive.database_path
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE lifecycle SET reason='pending' WHERE sequence=1")
        assert path.with_name(path.name + "-journal").is_file()
        before = inventory(tmp_path)
        with AttemptArchive.open(identity, read_only=True) as reader:
            assert reader.checkpoint().revision == 0
            assert reader.load_world().tick == 0
            assert reader.lifecycle()[0]["reason"] != "pending"
        assert read_trace_page(identity).calls == ()
        assert inventory(tmp_path) == before
        connection.commit()
    finally:
        connection.close()
    assert not path.with_name(path.name + "-journal").exists()
    with AttemptArchive.open(identity, read_only=True) as reader:
        assert reader.lifecycle()[0]["reason"] == "pending"


@pytest.mark.parametrize("failure", ["stat", "open", "sidecar_stat"])
def test_unreadable_input_uses_fixed_guard_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    archive = create(tmp_path)
    path = archive.database_path
    before = inventory(tmp_path)
    target = path if failure != "sidecar_stat" else path.with_name(path.name + "-wal")
    method = "open" if failure == "open" else "lstat"
    original = getattr(Path, method)

    def unreadable(self: Path, *args: object, **kwargs: object) -> object:
        if self == target:
            raise PermissionError("private source path must not be disclosed")
        return original(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, method, unreadable)
        patch.setattr(sqlite3, "connect", forbidden_connect)
        with pytest.raises(ArchiveFormatError, match=_ERROR) as caught:
            if failure == "stat":
                # Isolate the helper from the store's existing _path validation.
                require_rollback_database(path)
            else:
                AttemptArchive.open(archive.ref, read_only=True)
        assert caught.value.__cause__ is None
    assert inventory(tmp_path) == before


def test_missing_directory_read_does_not_create_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = AttemptRef(uuid4().hex, uuid4().hex, tmp_path / "absent")
    before = inventory(tmp_path)
    monkeypatch.setattr(sqlite3, "connect", forbidden_connect)
    with pytest.raises(ArchiveFormatError, match=_ERROR):
        AttemptArchive.open(identity, read_only=True)
    assert inventory(tmp_path) == before
