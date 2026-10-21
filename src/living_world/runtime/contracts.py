"""Engine-only runtime protocol and immutable operational records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Protocol

from living_world.archives import AttemptArchive, AttemptRef, Checkpoint, JournalEntry
from living_world.archives.model import frozen_map, integer
from living_world.repositories.world_snapshot import WorldSnapshot
from living_world.simulation.simulation_engine import SimulationEngine


class RuntimeState(str, Enum):
    INITIALIZING = "initializing"
    PAUSED = "paused"
    RUNNING = "running"
    AWAITING_MODEL = "awaiting_model"
    PAUSE_REQUESTED = "pause_requested"
    PROVIDER_ERROR_PAUSED = "provider_error_paused"
    STEPPING = "stepping"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

    @property
    def terminal(self) -> bool:
        return self in (self.COMPLETED, self.STOPPED, self.FAILED, self.INTERRUPTED)


def _short(value: str | None) -> None:
    if value is not None and (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 128
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("Expected a short operational string.")


@dataclass(frozen=True)
class RuntimeStatus:
    attempt: AttemptRef
    state: RuntimeState
    state_version: int
    revision: int | None
    tick: int | None
    activity: str | None
    error_code: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, AttemptRef) or not isinstance(
            self.state, RuntimeState
        ):
            raise TypeError("Expected runtime state and attempt reference.")
        integer(self.state_version)
        if (self.revision is None) != (self.tick is None):
            raise ValueError("Checkpoint revision and tick must be present together.")
        if self.revision is not None:
            integer(self.revision)
            integer(self.tick)
        _short(self.activity)
        _short(self.error_code)


@dataclass(frozen=True)
class DriverCommit:
    driver_cursor: Mapping[str, object]
    feedback_cursor: Mapping[str, object]
    journal_entries: tuple[JournalEntry, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "driver_cursor", frozen_map(self.driver_cursor))
        object.__setattr__(self, "feedback_cursor", frozen_map(self.feedback_cursor))
        if type(self.journal_entries) is not tuple or any(
            not isinstance(e, JournalEntry) for e in self.journal_entries
        ):
            raise TypeError("Expected tuple of journal entries.")


class ScenarioComposition(Protocol):
    def initialize(self) -> SimulationEngine: ...
    def restore(self, snapshot: WorldSnapshot) -> SimulationEngine: ...
    def terminal_condition(self, engine: SimulationEngine) -> str | None: ...
    def finalize(self, engine: SimulationEngine, *, stopped: bool) -> None: ...


class TickPreparation(Protocol):
    @property
    def activity(self) -> str | None: ...
    @property
    def error_code(self) -> str | None: ...
    def poll(self) -> Literal["waiting", "ready", "provider_error", "paused"]: ...
    def request_pause(self) -> None: ...
    def install(self) -> None: ...
    def finish_tick(self) -> DriverCommit: ...
    def close(self) -> None: ...


class TickDriver(Protocol):
    def initialize(
        self, candidate: SimulationEngine, archive: AttemptArchive
    ) -> DriverCommit: ...
    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> TickPreparation: ...
