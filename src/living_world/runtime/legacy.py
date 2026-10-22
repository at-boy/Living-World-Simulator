"""Same-thread archive observation for the established scenario runner."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import Self

from living_world.archives import (
    ArchiveError,
    ArchiveFormatError,
    AttemptArchive,
    AttemptConfig,
    AttemptLease,
    JournalEntry,
    RetainedInputs,
    RunCatalog,
    retain_inputs,
)
from living_world.repositories.world_snapshot import encode_world
from living_world.running import RunResult, StopReason
from living_world.scenarios.scenario import LoadedScenario
from living_world.simulation.simulation_engine import SimulationEngine


def legacy_cursor(engine: SimulationEngine) -> Mapping[str, object]:
    metadata = engine.state.run_metadata
    if metadata is None:
        raise ArchiveFormatError("Legacy world requires scenario identity.")
    engine.replay.validate_loaded_state()
    binding = engine.state.replay_binding
    replay = engine.state.replay_state
    if binding is not None and (
        binding.scenario_key != metadata.scenario_key
        or binding.scenario_fingerprint != metadata.configuration_fingerprint
    ):
        raise ArchiveFormatError("Legacy replay identity mismatch.")
    return {
        "format": 1,
        "mode": "legacy_recorded",
        "scenario_fingerprint": metadata.configuration_fingerprint,
        "next_tick": engine.state.tick,
        "tape_fingerprint": None if binding is None else binding.tape_fingerprint,
        "next_index": None if replay is None else replay.next_index,
    }


class LegacyArchiveSession:
    """Own one independent attempt while its original runner owns the world."""

    def __init__(self, catalog: RunCatalog, config: AttemptConfig) -> None:
        if config.mode != "recorded":
            raise ArchiveFormatError("Legacy session requires recorded mode.")
        self._catalog = catalog
        self._config = config
        self.ref = catalog.reserve(config)
        self._lease: AttemptLease | None = None
        self._archive: AttemptArchive | None = None
        self._last_revision: int | None = None
        self._settled = False
        self._finished_observed = False

    @property
    def archive(self) -> AttemptArchive:
        if self._archive is None:
            raise ArchiveError("Legacy session is not entered.")
        return self._archive

    @property
    def last_revision(self) -> int | None:
        return self._last_revision

    def __enter__(self) -> Self:
        if self._lease is not None or self._settled:
            raise ArchiveError("Legacy session cannot be reentered.")
        lease = AttemptLease(self.ref)
        lease.__enter__()
        self._lease = lease
        try:
            self._archive = self._catalog.open_attempt(
                self.ref.attempt_id, read_only=False
            )
        except BaseException:
            with suppress(BaseException):
                self.close()
            raise
        return self

    def retain(self, scenario_path: Path, *, tape_path: Path | None) -> RetainedInputs:
        _ = self.archive
        return retain_inputs(self.ref, scenario_path, tape_path=tape_path)

    def initialized(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
        metadata = engine.state.run_metadata
        if (
            metadata != scenario.run_metadata
            or metadata is None
            or (
                metadata.scenario_key != self._config.scenario_key
                or metadata.seed != self._config.seed
                or metadata.configuration_fingerprint
                != scenario.configuration_fingerprint
                or scenario.key != self._config.scenario_key
                or scenario.seed != self._config.seed
            )
        ):
            raise ArchiveFormatError("Legacy initialized identity mismatch.")
        self._commit(engine)

    def tick_completed(self, engine: SimulationEngine) -> None:
        self._commit(engine)

    def finished(self, engine: SimulationEngine, result: RunResult) -> None:
        self._commit(engine)
        self._finished_observed = True

    def _commit(self, engine: SimulationEngine) -> None:
        snapshot, cursor = encode_world(engine.state), legacy_cursor(engine)
        if self._last_revision is not None:
            previous = self.archive.checkpoint()
            if (
                previous.snapshot == snapshot
                and previous.driver_cursor == cursor
                and not previous.feedback_cursor
            ):
                return
        checkpoint = self.archive.commit(
            snapshot,
            expected_revision=self._last_revision,
            driver_cursor=cursor,
            feedback_cursor={},
            entries=(),
        )
        self._last_revision = checkpoint.revision

    def succeed(self, result: RunResult) -> None:
        stopped = (
            result.stop_reason == StopReason.OPERATOR_STOP
            or result.terminal_condition == "operator_stop"
        )
        self._settle(
            "stopped" if stopped else "completed",
            result.terminal_condition or result.stop_reason.value,
        )

    def fail(self, reason: str) -> None:
        if reason not in ("legacy_run_failed", "initialization_failed", "interrupted"):
            raise ArchiveFormatError("Unknown legacy failure reason.")
        self._settle("interrupted" if reason == "interrupted" else "failed", reason)

    def _settle(self, lifecycle: str, reason: str) -> None:
        if self._settled:
            return
        entries = []
        if (
            lifecycle in ("failed", "interrupted")
            and self._last_revision is not None
            and not self._finished_observed
        ):
            entries.append(
                JournalEntry(
                    "candidate_aborted",
                    {"base_revision": self._last_revision, "reason": reason},
                )
            )
        entries.append(
            JournalEntry(
                "attempt_finished",
                {
                    "lifecycle": lifecycle,
                    "outcome": reason,
                    "last_revision": self._last_revision,
                },
            )
        )
        self.archive.record(tuple(entries), lifecycle=lifecycle, reason=reason)
        self._settled = True

    def close(self) -> None:
        archive, self._archive = self._archive, None
        lease, self._lease = self._lease, None
        try:
            if archive is not None:
                archive.close()
        except BaseException:
            if lease is not None:
                with suppress(BaseException):
                    lease.release()
            raise
        else:
            if lease is not None:
                lease.release()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        failed = exc is not None
        try:
            if not self._settled:
                self.fail("legacy_run_failed" if failed else "interrupted")
        except BaseException:
            if not failed:
                failed = True
                raise
        finally:
            try:
                self.close()
            except BaseException:
                if not failed:
                    raise
