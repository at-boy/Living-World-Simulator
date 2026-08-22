from dataclasses import dataclass, field

from living_world.core.belief import Belief
from living_world.core.entity import Entity
from living_world.core.event import Event
from living_world.core.experience import Experience
from living_world.core.knowledge import Knowledge
from living_world.core.memory import Memory
from living_world.core.npc_relationship import NPCRelationship
from living_world.core.observation import Observation
from living_world.core.relationship import Relationship
from living_world.core.run_metadata import RunMetadata
from living_world.external_world.dispatch import ExternalDispatch
from living_world.external_world.model import ExternalWorldReference
from living_world.goals.model import (
    GoalDefinition,
    GoalState,
    ObjectiveDefinition,
    ObjectiveState,
)
from living_world.needs.model import (
    ConsumptionPolicy,
    ConsumptionState,
    MaintenancePolicy,
    MaintenanceState,
    NeedDefinition,
    NeedState,
    StoragePolicy,
    StorageState,
)
from living_world.spatial.model import Placement
from living_world.work.model import WorkDefinition, WorkReservation, WorkState


@dataclass(slots=True)
class WorldState:
    """In-memory runtime snapshot owned and mutated through lifecycle managers."""

    tick: int = 0

    run_metadata: RunMetadata | None = None

    entities: dict[str, Entity] = field(default_factory=dict)

    relationships: dict[str, Relationship] = field(default_factory=dict)

    placements: dict[str, Placement] = field(default_factory=dict)

    external_world_references: dict[str, ExternalWorldReference] = field(
        default_factory=dict
    )

    external_dispatches: dict[str, ExternalDispatch] = field(default_factory=dict)

    goal_definitions: dict[str, GoalDefinition] = field(default_factory=dict)
    goal_states: dict[str, GoalState] = field(default_factory=dict)
    objective_definitions: dict[str, ObjectiveDefinition] = field(default_factory=dict)
    objective_states: dict[str, ObjectiveState] = field(default_factory=dict)

    need_definitions: dict[str, NeedDefinition] = field(default_factory=dict)
    need_states: dict[str, NeedState] = field(default_factory=dict)

    consumption_policies: dict[str, ConsumptionPolicy] = field(default_factory=dict)
    consumption_states: dict[str, ConsumptionState] = field(default_factory=dict)
    storage_policies: dict[str, StoragePolicy] = field(default_factory=dict)
    storage_states: dict[str, StorageState] = field(default_factory=dict)
    maintenance_policies: dict[str, MaintenancePolicy] = field(default_factory=dict)
    maintenance_states: dict[str, MaintenanceState] = field(default_factory=dict)

    work_definitions: dict[str, WorkDefinition] = field(default_factory=dict)
    work_states: dict[str, WorkState] = field(default_factory=dict)
    work_reservations: dict[str, WorkReservation] = field(default_factory=dict)

    events: dict[str, Event] = field(default_factory=dict)

    observations: dict[str, Observation] = field(default_factory=dict)

    beliefs: dict[str, Belief] = field(default_factory=dict)

    experiences: dict[str, Experience] = field(default_factory=dict)

    memories: dict[str, Memory] = field(default_factory=dict)

    npc_relationships: dict[str, NPCRelationship] = field(default_factory=dict)

    knowledge: dict[str, Knowledge] = field(default_factory=dict)
