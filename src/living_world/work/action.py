"""Actor-bound gateway for engine-authored work proposals."""

from __future__ import annotations

from dataclasses import dataclass

from living_world.cognition.action_resolution import ActionResolution
from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.npc_cognition_client import ActionOption, ActionRequest
from living_world.goals.model import GoalOwnerKind, GoalStatus
from living_world.managers.definition_manager import DefinitionManager
from living_world.npc.identity import NPCIdentity
from living_world.state.world_state import WorldState
from living_world.work.manager import WorkManager
from living_world.work.model import (
    CapabilityWorkTarget,
    ExternalConnectionWorkTarget,
    MaintenanceWorkTarget,
    ResourceRequirement,
    ResourceWorkTarget,
    ToolRequirement,
    WorkCategory,
    WorkDefinition,
    WorkTarget,
    integer,
    text,
    visible_text,
)

PRIORITIZE_WORK_ACTION_KEY = "prioritize_work"
VOLUNTEER_FOR_WORK_ACTION_KEY = "volunteer_for_work"

_ACTION_DESCRIPTIONS = {
    WorkCategory.GATHER_WATER.value: "Propose gathering water for the settlement.",
    WorkCategory.PRODUCE_FOOD.value: "Propose producing food for the settlement.",
    WorkCategory.BUILD_SHELTER.value: "Propose building shelter for the settlement.",
    WorkCategory.BUILD_STORAGE.value: "Propose building storage for the settlement.",
    WorkCategory.MAINTAIN_CAPABILITY.value: (
        "Propose maintaining a settlement capability."
    ),
    WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION.value: (
        "Propose establishing an external trade connection."
    ),
    PRIORITIZE_WORK_ACTION_KEY: (
        "Propose changing the priority of one offered work order."
    ),
    VOLUNTEER_FOR_WORK_ACTION_KEY: "Volunteer for one offered work order.",
}
_ACTION_KEYS = tuple(category.value for category in WorkCategory) + (
    PRIORITIZE_WORK_ACTION_KEY,
    VOLUNTEER_FOR_WORK_ACTION_KEY,
)
_TARGET_TYPES = (
    ResourceWorkTarget,
    CapabilityWorkTarget,
    MaintenanceWorkTarget,
    ExternalConnectionWorkTarget,
)


@dataclass(frozen=True, slots=True)
class WorkCreationOffer:
    """Complete hidden manager policy behind one qualitative creation label."""

    label: str
    category: WorkCategory
    target: WorkTarget
    settlement_id: str
    objective_id: str
    location_id: str
    prerequisite_work_ids: tuple[str, ...] = ()
    labor_required: int = 0
    tools: tuple[ToolRequirement, ...] = ()
    resources: tuple[ResourceRequirement, ...] = ()
    required_progress: int = 1
    priority: int = 0
    deadline_tick: int | None = None

    def __post_init__(self) -> None:
        visible_text(self.label, "label")
        if not isinstance(self.category, WorkCategory):
            raise TypeError("category must be a WorkCategory.")
        if type(self.target) not in _TARGET_TYPES:
            raise TypeError("target must be a work target.")
        target_types = {
            WorkCategory.GATHER_WATER: ResourceWorkTarget,
            WorkCategory.PRODUCE_FOOD: ResourceWorkTarget,
            WorkCategory.BUILD_SHELTER: CapabilityWorkTarget,
            WorkCategory.BUILD_STORAGE: CapabilityWorkTarget,
            WorkCategory.MAINTAIN_CAPABILITY: MaintenanceWorkTarget,
            WorkCategory.ESTABLISH_EXTERNAL_TRADE_CONNECTION: (
                ExternalConnectionWorkTarget
            ),
        }
        if type(self.target) is not target_types[self.category]:
            raise ValueError("Work category and target type do not match.")
        if isinstance(self.target, ResourceWorkTarget):
            expected = "water" if self.category is WorkCategory.GATHER_WATER else "food"
            if self.target.resource != expected:
                raise ValueError("Resource target does not match category.")
        for value, name in (
            (self.settlement_id, "settlement_id"),
            (self.objective_id, "objective_id"),
            (self.location_id, "location_id"),
        ):
            text(value, name)
        integer(self.labor_required, "labor_required")
        integer(self.required_progress, "required_progress", 1)
        integer(self.priority, "priority")
        if self.deadline_tick is not None:
            integer(self.deadline_tick, "deadline_tick")
        _canonical_tuple(self.prerequisite_work_ids, str, "prerequisite_work_ids")
        _canonical_requirements(self.tools, ToolRequirement, "tools", "tool")
        _canonical_requirements(
            self.resources, ResourceRequirement, "resources", "resource"
        )
        if {item.tool for item in self.tools}.intersection(
            item.resource for item in self.resources
        ):
            raise ValueError("Tool and resource names cannot overlap.")


