from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Event:
    """An immutable record of something that happened in the world."""

    id: str

    tick: int

    kind: str

    subject_id: str | None = None

    attributes: dict[str, object] = field(default_factory=dict)
