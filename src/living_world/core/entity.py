from dataclasses import dataclass, field


@dataclass(slots=True)
class Entity:
    """A runtime entity in the simulation."""

    id: str

    definition_key: str

    name: str

    attributes: dict[str, object] = field(default_factory=dict)

    created_tick: int = 0

    destroyed_tick: int | None = None
