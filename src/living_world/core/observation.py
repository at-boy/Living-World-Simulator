from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Observation:
    """Immutable record of an entity's perception of another entity."""

    id: str
    tick: int
    observer: str
    subject: str
    description: str
    confidence: float
    evidence: Mapping[str, object]
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence",
            MappingProxyType(dict(self.evidence)),
        )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )
