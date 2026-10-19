from living_world.external_world.dispatch import (
    DispatchDirection,
    DispatchStatus,
    ExternalDispatch,
    NPCDispatchPerception,
)
from living_world.external_world.model import (
    ContactState,
    ExternalWorldReference,
    NPCExternalReference,
)

__all__ = [
    "DISPATCH_ACTION_KEY",
    "ContactState",
    "DispatchDirection",
    "DispatchOffer",
    "DispatchStatus",
    "ExternalDispatch",
    "ExternalDispatchActionHandler",
    "ExternalDispatchManager",
    "ExternalDispatchSystem",
    "ExternalWorldReference",
    "ExternalWorldReferenceManager",
    "NPCDispatchPerception",
    "NPCExternalReference",
]


def __getattr__(name: str) -> object:
    if name == "ExternalWorldReferenceManager":
        from living_world.external_world.manager import ExternalWorldReferenceManager

        return ExternalWorldReferenceManager
    if name == "ExternalDispatchManager":
        from living_world.external_world.dispatch_manager import ExternalDispatchManager

        return ExternalDispatchManager
    if name == "ExternalDispatchSystem":
        from living_world.external_world.dispatch_system import ExternalDispatchSystem

        return ExternalDispatchSystem
    if name in {
        "DISPATCH_ACTION_KEY",
        "DispatchOffer",
        "ExternalDispatchActionHandler",
    }:
        from living_world.external_world import dispatch_action

        return getattr(dispatch_action, name)
    raise AttributeError(name)
