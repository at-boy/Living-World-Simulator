"""Keep unit-test CLI archives inside each test's temporary directory."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
