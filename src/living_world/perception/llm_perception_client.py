"""Provider-neutral boundary for local LLM perception clients."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol


class LLMPerceptionClientError(Exception):
    """Raised when a configured local perception provider cannot respond."""


class LLMPerceptionInvalidResponseError(LLMPerceptionClientError):
    """Raised when a provider response cannot satisfy the perception contract."""


@dataclass(frozen=True)
class LLMPerceptionRequest:
    """Curated engine-side input for a perception model.

    This value deliberately excludes runtime objects and internal entity
    identifiers. A provider receives only data needed to describe a perception.
    """

    observer_name: str
    capabilities: Mapping[str, object]
    subject_name: str
    subject_attributes: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capabilities",
            MappingProxyType(dict(self.capabilities)),
        )
        object.__setattr__(
            self,
            "subject_attributes",
            MappingProxyType(dict(self.subject_attributes)),
        )


@dataclass(frozen=True)
class LLMPerceptionResponse:
    """The only values a perception provider may contribute."""

    description: str
    confidence: float


class LLMPerceptionClient(Protocol):
    """Local-model client used by ``LLMPerceptionEngine``.

    Future Ollama and llama.cpp HTTP adapters implement this protocol without
    changing the engine or its observation contract.
    """

    @property
    def provider_name(self) -> str:
        """Return a stable, non-sensitive name for diagnostics."""

    def perceive(self, request: LLMPerceptionRequest) -> LLMPerceptionResponse:
        """Return one structured, NPC-readable perception."""
