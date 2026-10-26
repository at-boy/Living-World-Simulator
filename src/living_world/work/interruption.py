"""Engine-only typed requests/results for one atomic work execution phase."""

from dataclasses import dataclass
from typing import Literal


def _text(value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a nonempty work interruption identity.")


@dataclass(frozen=True, kw_only=True)
class WorkInterruptionRequest:
    settlement_id: str
    execution_tick: int

    def __post_init__(self) -> None:
        _text(self.settlement_id)
        if type(self.execution_tick) is not int or self.execution_tick < 0:
            raise ValueError("Expected a nonnegative exact execution tick.")


@dataclass(frozen=True, kw_only=True)
class WorkInterruptionResult:
    request: WorkInterruptionRequest
    outcome: Literal["applied", "no_eligible_work"]
    work_id: str | None
    event_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request, WorkInterruptionRequest):
            raise TypeError("Expected a work interruption request.")
        if type(self.event_references) is not tuple:
            raise TypeError("Expected ordered event reference tuple.")
        for ref in self.event_references:
            _text(ref)
        if len(set(self.event_references)) != len(self.event_references):
            raise ValueError("Duplicate interruption event reference.")
        if self.outcome == "applied":
            _text(self.work_id)
            if not self.event_references:
                raise ValueError("Applied interruption requires manager events.")
        elif (
            self.outcome != "no_eligible_work"
            or self.work_id is not None
            or self.event_references
        ):
            raise ValueError("Invalid work interruption outcome.")
