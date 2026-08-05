from dataclasses import dataclass, field


@dataclass(slots=True)
class Relationship:
    """Runtime connection between two entities."""

    id: str

    kind: str

    source_id: str

    target_id: str

    attributes: dict[str, object] = field(default_factory=dict)

    created_tick: int = 0

    destroyed_tick: int | None = None
