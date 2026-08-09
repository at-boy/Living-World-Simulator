from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Definition:
    """Template describing what may exist."""

    key: str

    initial_attributes: dict[str, object] = field(default_factory=dict)

    systems: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the definition vocabulary used by runtime entity creation."""

        if not self.key.strip():
            raise ValueError("Definition key cannot be empty.")

        if any(not system.strip() for system in self.systems):
            raise ValueError("Definition systems cannot contain empty names.")
