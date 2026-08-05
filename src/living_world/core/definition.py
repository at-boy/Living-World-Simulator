from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Definition:
    """Template describing what may exist."""

    key: str

    initial_attributes: dict[str, object] = field(default_factory=dict)

    systems: tuple[str, ...] = ()
