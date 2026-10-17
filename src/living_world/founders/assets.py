"""Portable private materialization of the five fixed package resources."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from .model import FoundersOutcome


@dataclass(frozen=True, slots=True)
class FoundersAssets:
    scenario: Path
    success: Path
    stall: Path
    failure: Path

    def tape_for(self, outcome: FoundersOutcome) -> Path:
        return {
            FoundersOutcome.SUCCESS: self.success,
            FoundersOutcome.STALL: self.stall,
            FoundersOutcome.FAILURE: self.failure,
        }[outcome]


@contextmanager
def materialize_founders_assets() -> Iterator[FoundersAssets]:
    with TemporaryDirectory(prefix="living-world-founders-") as temporary:
        root = Path(temporary)
        package = files("living_world.founders").joinpath("assets")
        for name in ("founders", "definitions", "success", "stall", "failure"):
            (root / (name + ".yaml")).write_bytes(
                package.joinpath(name + ".yaml").read_bytes()
            )
        yield FoundersAssets(
            root / "founders.yaml",
            root / "success.yaml",
            root / "stall.yaml",
            root / "failure.yaml",
        )
