from dataclasses import dataclass, field


@dataclass(slots=True)
class Relationship:
    id: str
    kind: str
    source_id: str
    target_id: str
    properties: dict[str, object] = field(default_factory=dict)
    created_tick: int = 0
    destroyed_tick: int | None = None
