"""Owner-called atomic inference imports and authenticated trace projections."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from living_world.archives import (
    ArchiveFormatError,
    AttemptArchive,
    InferenceBlob,
    JournalBoundary,
    JournalEntry,
)
from living_world.archives.model import canonical
from living_world.cognition.npc_cognition_client import NPCDecision

from .broker import BrokerResult, DecisionBroker, decision_document
from .inference_trace import (
    InferenceObservation,
    PreparedInference,
    settle_observation,
    utc_now,
)


def record_request(
    archive: AttemptArchive, request: Mapping[str, object], prepared: PreparedInference
) -> None:
    archive.record(
        (
            JournalEntry(
                "request_started", {**request, "request_trace": prepared.request_trace}
            ),
        ),
        inference_blobs=(InferenceBlob(prepared.body),),
    )


def observation_for_result(
    result: BrokerResult, *, dispatch_started_at: str, broker_seconds: float
) -> InferenceObservation:
    if result.response_trace is not None:
        return InferenceObservation(result.response_trace, result.response_body)
    return settle_observation(
        None,
        dispatch_started_at=dispatch_started_at,
        settled_at=utc_now(),
        broker_seconds=broker_seconds,
    )


def record_response(
    archive: AttemptArchive,
    request_id: str,
    result: BrokerResult,
    observation: InferenceObservation,
    *,
    decision: NPCDecision | None,
    error_code: str | None,
) -> None:
    if (decision is None) == (error_code is None):
        raise ValueError("Expected exclusive decision or error.")
    payload: dict[str, object] = {
        "request_id": request_id,
        "response_trace": observation.response_trace,
    }
    if result.response_digest is not None:
        payload["content_digest"] = result.response_digest
    if decision is not None:
        payload.update(
            decision=decision_document(decision), elapsed_seconds=result.elapsed_seconds
        )
    else:
        payload["code"] = error_code
    archive.record(
        (
            JournalEntry(
                "response_validated" if decision is not None else "response_failed",
                payload,
            ),
        ),
        inference_blobs=(
            () if observation.body is None else (InferenceBlob(observation.body),)
        ),
    )


def trace_fields(
    started: JournalEntry, response: JournalEntry | None
) -> dict[str, object]:
    if (
        response is not None
        and started.payload["request_id"] != response.payload["request_id"]
    ):
        raise ArchiveFormatError("Inference trace identity mismatch.")
    fields: dict[str, object] = {}
    if "request_trace" in started.payload:
        fields["request_trace"] = started.payload["request_trace"]
    if response is not None:
        for key in ("response_trace", "content_digest", "elapsed_seconds"):
            if key in response.payload:
                fields[key] = response.payload[key]
    return fields


def capture_trace_blobs(
    source: AttemptArchive, boundary: JournalBoundary, entries: tuple[JournalEntry, ...]
) -> tuple[InferenceBlob, ...]:
    def verify() -> None:
        if source.journal_boundary(through_sequence=boundary.sequence) != boundary:
            raise ArchiveFormatError("Inference source seal mismatch.")

    verify()
    prefix = source.journal_records(through_sequence=boundary.sequence)
    available = {
        canonical({"kind": r.entry.kind, "payload": r.entry.payload}) for r in prefix
    }
    if any(
        canonical({"kind": e.kind, "payload": e.payload}) not in available
        for e in entries
    ):
        raise ArchiveFormatError("Inference entries outside selected prefix.")
    digests = sorted(
        {
            trace["body_digest"]
            for entry in entries
            for key in ("request_trace", "response_trace")
            if (trace := entry.payload.get(key)) is not None
            and trace["body_digest"] is not None
        }
    )
    blobs = source.inference_blobs(tuple(digests), through_sequence=boundary.sequence)
    verify()
    return blobs


def acknowledge_recorded(
    broker: DecisionBroker, request_id: str, result: BrokerResult
) -> None:
    try:
        broker.acknowledge_trace(request_id, result=result)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning("Inference trace cleanup pending.")
