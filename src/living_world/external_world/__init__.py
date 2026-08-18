from living_world.external_world.model import (
    ContactState,
    ExternalWorldReference,
    NPCExternalReference,
)

__all__ = [
    "ContactState",
    "ExternalWorldReference",
    "ExternalWorldReferenceManager",
    "NPCExternalReference",
]


def __getattr__(name: str) -> object:
    if name == "ExternalWorldReferenceManager":
        from living_world.external_world.manager import ExternalWorldReferenceManager

        return ExternalWorldReferenceManager
    raise AttributeError(name)
