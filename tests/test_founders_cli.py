from pathlib import Path

import pytest

from living_world.cli import main


def test_founders_failure_alias_and_read_only_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from living_world import cli

    database = tmp_path / "failure.sqlite3"
    assert main(["run", "--founders", "failure", "--database", str(database)]) == 0
    before = database.read_bytes()
    captured: list[tuple[int, int]] = []
    monkeypatch.setattr(
        cli,
        "_serve_inspection",
        lambda engine, port: captured.append((engine.state.tick, port)),
    )
    assert (
        main(["inspect", "--founders", "--database", str(database), "--port", "8123"])
        == 0
    )
    assert captured == [(13, 8123)]
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "selectors",
    [
        ["scenario.yaml", "--founders", "success"],
        ["--founders", "stall", "--proposal-tape", "other.yaml"],
        [],
    ],
)
def test_alias_selector_conflicts_reject_before_database(
    tmp_path: Path, selectors: list[str]
) -> None:
    database = tmp_path / "absent.sqlite3"
    with pytest.raises(SystemExit):
        main(["run", *selectors, "--database", str(database)])
    assert not database.exists()


@pytest.mark.parametrize("selectors", [[], ["other.yaml", "--founders"]])
def test_inspect_selector_conflicts_do_not_create_database(
    tmp_path: Path, selectors: list[str]
) -> None:
    database = tmp_path / "absent.sqlite3"
    with pytest.raises(SystemExit):
        main(["inspect", *selectors, "--database", str(database)])
    assert not database.exists()


@pytest.mark.parametrize("port", ["0", "65536", "not-a-port"])
def test_inspect_invalid_port_rejects_before_database(
    tmp_path: Path, port: str
) -> None:
    database = tmp_path / "absent.sqlite3"
    with pytest.raises(SystemExit):
        main(["inspect", "--founders", "--port", port, "--database", str(database)])
    assert not database.exists()


def test_explicit_canonical_path_requires_tape_before_database(tmp_path: Path) -> None:
    from living_world.founders import materialize_founders_assets

    database = tmp_path / "absent.sqlite3"
    with materialize_founders_assets() as assets:
        assert main(["run", str(assets.scenario), "--database", str(database)]) == 2
    assert not database.exists()


def test_inspection_missing_optional_server_is_actionable_without_save_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import sys

    database = tmp_path / "world.sqlite3"
    assert main(["run", "--founders", "failure", "--database", str(database)]) == 0
    before = database.read_bytes()
    monkeypatch.setitem(sys.modules, "uvicorn", None)
    assert main(["inspect", "--founders", "--database", str(database)]) == 2
    assert "Install living-world-simulator[server]" in capsys.readouterr().err
    assert database.read_bytes() == before
