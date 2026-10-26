"""Closed, immutable engine-only archive format-one records."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from living_world.cognition.local_llm_cognition_format import parse_decision_response
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCDecision,
    _require_prose,
)
from living_world.cognition.retrieval import RetrievedCognition
from living_world.repositories.world_snapshot import WorldSnapshot


class ArchiveError(RuntimeError):
    """An archive operation failed without publishing partial state."""


class ArchiveFormatError(ArchiveError):
    """An archive record or stored format is invalid."""


class ArchiveRevisionConflict(ArchiveError):
    """An optimistic revision or identity was reused divergently."""


STATES = frozenset(
    (
        "initializing",
        "paused",
        "running",
        "awaiting_model",
        "pause_requested",
        "provider_error_paused",
        "stepping",
        "completed",
        "stopped",
        "failed",
        "interrupted",
    )
)
TERMINAL_STATES = frozenset(("completed", "stopped", "failed", "interrupted"))


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArchiveFormatError("Expected a nonempty string.")
    return value


def integer(value: object, *, minimum: int | None = 0) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ArchiveFormatError("Expected an exact integer in range.")
    return value


def digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ArchiveFormatError("Expected a lowercase SHA256 digest.")
    return value


def identifier(value: object) -> str:
    value = text(value)
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ArchiveFormatError("Expected UUID4 hex identity.") from exc
    if parsed.version != 4 or parsed.hex != value:
        raise ArchiveFormatError("Expected UUID4 hex identity.")
    return value


def document(
    value: object, required: set[str], optional: set[str] = frozenset()
) -> Mapping[str, object]:
    if (
        not isinstance(value, Mapping)
        or not required <= value.keys()
        or not value.keys() <= required | optional
    ):
        raise ArchiveFormatError("Unexpected or missing document fields.")
    return value


def freeze(value: object) -> object:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ArchiveFormatError("JSON object keys must be strings.")
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    raise ArchiveFormatError("Expected finite JSON data.")


def frozen_map(value: object) -> Mapping[str, object]:
    result = freeze(value)
    if not isinstance(result, Mapping):
        raise ArchiveFormatError("Expected a JSON object.")
    return result


def plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [plain(item) for item in value]
    return value


def canonical(value: object) -> str:
    return json.dumps(
        plain(freeze(value)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def loads(value: object) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in items:
            if key in result:
                raise ArchiveFormatError("Duplicate JSON key.")
            result[key] = item
        return result

    if not isinstance(value, str):
        raise ArchiveFormatError("Expected JSON text.")
    try:
        return freeze(json.loads(value, object_pairs_hook=pairs))
    except (ValueError, TypeError) as exc:
        raise ArchiveFormatError("Malformed JSON document.") from exc


@dataclass(frozen=True)
class AttemptRef:
    lineage_id: str
    attempt_id: str
    directory: Path

    def __post_init__(self) -> None:
        identifier(self.lineage_id)
        identifier(self.attempt_id)
        if not isinstance(self.directory, Path):
            raise ArchiveFormatError("Directory must be a Path.")


@dataclass(frozen=True, kw_only=True)
class BoundaryDisturbance:
    """Version-one, fixed completed-boundary policy; never NPC-facing."""

    kind: Literal["resource_loss", "work_blockage"]
    format: int = 1
    at_tick: int = 2

    def __post_init__(self) -> None:
        if (
            integer(self.format) not in (1, 2)
            or integer(self.at_tick) != 2
            or (self.format == 2 and self.kind != "work_blockage")
        ):
            raise ArchiveFormatError("Unknown boundary disturbance schedule.")
        if type(self.kind) is not str or self.kind not in (
            "resource_loss",
            "work_blockage",
        ):
            raise ArchiveFormatError("Unknown boundary disturbance kind.")

    def as_document(self) -> dict[str, object]:
        return {"format": self.format, "at_tick": self.at_tick, "kind": self.kind}

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical(self.as_document()).encode()).hexdigest()


def parse_boundary_disturbance(value: object) -> BoundaryDisturbance:
    return BoundaryDisturbance(**document(value, {"format", "at_tick", "kind"}))


def _validate_boundary_entry(p: Mapping[str, object]) -> None:
    policy = BoundaryDisturbance(kind=p["kind"], at_tick=p["boundary_tick"])
    fingerprints = {policy.fingerprint}
    if policy.kind == "work_blockage":
        fingerprints.add(
            BoundaryDisturbance(kind="work_blockage", format=2).fingerprint
        )
    if digest(p["schedule_fingerprint"]) not in fingerprints:
        raise ArchiveFormatError("Boundary schedule fingerprint mismatch.")
    target = p["target_id"]
    if target is not None:
        text(target)
    refs = array(p["event_references"])
    for ref in refs:
        text(ref)
    if len(set(refs)) != len(refs):
        raise ArchiveFormatError("Duplicate boundary event reference.")
    outcome = p["outcome"]
    quantities = p["quantity_before"], p["quantity_after"]
    if outcome == "terminal" or (
        policy.kind == "work_blockage" and outcome == "no_eligible_work"
    ):
        valid = (
            target is None
            and p["resource"] is None
            and quantities == (None, None)
            and not refs
        )
    elif policy.kind == "resource_loss" and outcome in ("applied", "empty_stock"):
        before, after = integer(quantities[0]), integer(quantities[1])
        valid = target is not None and p["resource"] == "timber" and after == 0
        valid = valid and (
            (before > 0 and len(refs) == 1)
            if outcome == "applied"
            else (before == 0 and not refs)
        )
    elif policy.kind == "work_blockage" and outcome == "applied":
        valid = (
            target is not None
            and p["resource"] is None
            and quantities == (None, None)
            and bool(refs)
        )
    else:
        valid = False
    if not valid:
        raise ArchiveFormatError("Invalid boundary disturbance outcome.")


@dataclass(frozen=True)
class AttemptConfig:
    mode: Literal["recorded", "ollama", "journal_replay"]
    scenario_key: str
    seed: int
    software_revision: str
    settings: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.mode not in ("recorded", "ollama", "journal_replay"):
            raise ArchiveFormatError("Unknown archive mode.")
        text(self.scenario_key)
        text(self.software_revision)
        integer(self.seed, minimum=None)
        settings = document(
            self.settings,
            set(),
            {
                "provider",
                "limits",
                "recorded_outcome",
                "launch_source",
                "disturbance",
                "boundary_disturbance",
                "driver_format",
                "source_config_fingerprint",
                "finalize_proposals",
            },
        )
        if "finalize_proposals" in settings and (
            self.mode != "recorded" or type(settings["finalize_proposals"]) is not bool
        ):
            raise ArchiveFormatError("Finalization flag requires recorded boolean.")
        if "provider" in settings:
            provider = document(
                settings["provider"],
                set(),
                {
                    "model",
                    "base_url",
                    "timeout_seconds",
                    "max_output_tokens",
                    "max_response_bytes",
                    "temperature",
                    "seed",
                    "model_digest",
                },
            )
            for key, value in provider.items():
                if key in ("model", "model_digest"):
                    text(value)
                elif key == "base_url":
                    try:
                        url = urlsplit(text(value))
                        if (
                            url.scheme not in ("http", "https")
                            or url.hostname not in ("localhost", "127.0.0.1", "::1")
                            or url.username is not None
                            or url.password is not None
                            or url.query
                            or url.fragment
                        ):
                            raise ValueError()
                        _ = url.port
                    except ValueError as exc:
                        raise ArchiveFormatError(
                            "Provider URL must be credential-free loopback HTTP(S)."
                        ) from exc
                elif key in ("max_output_tokens", "max_response_bytes"):
                    integer(value, minimum=1)
                elif key == "seed":
                    integer(value, minimum=None)
                elif (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or value < 0
                    or (key == "timeout_seconds" and value == 0)
                ):
                    raise ArchiveFormatError("Provider numeric value out of range.")
        if "limits" in settings:
            limits = document(
                settings["limits"],
                set(),
                {
                    "max_ticks",
                    "max_requests",
                    "max_perceptions",
                    "max_memories",
                    "max_request_characters",
                    "save_every",
                    "continuous",
                },
            )
            if "continuous" in limits and (
                self.mode != "recorded"
                or type(limits["continuous"]) is not bool
                or (limits["continuous"] and limits.get("max_ticks") is not None)
            ):
                raise ArchiveFormatError("Invalid recorded continuous intent.")
            for key, value in limits.items():
                if key == "continuous":
                    continue
                if key != "max_ticks" or value is not None:
                    integer(
                        value,
                        minimum=(
                            0 if key == "max_ticks" and self.mode == "recorded" else 1
                        ),
                    )
        for key, choices in (
            ("recorded_outcome", ("success", "stall", "failure")),
            ("launch_source", ("cli", "browser", "agent")),
            ("disturbance", ("none", "resource_loss", "work_blockage")),
        ):
            if key in settings and settings[key] not in choices:
                raise ArchiveFormatError("Unknown configuration value.")
        if "boundary_disturbance" in settings:
            policy = parse_boundary_disturbance(settings["boundary_disturbance"])
            if self.mode != "ollama" or settings.get("disturbance") != policy.kind:
                raise ArchiveFormatError(
                    "Boundary policy requires matching live label."
                )
        if "driver_format" in settings:
            integer(settings["driver_format"], minimum=1)
        if "source_config_fingerprint" in settings:
            digest(settings["source_config_fingerprint"])
        object.__setattr__(self, "settings", frozen_map(settings))


@dataclass(frozen=True)
class Checkpoint:
    revision: int
    snapshot: WorldSnapshot
    driver_cursor: Mapping[str, object]
    feedback_cursor: Mapping[str, object]

    def __post_init__(self) -> None:
        integer(self.revision)
        if not isinstance(self.snapshot, WorldSnapshot):
            raise ArchiveFormatError("Expected a WorldSnapshot.")
        object.__setattr__(self, "driver_cursor", frozen_map(self.driver_cursor))
        object.__setattr__(self, "feedback_cursor", frozen_map(self.feedback_cursor))


@dataclass(frozen=True)
class CommandEnvelope:
    command_id: str
    action: Literal["pause", "resume", "step", "stop", "retry"]
    expected_state_version: int

    def __post_init__(self) -> None:
        text(self.command_id)
        if self.action not in ("pause", "resume", "step", "stop", "retry"):
            raise ArchiveFormatError("Unknown command action.")
        integer(self.expected_state_version)


@dataclass(frozen=True)
class CommandReceipt:
    command_id: str
    status: Literal["queued", "applied", "rejected"]
    state_version: int
    revision: int
    reason: str | None

    def __post_init__(self) -> None:
        text(self.command_id)
        if self.status not in ("queued", "applied", "rejected"):
            raise ArchiveFormatError("Unknown receipt status.")
        integer(self.state_version)
        integer(self.revision)
        if self.reason is not None:
            text(self.reason)


def envelope(value: object) -> CommandEnvelope:
    return CommandEnvelope(
        **document(value, {"command_id", "action", "expected_state_version"})
    )


def receipt(value: object) -> CommandReceipt:
    return CommandReceipt(
        **document(
            value, {"command_id", "status", "state_version", "revision", "reason"}
        )
    )


def actions(request: Mapping[str, object]) -> tuple[ActionOption, ...]:
    return tuple(
        ActionOption(
            **{
                **document(item, {"key", "description", "target_labels"}),
                "target_labels": array(item["target_labels"]),
            }
        )
        for item in array(request["actions"])
    )


def array(value: object) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise ArchiveFormatError("Expected JSON array.")
    return tuple(value)


def validate_request(value: object) -> None:
    request = document(
        value,
        {
            "identity",
            "self_knowledge",
            "current_perceptions",
            "core_cognition",
            "retrieved_information",
            "conversation_history",
            "actions",
        },
    )
    _require_prose(request["identity"], "identity")
    for key in ("self_knowledge", "current_perceptions", "conversation_history"):
        for prose in array(request[key]):
            _require_prose(prose, key)
    for key in ("core_cognition", "retrieved_information"):
        for cognition in array(request[key]):
            item = RetrievedCognition(
                **document(cognition, {"kind", "text", "importance", "is_core"})
            )
            _require_prose(item.text, "cognition")
    offered = actions(request)
    if len({item.key for item in offered}) != len(offered):
        raise ArchiveFormatError("Duplicate action keys.")


def validate_decision(value: object) -> None:
    decision = document(value, {"spoken_text", "action_request"})
    request = decision["action_request"]
    parsed = (
        None
        if request is None
        else ActionRequest(
            **document(
                request, {"action_key", "target_label", "rationale", "arguments"}
            )
        )
    )
    NPCDecision(decision["spoken_text"], parsed)


@dataclass(frozen=True)
class JournalEntry:
    kind: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        schemas = {
            "request_started": {
                "request_id",
                "base_revision",
                "source_tick",
                "actor_label",
                "input_fingerprint",
                "config_fingerprint",
                "request",
            },
            "response_validated": {"request_id", "decision"},
            "response_failed": {"request_id", "code"},
            "action_resolved": {
                "base_revision",
                "source_tick",
                "actor_label",
                "request_id",
                "outcome",
                "event_references",
            },
            "boundary_disturbance": {
                "base_revision",
                "boundary_tick",
                "kind",
                "schedule_fingerprint",
                "outcome",
                "target_id",
                "resource",
                "quantity_before",
                "quantity_after",
                "event_references",
            },
            "candidate_aborted": {"base_revision", "reason"},
            "control_requested": {"envelope"},
            "control_resolved": {"receipt"},
            "attempt_finished": {"lifecycle", "outcome", "last_revision"},
        }
        schemas["response_reused"] = schemas["request_started"] | {"decision", "source"}
        try:
            if self.kind not in schemas:
                raise ArchiveFormatError("Unknown journal kind.")
            optional = {
                "response_failed": {"content_digest"},
                "response_validated": {"content_digest", "elapsed_seconds"},
                "response_reused": {"content_digest", "elapsed_seconds"},
                "control_requested": {"admitted_state_version"},
            }
            p = document(
                self.payload, schemas[self.kind], optional.get(self.kind, set())
            )
            for key in ("request_id", "actor_label", "reason"):
                if key in p:
                    text(p[key])
            for key in ("base_revision", "source_tick"):
                if key in p:
                    integer(p[key])
            for key in ("input_fingerprint", "config_fingerprint", "content_digest"):
                if key in p:
                    digest(p[key])
            if "elapsed_seconds" in p:
                elapsed = p["elapsed_seconds"]
                if (
                    type(elapsed) not in (int, float)
                    or not math.isfinite(elapsed)
                    or elapsed < 0
                ):
                    raise ArchiveFormatError(
                        "Expected finite nonnegative elapsed time."
                    )
            if self.kind in ("request_started", "response_reused"):
                _require_prose(p["actor_label"], "actor_label")
                validate_request(p["request"])
                if self.kind == "response_reused":
                    validate_decision(p["decision"])
                    validate_offered(p["decision"], p["request"])
                    source = document(
                        p["source"], {"attempt_id", "request_id", "boundary"}
                    )
                    identifier(source["attempt_id"])
                    text(source["request_id"])
                    JournalBoundary(
                        **document(source["boundary"], {"sequence", "digest"})
                    )
            elif self.kind == "response_validated":
                validate_decision(p["decision"])
            elif self.kind == "response_failed":
                if p["code"] not in (
                    "timeout",
                    "transport",
                    "http_error",
                    "invalid_response",
                    "oversized_response",
                    "unsafe_response",
                    "cancelled",
                    "worker_failed",
                    "uncertain",
                ):
                    raise ArchiveFormatError("Unknown failure code.")
            elif self.kind == "action_resolved":
                if p["outcome"] not in ("accepted", "rejected", "no_action"):
                    raise ArchiveFormatError("Unknown action outcome.")
                for item in array(p["event_references"]):
                    text(item)
            elif self.kind == "boundary_disturbance":
                _validate_boundary_entry(p)
            elif self.kind == "control_requested":
                envelope(p["envelope"])
                if "admitted_state_version" in p:
                    integer(p["admitted_state_version"])
            elif self.kind == "control_resolved":
                receipt(p["receipt"])
            elif self.kind == "attempt_finished":
                if p["lifecycle"] not in TERMINAL_STATES:
                    raise ArchiveFormatError("Expected terminal lifecycle.")
                if p["outcome"] is not None:
                    text(p["outcome"])
                if p["last_revision"] is not None:
                    integer(p["last_revision"])
            object.__setattr__(self, "payload", frozen_map(p))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise ArchiveFormatError("Invalid journal payload.") from exc


def validate_offered(decision: object, request: Mapping[str, object]) -> None:
    try:
        parse_decision_response(canonical(decision), actions(request))
    except Exception as exc:
        raise ArchiveFormatError("Decision outside offered vocabulary.") from exc


@dataclass(frozen=True)
class JournalRecord:
    """One committed immutable journal row with its original linkage."""

    sequence: int
    entry: JournalEntry
    checkpoint_revision: int | None
    revision_context: int | None

    def __post_init__(self) -> None:
        integer(self.sequence, minimum=1)
        if not isinstance(self.entry, JournalEntry):
            raise ArchiveFormatError("Expected JournalEntry.")
        for revision in (self.checkpoint_revision, self.revision_context):
            if revision is not None:
                integer(revision)


@dataclass(frozen=True)
class JournalBoundary:
    """Digest of an exact visible prefix; sequence zero denotes the empty prefix."""

    sequence: int
    digest: str

    def __post_init__(self) -> None:
        integer(self.sequence)
        digest(self.digest)


@dataclass(frozen=True)
class ForkPoint:
    """Checkpoint and source journal horizon from a single storage snapshot."""

    checkpoint: Checkpoint
    journal_boundary: JournalBoundary

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint, Checkpoint) or not isinstance(
            self.journal_boundary, JournalBoundary
        ):
            raise ArchiveFormatError("Expected checkpoint and journal boundary.")


def parent_boundary(value: object, parent: object) -> JournalBoundary | None:
    """Parse optional sealed parent metadata shared by reservation and archive."""
    if value is None:
        return None
    if parent is None:
        raise ArchiveFormatError("Parent journal boundary requires a parent.")
    return JournalBoundary(**document(value, {"sequence", "digest"}))
