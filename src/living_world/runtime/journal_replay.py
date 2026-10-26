"""Captured, exact complete-tick replay with no inference or network path."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Literal
from uuid import uuid4

from living_world.archives import (
    ArchiveFormatError,
    AttemptArchive,
    AttemptConfig,
    Checkpoint,
    ForkPoint,
    JournalEntry,
    load_retained_inputs,
)
from living_world.archives.model import canonical
from living_world.cognition.local_llm_cognition_format import (
    parse_decision_response,
    serialize_decision_request,
)
from living_world.repositories.world_snapshot import (
    WorldSnapshot,
    decode_world,
    encode_world,
)
from living_world.simulation.simulation_engine import SimulationEngine

from .broker import client_for, decision_document, encoded_body, provider_config
from .contracts import DriverCommit
from .disturbances import (
    PreparedBoundaryDisturbance,
    apply_boundary_disturbance,
    prepare_boundary_disturbance,
)
from .feedback import FoundersFeedback
from .founders import FoundersLiveComposition
from .ollama_driver import (
    _cursor,
    _hash,
    _ProposalSystem,
    _same_checkpoint,
    _Staged,
    _validated,
    effective_config_fingerprint,
)


class _CapturedSource:
    def __init__(
        self, source: AttemptArchive, source_point: ForkPoint | None = None
    ) -> None:
        # Read-only reopening also checks metadata/format independently of caller.
        with AttemptArchive.open(source.ref, read_only=True) as archive:
            self.config = archive.config
            self.provider = provider_config(archive.config)
            self.fingerprint = effective_config_fingerprint(archive.config)
            point = archive.fork_point() if source_point is None else source_point
            if (
                not isinstance(point, ForkPoint)
                or archive.checkpoint(point.checkpoint.revision) != point.checkpoint
                or archive.journal_boundary(
                    through_sequence=point.journal_boundary.sequence
                )
                != point.journal_boundary
            ):
                raise ArchiveFormatError("Replay source point mismatch.")
            self.point = point
            self.boundary = point.journal_boundary
            self.checkpoints = tuple(
                archive.checkpoint(i) for i in range(point.checkpoint.revision + 1)
            )
            self.records = archive.journal_records(
                through_sequence=self.boundary.sequence
            )
            self.ref = archive.ref
            self.hashes = load_retained_inputs(archive.ref).hashes
        if any(
            r.entry.kind == "boundary_disturbance"
            and r.checkpoint_revision in (None, 0)
            for r in self.records
        ):
            raise ArchiveFormatError(
                "Uncommitted or initial source boundary disturbance is invalid."
            )
        for previous, current in zip(self.checkpoints, self.checkpoints[1:]):
            a, b = (
                decode_world(previous.snapshot).tick,
                decode_world(current.snapshot).tick,
            )
            rows = [
                r
                for r in self.records
                if r.checkpoint_revision == current.revision
                and r.entry.kind in ("action_resolved", "boundary_disturbance")
            ]
            if b == a:
                if not _same_checkpoint(previous, current) or rows:
                    raise ArchiveFormatError("Divergent same-tick source checkpoint.")
            elif b != a + 1:
                raise ArchiveFormatError("Source skipped a complete tick.")


class JournalReplayComposition:
    def __init__(
        self,
        source: AttemptArchive,
        composition: FoundersLiveComposition,
        *,
        source_point: ForkPoint | None = None,
    ) -> None:
        self._source = _CapturedSource(source, source_point)
        self._composition = composition
        self._last_tick = decode_world(self._source.checkpoints[-1].snapshot).tick

    @property
    def source_point(self) -> ForkPoint:
        return self._source.point

    def initialize(self) -> SimulationEngine:
        return self._composition.restore(self._source.checkpoints[0].snapshot)

    def restore(self, snapshot: WorldSnapshot) -> SimulationEngine:
        return self._composition.restore(snapshot)

    def terminal_condition(self, engine: SimulationEngine) -> str | None:
        actual = self._composition.terminal_condition(engine)
        return actual or (
            "journal_replay_complete" if engine.state.tick == self._last_tick else None
        )

    def finalize(self, engine: SimulationEngine, *, stopped: bool) -> None:
        self._composition.finalize(engine, stopped=stopped)


class JournalReplayDriver:
    def __init__(
        self,
        source: AttemptArchive,
        feedback: FoundersFeedback,
        *,
        source_point: ForkPoint | None = None,
    ) -> None:
        self._source = _CapturedSource(source, source_point)
        self._feedback = feedback

    def _target(self, archive: AttemptArchive) -> None:
        config = archive.config
        if (
            config.mode != "journal_replay"
            or config.scenario_key != self._source.config.scenario_key
            or config.seed != self._source.config.seed
            or config.settings.get("source_config_fingerprint")
            != self._source.fingerprint
            or load_retained_inputs(archive.ref).hashes != self._source.hashes
        ):
            raise ArchiveFormatError("Replay source configuration or inputs mismatch.")

    def initialize(
        self, candidate: SimulationEngine, archive: AttemptArchive
    ) -> DriverCommit:
        self._target(archive)
        first = self._source.checkpoints[0]
        if encode_world(candidate.state) != first.snapshot:
            raise ArchiveFormatError("Replay initial world mismatch.")
        return DriverCommit(first.driver_cursor, first.feedback_cursor, ())

    def validate_checkpoint(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> None:
        self._target(archive)
        if encode_world(candidate.state) != base.snapshot or not any(
            _same_checkpoint(point, base) for point in self._source.checkpoints
        ):
            raise ArchiveFormatError("Replay candidate or cursor mismatch.")
        self._feedback.validate_checkpoint(candidate, base)

    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> _ReplayPreparation:
        self.validate_checkpoint(candidate, base, archive)
        selected: tuple[Checkpoint, Checkpoint] | None = None
        for previous, current in zip(
            self._source.checkpoints, self._source.checkpoints[1:]
        ):
            if (
                _same_checkpoint(previous, base)
                and decode_world(current.snapshot).tick
                == decode_world(previous.snapshot).tick + 1
            ):
                selected = previous, current
                break
        if selected is None:
            raise ArchiveFormatError("No matching advancing source checkpoint.")
        previous, target = selected
        items = self._feedback.prepare(candidate, base)
        action_rows = [
            r.entry
            for r in self._source.records
            if r.checkpoint_revision == target.revision
            and r.entry.kind == "action_resolved"
        ]
        if len(action_rows) != len(items) or {
            e.payload["actor_label"] for e in action_rows
        } != {item.actor_label for item in items}:
            raise ArchiveFormatError("Incomplete source action slots.")
        requests = {
            r.entry.payload["request_id"]: r.entry
            for r in self._source.records
            if r.entry.kind in ("request_started", "response_reused")
        }
        responses = {
            r.entry.payload["request_id"]: r.entry
            for r in self._source.records
            if r.entry.kind in ("response_validated", "response_reused")
        }
        staged = []
        imports = []
        client = client_for(self._source.provider)
        for item in items:
            action = next(
                entry
                for entry in action_rows
                if entry.payload["actor_label"] == item.actor_label
            )
            request_id = action.payload["request_id"]
            started = requests.get(request_id)
            response = responses.get(request_id)
            payload = client.build_payload(item.context, item.options)
            request = {
                "base_revision": base.revision,
                "source_tick": candidate.state.tick,
                "actor_label": item.actor_label,
                "input_fingerprint": _hash(
                    {"feedback_input": item.input_fingerprint, "payload": payload}
                ),
                "config_fingerprint": self._source.fingerprint,
                "request": json.loads(
                    serialize_decision_request(item.context, item.options)
                ),
            }
            if (
                len(encoded_body(payload)) > 16000
                or started is None
                or response is None
                or started.payload["base_revision"] != previous.revision
                or any(
                    canonical(started.payload[k]) != canonical(request[k])
                    for k in request
                    if k != "base_revision"
                )
            ):
                raise ArchiveFormatError("Source request or response mismatch.")
            decision = _validated(
                candidate,
                item,
                parse_decision_response(
                    canonical(response.payload["decision"]), item.options
                ),
            )
            local = next(
                (
                    r.entry
                    for r in archive.journal_records()
                    if r.entry.kind == "response_reused"
                    and all(
                        canonical(r.entry.payload[k]) == canonical(v)
                        for k, v in request.items()
                    )
                    and canonical(r.entry.payload["decision"])
                    == canonical(response.payload["decision"])
                    and r.entry.payload["source"]["attempt_id"]
                    == self._source.ref.attempt_id
                    and r.entry.payload["source"]["request_id"] == request_id
                    and canonical(r.entry.payload["source"]["boundary"])
                    == canonical(asdict(self._source.boundary))
                ),
                None,
            )
            local_id = local.payload["request_id"] if local else uuid4().hex
            if local is None:
                imports.append(
                    JournalEntry(
                        "response_reused",
                        {
                            **request,
                            "request_id": local_id,
                            "decision": decision_document(decision),
                            "source": {
                                "attempt_id": self._source.ref.attempt_id,
                                "request_id": request_id,
                                "boundary": asdict(self._source.boundary),
                            },
                        },
                    )
                )
            staged.append(_Staged(item, local_id, decision))
        if imports:
            archive.record(tuple(imports))
        return _ReplayPreparation(
            candidate,
            base,
            archive,
            tuple(staged),
            target,
            tuple(action_rows),
            self._feedback,
            self._source.fingerprint,
            self._source.config,
            previous.revision,
            tuple(
                r.entry
                for r in self._source.records
                if r.checkpoint_revision == target.revision
                and r.entry.kind == "boundary_disturbance"
            ),
        )


class _ReplayPreparation:
    activity = None
    error_code = None

    def __init__(
        self,
        candidate: SimulationEngine,
        base: Checkpoint,
        archive: AttemptArchive,
        staged: tuple[_Staged, ...],
        target: Checkpoint,
        expected: tuple[JournalEntry, ...],
        feedback: FoundersFeedback,
        fingerprint: str,
        source_config: AttemptConfig,
        source_base_revision: int,
        expected_boundary: tuple[JournalEntry, ...],
    ) -> None:
        self._candidate, self._base, self._archive = candidate, base, archive
        self._target, self._expected, self._feedback = target, expected, feedback
        self._fingerprint = fingerprint
        self._source_config = source_config
        self._source_base_revision = source_base_revision
        self._expected_boundary = expected_boundary
        self._system = _ProposalSystem(candidate, base, staged)
        self._paused, self._closed = False, False
        self._boundary: PreparedBoundaryDisturbance | None = None

    def poll(self) -> Literal["paused", "ready"]:
        if self._closed:
            raise RuntimeError("Preparation closed.")
        return "paused" if self._paused else "ready"

    def request_pause(self) -> None:
        self._paused = True

    def install(self) -> None:
        if self._paused or self._closed:
            raise ArchiveFormatError("Replay preparation unavailable.")
        self._candidate.configure_proposal_system(self._system)
        self._boundary = prepare_boundary_disturbance(
            self._candidate, self._source_config
        )

    def finish_tick(self) -> DriverCommit:
        outcomes = self._system.outcomes
        if outcomes is None:
            raise ArchiveFormatError("Replay complete world diverged.")
        boundary = apply_boundary_disturbance(
            self._candidate,
            self._source_config,
            base_revision=self._base.revision,
            prepared=self._boundary,
        )
        if len(boundary) != len(self._expected_boundary):
            raise ArchiveFormatError("Replay boundary disturbance count diverged.")
        for actual, expected in zip(boundary, self._expected_boundary):
            if expected.payload["base_revision"] != self._source_base_revision or any(
                canonical(actual.payload[k]) != canonical(expected.payload[k])
                for k in actual.payload
                if k != "base_revision"
            ):
                raise ArchiveFormatError("Replay boundary disturbance diverged.")
        if encode_world(self._candidate.state) != self._target.snapshot:
            raise ArchiveFormatError("Replay complete world diverged.")
        for actual, expected in zip(outcomes, self._expected):
            if any(
                canonical(actual.payload[k]) != canonical(expected.payload[k])
                for k in ("source_tick", "actor_label", "outcome", "event_references")
            ):
                raise ArchiveFormatError("Replay gateway outcomes diverged.")
        feedback = self._feedback.after_tick(self._candidate, outcomes)
        if canonical(feedback) != canonical(self._target.feedback_cursor):
            raise ArchiveFormatError("Replay feedback cursor diverged.")
        metadata = self._candidate.state.run_metadata
        if metadata is None:
            raise ArchiveFormatError("Replay binding missing.")
        cursor = _cursor(
            self._candidate, self._fingerprint, metadata.configuration_fingerprint
        )
        if canonical(cursor) != canonical(self._target.driver_cursor):
            raise ArchiveFormatError("Replay semantic cursor diverged.")
        return DriverCommit(cursor, feedback, outcomes + boundary)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._candidate.configure_work_interruption(None)
        self._boundary = None
        self._candidate.configure_proposal_system(None)
        latest = self._archive.checkpoint()
        if (
            latest.revision <= self._base.revision
            or latest.snapshot != self._target.snapshot
        ):
            self._archive.append(
                JournalEntry(
                    "candidate_aborted",
                    {
                        "base_revision": self._base.revision,
                        "reason": "preparation_discarded",
                    },
                )
            )
