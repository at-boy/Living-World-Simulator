"""Bounded reservation-only catalog discovery, without world certification."""

import importlib
import json
import os
from uuid import uuid4

import pytest
from test_trace_analysis_reader import snapshot

from living_world.archives import ArchiveFormatError
from living_world.archives.catalog import RunCatalog


def api():
    return importlib.import_module("living_world.archives.trace_catalog")


def reservation(root, *, lineage=None, attempt=None):
    lineage, attempt = lineage or uuid4().hex, attempt or uuid4().hex
    directory = root / lineage / attempt
    directory.mkdir(parents=True)
    data = {
        "format": 1,
        "lineage_id": lineage,
        "attempt_id": attempt,
        "config": {
            "mode": "recorded",
            "scenario_key": "founders",
            "seed": 7,
            "software_revision": "revision",
            "settings": {},
        },
        "parent": None,
        "reserved_at": "2026-11-01T00:00:00+00:00",
        "reservation_error": "archive_initialization_failed",
    }
    (directory / "attempt.json").write_text(json.dumps(data))
    return directory


def test_missing_root_and_ordered_refresh_pages(tmp_path):
    module = api()
    root = tmp_path / "absent"
    catalog = RunCatalog(root)
    assert module.list_trace_attempts(catalog).attempts == ()
    assert not root.exists()
    directories = [reservation(root) for _ in range(3)]
    before = snapshot(root)
    expected = sorted((p.parent.name, p.name) for p in directories)
    page = module.list_trace_attempts(catalog, limit=1)
    assert [(p.lineage_id, p.attempt_id) for p in page.attempts] == expected[:1]
    assert page.next_after == expected[0]
    assert page.integrity == "reservation_metadata_checked"
    tail = module.list_trace_attempts(catalog, after=page.next_after)
    assert [(p.lineage_id, p.attempt_id) for p in tail.attempts] == expected[1:]
    assert tail.next_after is None
    assert page.attempts[0].metadata_state == "available"
    assert page.attempts[0].reservation_error == "archive_initialization_failed"
    assert not page.attempts[0].has_database
    assert snapshot(root) == before
    added = reservation(root)
    assert len(module.list_trace_attempts(catalog).attempts) == 4
    assert module.resolve_trace_attempt(catalog, added.name).directory == added


@pytest.mark.parametrize(
    "damage,state",
    [
        ("missing", "missing"),
        ("json", "invalid"),
        ("oversize", "invalid"),
        ("symlink", "invalid"),
        ("hardlink", "invalid"),
        ("db_symlink", "invalid"),
        ("identity", "invalid"),
    ],
)
def test_bad_metadata_is_one_row_not_catalog_failure(tmp_path, damage, state):
    module = api()
    directory = reservation(tmp_path)
    header = directory / "attempt.json"
    if damage == "missing":
        header.unlink()
    elif damage == "json":
        header.write_text("{broken")
    elif damage == "oversize":
        header.write_bytes(b" " * 2049)
    elif damage in {"symlink", "hardlink"}:
        target = tmp_path / "target"
        header.rename(target)
        if damage == "symlink":
            header.symlink_to(target)
        else:
            os.link(target, header)
    elif damage == "db_symlink":
        (directory / "archive.sqlite3").symlink_to(header)
    else:
        data = json.loads(header.read_text())
        data["attempt_id"] = uuid4().hex
        header.write_text(json.dumps(data))
    row = module.list_trace_attempts(
        RunCatalog(tmp_path), limits=module.TraceCatalogLimits(max_header_bytes=2048)
    ).attempts[0]
    assert row.metadata_state == state
    assert row.mode is row.parent is row.reserved_at is row.reservation_error is None
    assert not row.has_database


