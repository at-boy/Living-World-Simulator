"""Filtered external inference, durable recovery and ordinary proposal gateways."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Literal, cast
from uuid import uuid4

from living_world.api.inspection import EngineWorldInspector
from living_world.archives import (
    ArchiveFormatError,
    AttemptArchive,
    AttemptConfig,
    Checkpoint,
    JournalBoundary,
    JournalEntry,
    JournalRecord,
    RunCatalog,
    load_retained_inputs,
)
from living_world.archives.model import canonical
from living_world.cognition.action_resolution import NPCActionResolver
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.local_llm_cognition_format import (
    parse_decision_response,
    serialize_decision_request,
)
from living_world.cognition.npc_cognition_client import ActionOption, NPCDecision
from living_world.cognition.npc_context import NPCContext
from living_world.founders.model import canonical_policy
from living_world.founders.runtime import FoundersLiveOfferProvider
from living_world.founders.setup import FoundersSetupManager
from living_world.repositories.world_snapshot import decode_world, encode_world
from living_world.scenarios.scenario import YAMLScenarioLoader
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState

from .archive_inference import (
    acknowledge_recorded,
    capture_trace_blobs,
    observation_for_result,
    record_request,
    record_response,
    trace_fields,
)
from .broker import (
    BrokerResult,
    DecisionBroker,
    ProviderConfig,
    client_for,
    decision_document,
    encoded_body,
    provider_config,
    provider_document,
)
from .contracts import DriverCommit
from .disturbances import (
    PreparedBoundaryDisturbance,
    apply_boundary_disturbance,
    prepare_boundary_disturbance,
)
from .feedback import DecisionInput, FoundersFeedback, _inside
from .inference_trace import (
    PreparedInference,
    empty_response_trace,
    prepare_inference,
    utc_now,
)


def _hash(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def effective_config_fingerprint(config: AttemptConfig) -> str:
    return _hash(
        {
            "format": 1,
            "scenario_key": config.scenario_key,
            "seed": config.seed,
            "software_revision": config.software_revision,
            "provider": provider_document(provider_config(config)),
            **(
                {"boundary_disturbance": config.settings["boundary_disturbance"]}
                if "boundary_disturbance" in config.settings
                else {}
            ),
            "feedback": {
                "max_perceptions": 8,
                "max_memories": 8,
                "max_request_characters": 16000,
            },
        }
    )


def _binding(candidate: SimulationEngine, archive: AttemptArchive) -> str:
    inputs = load_retained_inputs(archive.ref)
    scenario = YAMLScenarioLoader().load(inputs.scenario_path)
    metadata = candidate.state.run_metadata
    if (
        metadata is None
        or metadata != scenario.run_metadata
        or scenario.key != archive.config.scenario_key
        or scenario.seed != archive.config.seed
    ):
        raise ArchiveFormatError("Live scenario binding mismatch.")
    FoundersSetupManager(candidate.state, candidate.definitions).validate_live(
        canonical_policy()
    )
    return metadata.configuration_fingerprint


def _cursor(
    candidate: SimulationEngine, fingerprint: str, binding: str
) -> dict[str, object]:
    return {
        "format": 1,
        "mode": "live",
        "schedule_labels": sorted(canonical_policy().founder_labels),
        "binding_fingerprint": binding,
        "config_fingerprint": fingerprint,
        "next_tick": candidate.state.tick,
        "next_slot": 0,
    }


def _same_checkpoint(a: Checkpoint, b: Checkpoint) -> bool:
    return (
        a.snapshot == b.snapshot
        and canonical(a.driver_cursor) == canonical(b.driver_cursor)
        and canonical(a.feedback_cursor) == canonical(b.feedback_cursor)
    )


def _parent(
    archive: AttemptArchive, base: Checkpoint, seen: set[str]
) -> tuple[AttemptArchive, Checkpoint, JournalBoundary] | None:
    if archive.parent is None:
        return None
    parent_id, revision = archive.parent
    if parent_id in seen:
        raise ArchiveFormatError("Parent cycle.")
    seal = archive.parent_journal_boundary
    if seal is None:
        return None
    catalog = RunCatalog(archive.ref.directory.parent.parent)
    parent = catalog.open_attempt(parent_id)
    try:
        selected = parent.checkpoint(revision)
        if (
            not _same_checkpoint(archive.checkpoint(0), selected)
            or parent.journal_boundary(through_sequence=seal.sequence) != seal
        ):
            raise ArchiveFormatError("Parent continuity or seal mismatch.")
    except BaseException:
        parent.close()
        raise
    if not _same_checkpoint(base, archive.checkpoint(0)):
        parent.close()
        return None
    seen.add(parent_id)
    return parent, selected, seal


class _PreparedClient:
    provider_name = "prepared"

    def __init__(self, decision: NPCDecision) -> None:
        self.decision = decision

    def decide(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> NPCDecision:
        return self.decision


def _validated(
    candidate: SimulationEngine, item: DecisionInput, decision: NPCDecision
) -> NPCDecision:
    decision = DecisionEngine(_PreparedClient(decision)).decide(
        item.context, item.options
    )
    boundary = NPCInformationBoundary(candidate.state)
    prose: list[str] = []
    if decision.spoken_text is not None:
        prose.append(decision.spoken_text)
    request = decision.action_request
    if request is not None:
        prose.extend((request.action_key, request.rationale))
        if request.target_label is not None:
            prose.append(request.target_label)
        prose.extend(request.arguments.keys())
        prose.extend(request.arguments.values())
    for value in prose:
        boundary.validate_conversation_prose(value)
    return decision


@dataclass(frozen=True)
class _Staged:
    item: DecisionInput
    request_id: str
    decision: NPCDecision


class _ProposalSystem:
    def __init__(
        self, candidate: SimulationEngine, base: Checkpoint, staged: tuple[_Staged, ...]
    ) -> None:
        self.candidate, self.base, self.staged = candidate, base, staged
        self.outcomes: tuple[JournalEntry, ...] | None = None

    def step(self, state: WorldState) -> None:
        if (
            state is not self.candidate.state
            or state.tick != decode_world(self.base.snapshot).tick
            or self.outcomes is not None
        ):
            raise ArchiveFormatError("Invalid proposal phase.")
        results = []
        policy = canonical_policy()
        for staged in self.staged:
            item = staged.item
            decision = _validated(self.candidate, item, staged.decision)
            before = frozenset(state.events)
            outcome = "no_action"
            if decision.action_request is not None:
                FoundersSetupManager(state, self.candidate.definitions).validate_live(
                    policy
                )
                actor = state.entities.get(item.actor_id)
                eligible = (
                    actor is not None
                    and actor.destroyed_tick is None
                    and _inside(
                        self.candidate,
                        item.actor_id,
                        state.scenario_entity_bindings["camp"],
                    )
                )
                offers = (
                    FoundersLiveOfferProvider(self.candidate, policy).offers(
                        actor_id=item.actor_id,
                        inspector=EngineWorldInspector(self.candidate),
                    )
                    if eligible
                    else None
                )
                resolution = self.candidate.resolve_npc_action(
                    resolver=NPCActionResolver(
                        offers.options if offers else (),
                        offers.handlers if offers else (),
                    ),
                    actor_id=item.actor_id,
                    request=decision.action_request,
                )
                outcome = "accepted" if resolution.accepted else "rejected"
            results.append(
                JournalEntry(
                    "action_resolved",
                    {
                        "base_revision": self.base.revision,
                        "source_tick": decode_world(self.base.snapshot).tick,
                        "actor_label": item.actor_label,
                        "request_id": staged.request_id,
                        "outcome": outcome,
                        "event_references": [
                            key for key in state.events if key not in before
                        ],
                    },
                )
            )
        self.outcomes = tuple(results)


class OllamaTickDriver:
    def __init__(
        self, config: ProviderConfig, feedback: FoundersFeedback, broker: DecisionBroker
    ) -> None:
        self.config, self.feedback, self.broker = config, feedback, broker
        self._retry: set[tuple[str, int, str]] = set()

    def initialize(
        self, candidate: SimulationEngine, archive: AttemptArchive
    ) -> DriverCommit:
        if self.config != provider_config(archive.config):
            raise ArchiveFormatError("Provider configuration mismatch.")
        binding = _binding(candidate, archive)
        return DriverCommit(
            _cursor(candidate, effective_config_fingerprint(archive.config), binding),
            self.feedback.initialize(candidate),
            (),
        )

    def validate_checkpoint(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> None:
        if archive.checkpoint(base.revision) != base:
            raise ArchiveFormatError("Unknown complete checkpoint.")
        if self.config != provider_config(archive.config):
            raise ArchiveFormatError("Provider configuration mismatch.")
        binding = _binding(candidate, archive)
        fingerprint = effective_config_fingerprint(archive.config)
        expected = _cursor(candidate, fingerprint, binding)
        if canonical(base.driver_cursor) != canonical(expected):
            changed = dict(expected)
            changed["config_fingerprint"] = base.driver_cursor.get("config_fingerprint")
            if base.revision != 0 or canonical(base.driver_cursor) != canonical(
                changed
            ):
                raise ArchiveFormatError("Live cursor mismatch.")
            parent = _parent(archive, base, {archive.ref.attempt_id})
            if parent is None:
                raise ArchiveFormatError("Config changes require sealed fork.")
            parent[0].close()
        if encode_world(candidate.state) != base.snapshot:
            raise ArchiveFormatError("Candidate world mismatch.")
        if archive.parent is not None:
            linked = _parent(archive, base, {archive.ref.attempt_id})
            if linked is not None:
                linked[0].close()
        self.feedback.validate_checkpoint(candidate, base)

    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint, archive: AttemptArchive
    ) -> _LivePreparation:
        if archive.format_version != 2:
            raise ArchiveFormatError(
                "Exact inference traces require archive format two; resume into a new attempt."
            )
        if archive.checkpoint() != base:
            raise ArchiveFormatError("Stale complete checkpoint.")
        self.validate_checkpoint(candidate, base, archive)
        fingerprint = effective_config_fingerprint(archive.config)
        binding = _binding(candidate, archive)
        items = self.feedback.prepare(candidate, base)
        client = client_for(self.config)
        for item in items:
            if (
                len(encoded_body(client.build_payload(item.context, item.options)))
                > 16000
            ):
                raise ArchiveFormatError("Complete request exceeds budget.")
        return _LivePreparation(
            self, candidate, base, archive, items, fingerprint, binding
        )


class _LivePreparation:
    activity: str | None = None
    error_code: str | None = None

    def __init__(
        self,
        driver: OllamaTickDriver,
        candidate: SimulationEngine,
        base: Checkpoint,
        archive: AttemptArchive,
        items: tuple[DecisionInput, ...],
        fingerprint: str,
        binding: str,
    ) -> None:
        self.driver, self.candidate, self.base, self.archive = (
            driver,
            candidate,
            base,
            archive,
        )
        self.items, self.fingerprint, self.binding = items, fingerprint, binding
        self.staged: list[_Staged] = []
        self.active: (
            tuple[
                DecisionInput, str, Mapping[str, object], PreparedInference, str, float
            ]
            | None
        ) = None
        self.paused, self.closed = False, False
        self.system: _ProposalSystem | None = None
        self._aborted = False
        self._boundary: PreparedBoundaryDisturbance | None = None

    def _request(
        self, item: DecisionInput, prepared: PreparedInference | None = None
    ) -> dict[str, object]:
        prepared = prepared or prepare_inference(
            self.driver.config, item.context, item.options
        )
        payload = json.loads(prepared.body)
        return {
            "base_revision": self.base.revision,
            "source_tick": decode_world(self.base.snapshot).tick,
            "actor_label": item.actor_label,
            "input_fingerprint": _hash(
                {"feedback_input": item.input_fingerprint, "payload": payload}
            ),
            "config_fingerprint": self.fingerprint,
            "request": json.loads(
                serialize_decision_request(item.context, item.options)
            ),
        }

    def _retry_key(self, request: Mapping[str, object]) -> tuple[str, int, str]:
        return (
            self.archive.ref.attempt_id,
            self.base.revision,
            cast(str, request["input_fingerprint"]),
        )

    def _find(
        self,
        records: tuple[JournalRecord, ...],
        request: Mapping[str, object],
        base: Checkpoint,
        source: AttemptArchive | None = None,
    ) -> tuple[JournalEntry, JournalEntry | None] | None:
        matching = []
        responses = {
            r.entry.payload["request_id"]: r.entry
            for r in records
            if r.entry.kind in ("response_validated", "response_failed")
        }
        committed = {
            r.entry.payload["request_id"]
            for r in records
            if r.entry.kind == "action_resolved"
        }
        for record in records:
            entry = record.entry
            p = entry.payload
            if entry.kind not in ("request_started", "response_reused") or any(
                canonical(p[k]) != canonical(request[k])
                for k in (
                    "source_tick",
                    "actor_label",
                    "input_fingerprint",
                    "config_fingerprint",
                    "request",
                )
            ):
                continue
            revision = cast(int, p["base_revision"])
            # Only a sealed external source may alias an operational checkpoint.
            # Local requests always retain their actual complete-base identity.
            if revision != base.revision and (
                source is None
                or revision > base.revision
                or not _same_checkpoint(source.checkpoint(revision), base)
            ):
                continue
            response = (
                entry
                if entry.kind == "response_reused"
                else responses.get(p["request_id"])
            )
            matching.append((entry, response))
        validated = [
            pair
            for pair in matching
            if pair[1] is not None
            and pair[1].kind in ("response_validated", "response_reused")
        ]
        owned = [
            pair for pair in validated if pair[0].payload["request_id"] in committed
        ]
        return (owned or validated or matching)[-1] if matching else None

    def _reuse(
        self, item: DecisionInput, request: Mapping[str, object]
    ) -> _Staged | None:
        source = self.archive
        base = self.base
        seal = source.journal_boundary()
        seen = {source.ref.attempt_id}
        owned: list[AttemptArchive] = []
        try:
            while True:
                found = self._find(
                    source.journal_records(through_sequence=seal.sequence),
                    request,
                    base,
                    source if source is not self.archive else None,
                )
                if found is not None:
                    started, response = found
                    if response is None or response.kind == "response_failed":
                        key = self._retry_key(request)
                        if key not in self.driver._retry:
                            self.driver._retry.add(key)
                            self.error_code = (
                                "uncertain"
                                if response is None
                                else cast(str, response.payload["code"])
                            )
                            if source is self.archive and response is None:
                                self.archive.append(
                                    JournalEntry(
                                        "response_failed",
                                        {
                                            "request_id": started.payload["request_id"],
                                            "code": "uncertain",
                                            **(
                                                {
                                                    "response_trace": empty_response_trace()
                                                }
                                                if "request_trace" in started.payload
                                                else {}
                                            ),
                                        },
                                    )
                                )
                            return None
                        return None
                    decision = _validated(
                        self.candidate,
                        item,
                        parse_decision_response(
                            canonical(response.payload["decision"]), item.options
                        ),
                    )
                    request_id = cast(str, started.payload["request_id"])
                    if source is not self.archive:
                        request_id = uuid4().hex
                        reused = {
                            **request,
                            "request_id": request_id,
                            "decision": decision_document(decision),
                            "source": {
                                "attempt_id": source.ref.attempt_id,
                                "request_id": started.payload["request_id"],
                                "boundary": asdict(seal),
                            },
                        }
                        reused.update(trace_fields(started, response))
                        blobs = capture_trace_blobs(source, seal, (started, response))
                        self.archive.record(
                            (JournalEntry("response_reused", reused),),
                            inference_blobs=blobs,
                        )
                    return _Staged(item, request_id, decision)
                parent = _parent(source, base, seen)
                if parent is None:
                    return None
                source, base, seal = parent
                owned.append(source)
                if effective_config_fingerprint(source.config) != self.fingerprint:
                    return None
        finally:
            for parent_archive in owned:
                parent_archive.close()

    def poll(self) -> Literal["waiting", "ready", "provider_error", "paused"]:
        if self.closed:
            raise RuntimeError("Preparation closed.")
        if self.error_code is not None:
            return "provider_error"
        if self.active is not None:
            item, job, request, _, dispatch_at, dispatch_clock = self.active
            result = self.driver.broker.poll(job)
            if result is None:
                return "waiting"
            code = result.error_code
            decision = result.decision
            if decision is not None:
                try:
                    decision = _validated(self.candidate, item, decision)
                except Exception:  # noqa: BLE001
                    code, decision = "unsafe_response", None
            observation = observation_for_result(
                result,
                dispatch_started_at=dispatch_at,
                broker_seconds=time.monotonic() - dispatch_clock,
            )
            record_response(
                self.archive,
                job,
                result,
                observation,
                decision=decision,
                error_code=code,
            )
            acknowledge_recorded(self.driver.broker, job, result)
            self.active = None
            if code is not None:
                self.driver._retry.add(self._retry_key(request))
                self.error_code = code
                return "provider_error"
            assert decision is not None
            self.staged.append(_Staged(item, job, decision))
        if self.paused:
            return "paused"
        if len(self.staged) == len(self.items):
            self.activity = None
            return "ready"
        item = self.items[len(self.staged)]
        prepared = prepare_inference(self.driver.config, item.context, item.options)
        request = self._request(item, prepared)
        reused = self._reuse(item, request)
        if self.error_code is not None:
            return "provider_error"
        if reused is not None:
            self.staged.append(reused)
            return "waiting" if len(self.staged) < len(self.items) else "ready"
        maximum = cast(
            Mapping[str, object], self.archive.config.settings.get("limits", {})
        ).get("max_requests", 40)
        count = sum(entry.kind == "request_started" for entry in self.archive.entries())
        if count >= cast(int, maximum):
            self.error_code = "request_budget_exhausted"
            return "provider_error"
        job = uuid4().hex
        record_request(self.archive, {**request, "request_id": job}, prepared)
        dispatch_at, dispatch_clock = utc_now(), time.monotonic()
        self.active = item, job, request, prepared, dispatch_at, dispatch_clock
        self.activity = "awaiting_model"
        try:
            self.driver.broker.bind_trace(
                job,
                prepared,
                spool_root=self.archive.database_path.parent / "inference-spool",
            )
            self.driver.broker.start(job, self.driver.config, item)
        except Exception:  # noqa: BLE001
            self.driver.broker.close()
            try:
                result = self.driver.broker.poll(job)
            except Exception:  # noqa: BLE001
                result = None
            result = result or BrokerResult(job, None, "worker_failed", None, 0.0)
            observation = observation_for_result(
                result,
                dispatch_started_at=dispatch_at,
                broker_seconds=time.monotonic() - dispatch_clock,
            )
            record_response(
                self.archive,
                job,
                result,
                observation,
                decision=None,
                error_code="worker_failed",
            )
            acknowledge_recorded(self.driver.broker, job, result)
            self.active = None
            self.driver._retry.add(self._retry_key(request))
            self.error_code = "worker_failed"
            return "provider_error"
        return "waiting"

    def request_pause(self) -> None:
        self.paused = True

    def install(self) -> None:
        if (
            self.active is not None
            or self.error_code is not None
            or self.paused
            or len(self.staged) != len(self.items)
        ):
            raise ArchiveFormatError("Proposals are not ready.")
        self.system = _ProposalSystem(self.candidate, self.base, tuple(self.staged))
        self.candidate.configure_proposal_system(self.system)
        self._boundary = prepare_boundary_disturbance(
            self.candidate, self.archive.config
        )

    def finish_tick(self) -> DriverCommit:
        if (
            self.system is None
            or self.system.outcomes is None
            or self.candidate.state.tick != decode_world(self.base.snapshot).tick + 1
        ):
            raise ArchiveFormatError("Incomplete live tick.")
        outcomes = self.system.outcomes
        boundary = apply_boundary_disturbance(
            self.candidate,
            self.archive.config,
            base_revision=self.base.revision,
            prepared=self._boundary,
        )
        return DriverCommit(
            _cursor(self.candidate, self.fingerprint, self.binding),
            self.driver.feedback.after_tick(self.candidate, outcomes),
            outcomes + boundary,
        )

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.driver.broker.close()
            if self.active is not None:
                _, job, request, _, dispatch_at, dispatch_clock = self.active
                try:
                    result = self.driver.broker.poll(job)
                except Exception:  # noqa: BLE001
                    result = None
                result = result or BrokerResult(job, None, "cancelled", None, 0.0)
                observation = observation_for_result(
                    result,
                    dispatch_started_at=dispatch_at,
                    broker_seconds=time.monotonic() - dispatch_clock,
                )
                record_response(
                    self.archive,
                    job,
                    result,
                    observation,
                    decision=None,
                    error_code="cancelled",
                )
                acknowledge_recorded(self.driver.broker, job, result)
                self.driver._retry.add(self._retry_key(request))
                self.active = None
            latest = self.archive.checkpoint()
            committed = (
                latest.revision > self.base.revision
                and decode_world(latest.snapshot).tick
                == decode_world(self.base.snapshot).tick + 1
            )
            if not committed and not self._aborted:
                self.archive.append(
                    JournalEntry(
                        "candidate_aborted",
                        {
                            "base_revision": self.base.revision,
                            "reason": "preparation_discarded",
                        },
                    )
                )
                self._aborted = True
        finally:
            self.candidate.configure_work_interruption(None)
            self._boundary = None
            self.candidate.configure_proposal_system(None)
            self.staged.clear()
            self.system = None