@dataclass(frozen=True, slots=True)
class WorkPriorityOffer:
    """One fixed priority change hidden behind a qualitative label."""

    label: str
    work_id: str
    priority: int

    def __post_init__(self) -> None:
        visible_text(self.label, "label")
        text(self.work_id, "work_id")
        integer(self.priority, "priority")


@dataclass(frozen=True, slots=True)
class WorkAssignmentOffer:
    """One actor-bound self-assignment hidden behind a qualitative label."""

    label: str
    work_id: str

    def __post_init__(self) -> None:
        visible_text(self.label, "label")
        text(self.work_id, "work_id")


WorkOffer = WorkCreationOffer | WorkPriorityOffer | WorkAssignmentOffer


class WorkActionHandler:
    """Resolve offered labels to one authoritative WorkManager mutation."""

    def __init__(
        self,
        state: WorldState,
        definitions: DefinitionManager,
        manager: WorkManager,
        actor_id: str,
        creation_offers: tuple[WorkCreationOffer, ...] = (),
        priority_offers: tuple[WorkPriorityOffer, ...] = (),
        assignment_offers: tuple[WorkAssignmentOffer, ...] = (),
    ) -> None:
        if not isinstance(state, WorldState):
            raise TypeError("state must be a WorldState.")
        if not isinstance(definitions, DefinitionManager):
            raise TypeError("definitions must be a DefinitionManager.")
        if not isinstance(manager, WorkManager):
            raise TypeError("manager must be a WorkManager.")
        text(actor_id, "actor_id")
        _offer_tuple(creation_offers, WorkCreationOffer, "creation_offers")
        _offer_tuple(priority_offers, WorkPriorityOffer, "priority_offers")
        _offer_tuple(assignment_offers, WorkAssignmentOffer, "assignment_offers")
        if not creation_offers and not priority_offers and not assignment_offers:
            raise ValueError("At least one work offer is required.")

        self._state = state
        self._definitions = definitions
        self._manager = manager
        self._actor_id = actor_id
        self._offers: dict[tuple[str, str], WorkOffer] = {}
        self._last_created: WorkDefinition | None = None

        duplicate_creation: set[tuple[object, ...]] = set()
        duplicate_priority: set[str] = set()
        duplicate_assignment: set[str] = set()
        for offer in creation_offers:
            identity = self._creation_identity(offer)
            if identity in duplicate_creation:
                raise ValueError("Creation offers must have unique work identities.")
            duplicate_creation.add(identity)
            self._add_offer(offer.category.value, offer)
        for offer in priority_offers:
            if offer.work_id in duplicate_priority:
                raise ValueError("Priority offers must identify unique work orders.")
            duplicate_priority.add(offer.work_id)
            self._add_offer(PRIORITIZE_WORK_ACTION_KEY, offer)
        for offer in assignment_offers:
            if offer.work_id in duplicate_assignment:
                raise ValueError("Assignment offers must identify unique work orders.")
            duplicate_assignment.add(offer.work_id)
            self._add_offer(VOLUNTEER_FOR_WORK_ACTION_KEY, offer)

        # Construction is deliberately state-aware: stale offers are rejected now
        # and then checked again at validation and application.
        for (key, _), offer in self._offers.items():
            self._preflight(key, offer)

        boundary = NPCInformationBoundary(state)
        options: list[ActionOption] = []
        for key in _ACTION_KEYS:
            labels = tuple(
                sorted(
                    (label for offer_key, label in self._offers if offer_key == key),
                    key=lambda value: (value.strip().casefold(), value),
                )
            )
            if labels:
                boundary.validate_conversation_prose(_ACTION_DESCRIPTIONS[key])
                for label in labels:
                    boundary.validate_conversation_prose(label)
                options.append(ActionOption(key, _ACTION_DESCRIPTIONS[key], labels))
        self._action_options = tuple(options)

    @property
    def action_options(self) -> tuple[ActionOption, ...]:
        return self._action_options

    @property
    def last_created(self) -> WorkDefinition | None:
        return self._last_created

    def supports(self, action_key: str) -> bool:
        return any(option.key == action_key for option in self._action_options)

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        offer = self._offers.get((request.action_key, request.target_label or ""))
        if request.arguments:
            return ActionResolution(False, "Work proposals cannot set engine policy.")
        if offer is None:
            return ActionResolution(False, self._rejection(request.action_key))
        try:
            self._require_actor(actor_id, self._settlement_id(offer))
            self._preflight(request.action_key, offer)
        except (TypeError, ValueError, KeyError):
            return ActionResolution(False, self._rejection(request.action_key))
        return ActionResolution(True, "Work proposal is valid.")

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        offer = self._offers[(request.action_key, request.target_label or "")]
        self._require_actor(actor_id, self._settlement_id(offer))
        self._preflight(request.action_key, offer)
        if isinstance(offer, WorkCreationOffer):
            created = self._manager.create(
                category=offer.category,
                target=offer.target,
                public_label=offer.label,
                settlement_id=offer.settlement_id,
                objective_id=offer.objective_id,
                location_id=offer.location_id,
                prerequisite_work_ids=offer.prerequisite_work_ids,
                labor_required=offer.labor_required,
                tools=offer.tools,
                resources=offer.resources,
                required_progress=offer.required_progress,
                priority=offer.priority,
                deadline_tick=offer.deadline_tick,
            )
            self._last_created = created
            return ActionResolution(True, "The work proposal was accepted.")
        if isinstance(offer, WorkPriorityOffer):
            self._manager.set_priority(offer.work_id, offer.priority)
            return ActionResolution(True, "The work priority proposal was accepted.")
        self._manager.assign_and_reserve(offer.work_id, (actor_id,))
        return ActionResolution(True, "The volunteer proposal was accepted.")

    def _add_offer(self, key: str, offer: WorkOffer) -> None:
        normalized = offer.label.strip().casefold()
        if any(
            existing_key == key and existing_label.strip().casefold() == normalized
            for existing_key, existing_label in self._offers
        ):
            raise ValueError("Offer labels must be unambiguous within an action key.")
        self._offers[(key, offer.label)] = offer

    def _preflight(self, key: str, offer: WorkOffer) -> None:
        settlement_id, objective_id, category = self._operation_context(offer)
        self._require_actor(self._actor_id, settlement_id)
        self._authorize(settlement_id, objective_id, category)
        if isinstance(offer, WorkCreationOffer):
            if isinstance(
                offer.target, CapabilityWorkTarget
            ) and not self._definitions.exists(offer.target.definition_key):
                raise ValueError("Capability definition is unknown.")
            self._manager.validate_create(
                category=offer.category,
                target=offer.target,
                public_label=offer.label,
                settlement_id=offer.settlement_id,
                objective_id=offer.objective_id,
                location_id=offer.location_id,
                prerequisite_work_ids=offer.prerequisite_work_ids,
                labor_required=offer.labor_required,
                tools=offer.tools,
                resources=offer.resources,
                required_progress=offer.required_progress,
                priority=offer.priority,
                deadline_tick=offer.deadline_tick,
                require_available_inputs=True,
                reject_nonterminal_duplicate=True,
            )
            return
        if isinstance(offer, WorkPriorityOffer):
            self._manager.validate_set_priority(offer.work_id, offer.priority)
            return
        definition = self._manager.get(offer.work_id)
        if definition is None or definition.labor_required != 1:
            raise ValueError("Volunteer work must require one laborer.")
        self._manager.validate_assign_and_reserve(offer.work_id, (self._actor_id,))

    def _authorize(
        self, settlement_id: str, objective_id: str, category: WorkCategory
    ) -> None:
        goals = tuple(
            goal
            for goal in self._state.goal_definitions.values()
            if objective_id in goal.objective_ids
        )
        if len(goals) != 1:
            raise ValueError("Objective ownership is invalid.")
        goal = goals[0]
        objective = self._state.objective_definitions.get(objective_id)
        goal_state = self._state.goal_states.get(goal.id)
        objective_state = self._state.objective_states.get(objective_id)
        if (
            goal.owner_kind is not GoalOwnerKind.SETTLEMENT
            or goal.owner_id != settlement_id
            or objective is None
            or goal_state is None
            or objective_state is None
            or goal_state.status is not GoalStatus.ACTIVE
            or objective_state.status is not GoalStatus.ACTIVE
            or "settlement_work" not in goal.authorized_action_categories
            or category.value not in objective.authorized_action_categories
        ):
            raise ValueError("Work is not authorized by an active objective.")

    def _require_actor(self, actor_id: str, settlement_id: str) -> None:
        if actor_id != self._actor_id:
            raise ValueError("Actor does not own this handler.")
        entity = self._state.entities.get(actor_id)
        if entity is None or entity.destroyed_tick is not None:
            raise ValueError("Actor must be live.")
        NPCIdentity.from_attribute(entity.attributes.get("npc_identity"))
        if any(
            policy.capability_id == actor_id
            for policy in self._state.maintenance_policies.values()
        ):
            raise ValueError("Maintenance capabilities cannot propose work.")
        if not self._inside(actor_id, settlement_id):
            raise ValueError("Actor must be within the settlement.")

    def _inside(self, entity_id: str, settlement_id: str) -> bool:
        current: str | None = entity_id
        seen: set[str] = set()
        while current is not None and current not in seen:
            if current == settlement_id:
                return current in self._state.placements
            seen.add(current)
            placement = self._state.placements.get(current)
            if placement is None or placement.geometry is None:
                return False
            current = placement.containing_entity_id
        return False

    def _operation_context(self, offer: WorkOffer) -> tuple[str, str, WorkCategory]:
        if isinstance(offer, WorkCreationOffer):
            return offer.settlement_id, offer.objective_id, offer.category
        definition = self._manager.get(offer.work_id)
        if definition is None:
            raise ValueError("Work order is unknown.")
        return definition.settlement_id, definition.objective_id, definition.category

    def _settlement_id(self, offer: WorkOffer) -> str:
        return self._operation_context(offer)[0]

    @staticmethod
    def _creation_identity(offer: WorkCreationOffer) -> tuple[object, ...]:
        return (
            offer.settlement_id,
            offer.objective_id,
            offer.category,
            offer.target,
            offer.location_id,
        )

    @staticmethod
    def _rejection(action_key: str) -> str:
        if action_key in {category.value for category in WorkCategory}:
            return "That work proposal is not currently available."
        if action_key == PRIORITIZE_WORK_ACTION_KEY:
            return "That priority proposal is not currently available."
        return "That volunteer proposal is not currently available."


def _offer_tuple(value: object, expected: type, name: str) -> None:
    if not isinstance(value, tuple) or any(
        type(item) is not expected for item in value
    ):
        raise TypeError(f"{name} must be a tuple of {expected.__name__} values.")


def _canonical_tuple(value: object, expected: type, name: str) -> None:
    if not isinstance(value, tuple) or any(
        type(item) is not expected for item in value
    ):
        raise TypeError(f"{name} must be a tuple of {expected.__name__} values.")
    for item in value:
        text(item, name)
    if value != tuple(sorted(value)) or len(value) != len(set(value)):
        raise ValueError(f"{name} must be unique and sorted.")


def _canonical_requirements(
    value: object, expected: type, name: str, attribute: str
) -> None:
    if not isinstance(value, tuple) or any(
        type(item) is not expected for item in value
    ):
        raise TypeError(f"{name} must be a tuple of {expected.__name__} values.")
    keys = tuple(getattr(item, attribute) for item in value)
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        raise ValueError(f"{name} must be unique and sorted.")