def test_unsafe_attempt_duplicate_resolution_and_budgets(tmp_path):
    module = api()
    directory = reservation(tmp_path)
    other = reservation(tmp_path, attempt=directory.name)
    catalog = RunCatalog(tmp_path)
    with pytest.raises(ArchiveFormatError):
        module.resolve_trace_attempt(catalog, directory.name)
    (other / "attempt.json").unlink()
    other.rmdir()
    other.symlink_to(directory, target_is_directory=True)
    rows = module.list_trace_attempts(catalog).attempts
    assert sorted(row.metadata_state for row in rows) == ["available", "invalid"]
    with pytest.raises(ArchiveFormatError):
        module.resolve_trace_attempt(catalog, "../unsafe")
    for index in range(5):
        (tmp_path / f"ignored-{index}").touch()
    with pytest.raises(module.TraceAnalysisLimitError):
        module.list_trace_attempts(
            catalog, limits=module.TraceCatalogLimits(max_entries=2)
        )
    with pytest.raises(module.TraceAnalysisLimitError):
        module.resolve_trace_attempt(
            catalog, directory.name, limits=module.TraceCatalogLimits(max_entries=2)
        )


@pytest.mark.parametrize("value", [True, 0, -1, 101, 1.0])
def test_invalid_page_limits(tmp_path, value):
    with pytest.raises(ArchiveFormatError):
        api().list_trace_attempts(RunCatalog(tmp_path), limit=value)


@pytest.mark.parametrize(
    "value", [True, [], ("bad", "bad"), [uuid4().hex, uuid4().hex], (uuid4().hex,)]
)
def test_invalid_cursors(tmp_path, value):
    with pytest.raises(ArchiveFormatError):
        api().list_trace_attempts(RunCatalog(tmp_path), after=value)


def test_shallow_count_header_selection_and_resolver_no_reads(tmp_path, monkeypatch):
    from pathlib import Path

    module = api()
    directories = sorted([reservation(tmp_path) for _ in range(2)])
    for index in range(10):
        (directories[0] / f"ignored-child-{index}").touch()
    (tmp_path / "ignored").touch()
    catalog = RunCatalog(tmp_path)
    # Two lineages, two attempts, one ignored root name: exactly five entries.
    assert (
        len(
            module.list_trace_attempts(
                catalog, limits=module.TraceCatalogLimits(max_entries=5)
            ).attempts
        )
        == 2
    )
    with pytest.raises(module.TraceAnalysisLimitError):
        module.list_trace_attempts(
            catalog, limits=module.TraceCatalogLimits(max_entries=4)
        )
    original = Path.open

    def guarded(path, *args, **kwargs):
        if path == directories[1] / "attempt.json":
            raise AssertionError("read metadata outside requested page")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    assert len(module.list_trace_attempts(catalog, limit=1).attempts) == 1
    assert (
        module.resolve_trace_attempt(catalog, directories[1].name).directory
        == directories[1]
    )


@pytest.mark.parametrize("value", [True, 0, -1, 1.0, None])
def test_catalog_budgets_require_exact_positive_integers(value):
    for name in ("max_entries", "max_header_bytes"):
        with pytest.raises(ArchiveFormatError):
            api().TraceCatalogLimits(**{name: value})


@pytest.mark.parametrize("field", ["scenario_key", "reserved_at"])
def test_unencodable_projected_reservation_text_is_invalid_row(tmp_path, field):
    broken = reservation(tmp_path)
    valid = reservation(tmp_path)
    for directory, scenario in ((broken, "\ud800"), (valid, "København 日本語 🦉")):
        header = directory / "attempt.json"
        data = json.loads(header.read_text())
        data["config"]["scenario_key"] = "København 日本語 🦉"
        data["reserved_at"] = "2026-11-01🦉00:00:00+00:00"
        if field == "scenario_key":
            data["config"][field] = scenario
        elif directory == broken:
            data[field] = "2026-11-01\ud80000:00:00+00:00"
        header.write_text(json.dumps(data))
    assert b"\\ud800" in (broken / "attempt.json").read_bytes()
    before = snapshot(tmp_path)
    rows = {
        row.attempt_id: row
        for row in api().list_trace_attempts(RunCatalog(tmp_path)).attempts
    }
    assert rows[broken.name].metadata_state == "invalid"
    assert all(
        getattr(rows[broken.name], field) is None
        for field in (
            "mode",
            "scenario_key",
            "reserved_at",
            "parent",
            "reservation_error",
        )
    )
    assert rows[valid.name].metadata_state == "available"
    assert rows[valid.name].scenario_key == "København 日本語 🦉"
    assert rows[valid.name].reserved_at == "2026-11-01🦉00:00:00+00:00"
    assert snapshot(tmp_path) == before
