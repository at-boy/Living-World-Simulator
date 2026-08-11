from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(slots=True, frozen=True)
class Event:
    """An immutable record of something that happened in the world."""

    id: str

    tick: int

    kind: str

    subject_id: str | None = None

    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Detach and recursively freeze event attributes."""

        object.__setattr__(self, "attributes", _freeze_mapping(self.attributes))


def _freeze_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    frozen_values: dict[str, object] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            raise TypeError("Event attribute keys must be strings.")
        frozen_values[key] = _freeze_value(value)
    return MappingProxyType(frozen_values)


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return value
