"""Immutable replay records and content identity."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum

from living_world.cognition.npc_cognition_client import NPCDecision, _require_prose

_MESSAGES = {
    "invalid_tape": "Invalid proposal tape.",
    "scenario_mismatch": "Proposal scenario does not match.",
    "actor_mismatch": "Proposal actor does not match.",
    "offered_action_mismatch": "Proposal vocabulary does not match.",
    "tape_exhausted": "Proposal tape is exhausted.",
    "unused_entries": "Proposal tape has unused entries.",
    "missing_replay_preparation": "Replay preparation is required.",
    "replay_state_invalid": "Replay state is invalid.",
}


class ProposalTapeError(ValueError):
    def __init__(self, code: str) -> None:
        if code not in _MESSAGES:
            raise ValueError("Unknown proposal error code.")
        self.code = code
        super().__init__(f"{code}: {_MESSAGES[code]}")


def integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def fingerprint_valid(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def prose(value: object, *, code: str = "invalid_tape") -> None:
    try:
        _require_prose(value, "Proposal prose")
    except (ValueError, TypeError):
        raise ProposalTapeError(code) from None


@dataclass(frozen=True, slots=True)
class ProposalTapeEntry:
    sequence: int
    actor_label: str
    decision: NPCDecision
    rationale: str

    def __post_init__(self) -> None:
        if (
            not integer(self.sequence)
            or self.sequence < 1
            or not isinstance(self.decision, NPCDecision)
        ):
            raise ProposalTapeError("invalid_tape")
        prose(self.actor_label)
        prose(self.rationale)
        try:
            NPCDecision(self.decision.spoken_text, self.decision.action_request)
        except (TypeError, ValueError):
            raise ProposalTapeError("invalid_tape") from None
        request = self.decision.action_request
        if request is not None and request.rationale != self.rationale:
            raise ProposalTapeError("invalid_tape")


@dataclass(frozen=True, slots=True)
class ProposalTape:
    schema_version: int
    scenario_key: str
    scenario_fingerprint: str
    entries: tuple[ProposalTapeEntry, ...]

    def __post_init__(self) -> None:
        if (
            not integer(self.schema_version)
            or self.schema_version != 1
            or not fingerprint_valid(self.scenario_fingerprint)
        ):
            raise ProposalTapeError("invalid_tape")
        prose(self.scenario_key)
        if not isinstance(self.entries, tuple) or not self.entries:
            raise ProposalTapeError("invalid_tape")
        if any(
            not isinstance(entry, ProposalTapeEntry) or entry.sequence != index
            for index, entry in enumerate(self.entries, 1)
        ):
            raise ProposalTapeError("invalid_tape")
        self._canonical_bytes()

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self._canonical_bytes()).hexdigest()

    def _canonical_bytes(self) -> bytes:
        """Validate identity encoding eagerly without changing Unicode codepoints."""
        entries: list[dict[str, object]] = []
        for entry in self.entries:
            request = entry.decision.action_request
            entries.append(
                {
                    "sequence": entry.sequence,
                    "actor_label": entry.actor_label,
                    "action": (
                        None
                        if request is None
                        else {
                            "key": request.action_key,
                            "target_label": request.target_label,
                            "arguments": dict(request.arguments),
                        }
                    ),
                    "speech": entry.decision.spoken_text,
                    "rationale": entry.rationale,
                }
            )
        value = {
            "schema_version": self.schema_version,
            "scenario_key": self.scenario_key,
            "scenario_fingerprint": self.scenario_fingerprint,
            "entries": entries,
        }
        try:
            return json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise ProposalTapeError("invalid_tape") from None


@dataclass(frozen=True, slots=True)
class ReplayBinding:
    scenario_key: str
    scenario_fingerprint: str
    tape_fingerprint: str
    actor_sequence: tuple[str, ...]
    configured_tick: int

    def __post_init__(self) -> None:
        prose(self.scenario_key, code="replay_state_invalid")
        if (
            not fingerprint_valid(self.scenario_fingerprint)
            or not fingerprint_valid(self.tape_fingerprint)
            or not integer(self.configured_tick)
        ):
            raise ProposalTapeError("replay_state_invalid")
        if not isinstance(self.actor_sequence, tuple) or not self.actor_sequence:
            raise ProposalTapeError("replay_state_invalid")
        for label in self.actor_sequence:
            prose(label, code="replay_state_invalid")


@dataclass(frozen=True, slots=True)
class ReplayState:
    next_index: int
    last_attempt_tick: int | None = None

    def __post_init__(self) -> None:
        if not integer(self.next_index) or (
            self.last_attempt_tick is not None and not integer(self.last_attempt_tick)
        ):
            raise ProposalTapeError("replay_state_invalid")


class ReplayOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NO_ACTION = "no_action"
