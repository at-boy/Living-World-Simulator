from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Occupation:
    """Validated occupation presentation data for a generic NPC entity."""

    title: str
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            raise TypeError("Occupation title must be a string.")
        if not self.title.strip():
            raise ValueError("Occupation title cannot be empty.")
        if not isinstance(self.description, str):
            raise TypeError("Occupation description must be a string.")
        if not self.description.strip():
            raise ValueError("Occupation description cannot be empty.")

    def to_attribute(self) -> dict[str, str]:
        """Return the JSON-compatible entity attribute representation."""

        return {"title": self.title, "description": self.description}

    @classmethod
    def from_attribute(cls, value: object) -> Occupation:
        """Validate and construct an occupation from an entity attribute."""

        if not isinstance(value, Mapping):
            raise TypeError("Occupation must be a mapping.")
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Occupation keys must be strings.")

        unknown_fields = set(value).difference({"title", "description"})
        if unknown_fields:
            field_names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Occupation has unknown fields: {field_names}.")

        title = value.get("title")
        description = value.get("description")
        if not isinstance(title, str):
            raise TypeError("Occupation title must be a string.")
        if not isinstance(description, str):
            raise TypeError("Occupation description must be a string.")

        return cls(title=title, description=description)
