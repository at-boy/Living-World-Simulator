from living_world.work.model import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    NPCWorkInterpretation,
    ResourceRequirement,
    ResourceWorkTarget,
    ToolRequirement,
    WorkCategory,
    WorkDefinition,
    WorkReservation,
    WorkState,
    WorkStatus,
)

__all__ = [
    "PRIORITIZE_WORK_ACTION_KEY",
    "VOLUNTEER_FOR_WORK_ACTION_KEY",
    "CapabilityWorkTarget",
    "ExternalConnectionWorkTarget",
    "MaintenanceWorkTarget",
    "NPCWorkInterpretation",
    "ResourceRequirement",
    "ResourceWorkTarget",
    "ToolRequirement",
    "WorkActionHandler",
    "WorkAssignmentOffer",
    "WorkCategory",
    "WorkCreationOffer",
    "WorkDefinition",
    "WorkPriorityOffer",
    "WorkReservation",
    "WorkState",
    "WorkStatus",
]


def __getattr__(name: str) -> object:
    if name in {
        "PRIORITIZE_WORK_ACTION_KEY",
        "VOLUNTEER_FOR_WORK_ACTION_KEY",
        "WorkActionHandler",
        "WorkAssignmentOffer",
        "WorkCreationOffer",
        "WorkPriorityOffer",
    }:
        from living_world.work import action

        return getattr(action, name)
    raise AttributeError(name)
