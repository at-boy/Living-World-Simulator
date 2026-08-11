"""NPC-held, source-attributed knowledge claims."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from living_world.core.memory import CognitiveSalience


@dataclass(frozen=True, slots=True)
class Knowledge:
    """An immutable NPC-held claim with NPC-readable source attribution.

    Knowledge records what a holder has heard or otherwise learned.  It is not
    an assertion of authoritative world truth and may be incomplete, stale, or
    false.  Supporting record identifiers are internal provenance only.
    """

    id: str
    tick: int
    holder_id: str
    subject_id: str
    statement: str
    source_description: str
    salience: CognitiveSalience
    supporting_observations: tuple[str, ...] = ()
    supporting_memories: tuple[str, ...] = ()
    supporting_experiences: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("Knowledge id", self.id),
            ("Knowledge holder_id", self.holder_id),
            ("Knowledge subject_id", self.subject_id),
            ("Knowledge statement", self.statement),
            ("Knowledge source_description", self.source_description),
        ):
            _require_non_empty_string(value, field_name)
        if not isinstance(self.tick, int) or isinstance(self.tick, bool):
            raise TypeError("Knowledge tick must be an integer.")
        if not isinstance(self.salience, CognitiveSalience):
            raise TypeError("Knowledge salience must be a CognitiveSalience value.")

        object.__setattr__(
            self,
            "supporting_observations",
            _provenance_ids(self.supporting_observations, "observation"),
        )
        object.__setattr__(
            self,
            "supporting_memories",
            _provenance_ids(self.supporting_memories, "memory"),
        )
        object.__setattr__(
            self,
            "supporting_experiences",
            _provenance_ids(self.supporting_experiences, "experience"),
        )
        provenance_ids = (
            self.supporting_observations
            + self.supporting_memories
            + self.supporting_experiences
        )
        _reject_visible_provenance(self.statement, "statement", provenance_ids)
        _reject_visible_provenance(
            self.source_description,
            "source_description",
            provenance_ids,
        )
        if not isinstance(self.metadata, Mapping):
            raise TypeError("Knowledge metadata must be a mapping.")
        if not all(isinstance(key, str) for key in self.metadata):
            raise TypeError("Knowledge metadata keys must be strings.")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _provenance_ids(value: object, record_kind: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(
            f"Knowledge supporting {record_kind} IDs must be a tuple of strings."
        )
    identifiers = value
    if not all(
        isinstance(identifier, str) and identifier.strip() for identifier in identifiers
    ):
        raise ValueError(
            f"Knowledge supporting {record_kind} IDs must be non-empty strings."
        )
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"Knowledge supporting {record_kind} IDs must be unique.")
    return identifiers


def _reject_visible_provenance(
    text: str,
    field_name: str,
    provenance_ids: tuple[str, ...],
) -> None:
    if any(identifier in text for identifier in provenance_ids):
        raise ValueError(
            f"Knowledge {field_name} cannot contain internal provenance identifiers."
        )


def _freeze_metadata(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_metadata(item) for key, item in value.items()}
        )
    if isinstance(value, tuple | list):
        return tuple(_freeze_metadata(item) for item in value)
    if isinstance(value, frozenset | set):
        return frozenset(_freeze_metadata(item) for item in value)
    return value
