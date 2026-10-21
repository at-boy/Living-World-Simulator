"""Standalone compatibility publication preserves authoritative archive history."""

import os
from pathlib import Path

import pytest
from test_run_archive_catalog import initialized

from living_world.archives.mirror import ArchiveMirrorError, write_checkpoint_mirror
from living_world.repositories.sqlite_repository import SQLiteRepository


def test_mirror_exact_checkpoint_closed_standalone_and_archive_unchanged(
    tmp_path: Path,
) -> None:
    catalog, ref, checkpoint = initialized(tmp_path)
    before = (ref.directory / "archive.sqlite3").read_bytes()
    target = tmp_path / "mirror ?#.db"
    write_checkpoint_mirror(checkpoint, target, attempt=ref)
    assert SQLiteRepository(str(target), read_only=True).load_world().tick == 0
    assert (ref.directory / "archive.sqlite3").read_bytes() == before
    assert catalog.open_attempt(ref.attempt_id).checkpoint() == checkpoint
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "kind",
    ["archive", "object", "symlink", "hardlink", "parent_symlink", "missing_parent"],
)
def test_mirror_rejects_unsafe_destinations(tmp_path: Path, kind: str) -> None:
    catalog, ref, checkpoint = initialized(tmp_path)
    target = tmp_path / "out.db"
    if kind == "archive":
        target = ref.directory / "archive.sqlite3"
    elif kind == "object":
        target = catalog.root / "objects" / "new"
    elif kind == "symlink":
        target.symlink_to(ref.directory / "archive.sqlite3")
    elif kind == "hardlink":
        os.link(ref.directory / "archive.sqlite3", target)
    elif kind == "parent_symlink":
        (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
        target = tmp_path / "link/out.db"
    else:
        target = tmp_path / "missing/out.db"
    before = (ref.directory / "archive.sqlite3").read_bytes()
    with pytest.raises(ArchiveMirrorError) as error:
        write_checkpoint_mirror(checkpoint, target, attempt=ref)
    assert error.value.attempt == ref and error.value.revision == 0
    assert error.value.destination == target
    assert (ref.directory / "archive.sqlite3").read_bytes() == before


def test_mirror_failure_after_commit_keeps_prior_destination(tmp_path: Path) -> None:
    catalog, ref, checkpoint = initialized(tmp_path)
    parent = tmp_path / "denied"
    parent.mkdir()
    target = parent / "mirror.db"
    target.write_bytes(b"previous")
    parent.chmod(320)
    try:
        with pytest.raises(ArchiveMirrorError):
            write_checkpoint_mirror(checkpoint, target, attempt=ref)
    finally:
        parent.chmod(448)
    assert target.read_bytes() == b"previous"
    assert catalog.open_attempt(ref.attempt_id).checkpoint() == checkpoint


def test_checkpoint_must_belong_to_source_attempt(tmp_path: Path) -> None:
    from living_world.archives import Checkpoint

    _catalog, ref, checkpoint = initialized(tmp_path)
    changed = Checkpoint(checkpoint.revision, checkpoint.snapshot, {"changed": 1}, {})
    with pytest.raises(ArchiveMirrorError):
        write_checkpoint_mirror(changed, tmp_path / "mirror.db", attempt=ref)


def test_pre_replace_fsync_failure_keeps_previous_mirror_and_no_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import living_world.archives.mirror as module

    catalog, ref, checkpoint = initialized(tmp_path)
    target = tmp_path / "mirror.db"
    target.write_bytes(b"previous")

    def fail(descriptor: int) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(module.os, "fsync", fail)
    with pytest.raises(ArchiveMirrorError) as error:
        write_checkpoint_mirror(checkpoint, target, attempt=ref)
    assert error.value.revision == 0
    assert target.read_bytes() == b"previous"
    assert catalog.open_attempt(ref.attempt_id).checkpoint() == checkpoint
    assert not list(tmp_path.glob(".checkpoint-*"))


def test_post_replace_failure_reports_archive_ahead_without_rollback_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import living_world.archives.mirror as module

    _, ref, checkpoint = initialized(tmp_path)
    target = tmp_path / "mirror.db"
    target.write_bytes(b"previous")

    def fail(path: Path) -> None:
        raise OSError("directory sync failed")

    monkeypatch.setattr(module, "fsync_directory", fail)
    with pytest.raises(ArchiveMirrorError):
        write_checkpoint_mirror(checkpoint, target, attempt=ref)
    assert SQLiteRepository(str(target), read_only=True).load_world().tick == 0
