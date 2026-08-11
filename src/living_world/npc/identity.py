from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NPCIdentity:
    """Validated presentation data for a generic NPC entity."""

    name: str
    description: str
    capability_descriptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("NPC identity name must be a string.")
        if not self.name.strip():
            raise ValueError("NPC identity name cannot be empty.")

        if not isinstance(self.description, str):
            raise TypeError("NPC identity description must be a string.")
        if not self.description.strip():
            raise ValueError("NPC identity description cannot be empty.")

        if not isinstance(self.capability_descriptions, tuple):
            raise TypeError("NPC identity capability descriptions must be a tuple.")
        if any(
            not isinstance(description, str)
            for description in self.capability_descriptions
        ):
            raise TypeError(
                "NPC identity capability descriptions must contain only strings."
            )
        if any(not description.strip() for description in self.capability_descriptions):
            raise ValueError(
                "NPC identity capability descriptions must be non-empty strings."
            )

        object.__setattr__(
            self,
            "capability_descriptions",
            tuple(self.capability_descriptions),
        )

    def to_attribute(self) -> dict[str, object]:
        """Return the JSON-compatible entity attribute representation."""

        return {
            "name": self.name,
            "description": self.description,
            "capability_descriptions": list(self.capability_descriptions),
        }

    @classmethod
    def from_attribute(cls, value: object) -> NPCIdentity:
        """Validate and construct an identity from an entity attribute."""

        attributes = _require_mapping(value, "NPC identity")
        _reject_unknown_fields(
            attributes,
            frozenset({"name", "description", "capability_descriptions"}),
            "NPC identity",
        )

        name = attributes.get("name")
        description = attributes.get("description")
        capability_descriptions = attributes.get("capability_descriptions", [])

        if not isinstance(name, str):
            raise TypeError("NPC identity name must be a string.")
        if not isinstance(description, str):
            raise TypeError("NPC identity description must be a string.")
        if not isinstance(capability_descriptions, list) or any(
            not isinstance(capability, str) for capability in capability_descriptions
        ):
            raise TypeError(
                "NPC identity capability_descriptions must be a list of strings."
            )

        return cls(
            name=name,
            description=description,
            capability_descriptions=tuple(capability_descriptions),
        )


def _require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be a mapping.")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{context} keys must be strings.")
    return value


def _reject_unknown_fields(
    attributes: Mapping[str, object],
    allowed_fields: frozenset[str],
    context: str,
) -> None:
    unknown_fields = set(attributes).difference(allowed_fields)
    if unknown_fields:
        field_names = ", ".join(sorted(unknown_fields))
        raise ValueError(f"{context} has unknown fields: {field_names}.")
