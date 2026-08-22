"""Demonstrate a label-only NPC work proposal through simulation authority."""

from living_world.cognition import ActionRequest, NPCActionResolver, NPCContextAssembler
from living_world.core.definition import Definition
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    GoalStatus,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point
from living_world.work import (
    ResourceRequirement,
    ResourceWorkTarget,
    WorkActionHandler,
    WorkCategory,
    WorkCreationOffer,
    WorkStatus,
)

engine = SimulationEngine()
for definition_key in ("settlement", "npc"):
    engine.definitions.register(Definition(definition_key))
settlement = engine.entities.create(
    definition_key="settlement",
    name="Oakford",
    attributes={"resources": {"seed": 3}},
)
worker = engine.entities.create(
    definition_key="npc",
    name="Mara",
    attributes={
        "npc_identity": {
            "name": "Mara",
            "description": "A farmer.",
            "capability_descriptions": [],
        }
    },
)
engine.spatial.place(
    entity_id=settlement.id,
    geometry=Bounds(0, 0, 8, 8),
    bounds_kind=BoundsKind.AREA,
)
engine.spatial.place(
    entity_id=worker.id,
    geometry=Point(1, 1),
    containing_entity_id=settlement.id,
)
objective = ObjectiveDefinition(
    "objective_food",
    "Produce food",
    "Produce food",
    "Secure a dependable food supply.",
    (ResourceMinimumCriterion("food", 5),),
    authorized_action_categories=(WorkCategory.PRODUCE_FOOD.value,),
)
goal = GoalDefinition(
    "goal_home",
    GoalOwnerKind.SETTLEMENT,
    settlement.id,
    "Found a home",
    "Found a home",
    "Help the settlement thrive.",
    (objective.id,),
    authorized_action_categories=("settlement_work",),
)
engine.goals.create(goal, (objective,))
engine.goals.transition_goal(goal.id, GoalStatus.ACTIVE)
engine.goals.transition_objective(objective.id, GoalStatus.ACTIVE)

context = NPCContextAssembler(engine.state).assemble(
    holder_id=worker.id,
    capability_descriptions=("I can help establish crops.",),
)
offer = WorkCreationOffer(
    label="Plant the first crop",
    category=WorkCategory.PRODUCE_FOOD,
    target=ResourceWorkTarget("food", 5),
    settlement_id=settlement.id,
    objective_id=objective.id,
    location_id=settlement.id,
    labor_required=1,
    resources=(ResourceRequirement("seed", 2),),
    required_progress=2,
)
handler = WorkActionHandler(
    engine.state,
    engine.definitions,
    engine.work,
    worker.id,
    creation_offers=(offer,),
)
resolver = NPCActionResolver(handler.action_options, (handler,))
proposal = ActionRequest(
    action_key=WorkCategory.PRODUCE_FOOD.value,
    target_label="Plant the first crop",
    rationale="A crop could help the settlement.",
)
resolution = resolver.resolve(actor_id=worker.id, request=proposal)

created = handler.last_created
assert resolution.accepted and created is not None
assert engine.state.work_states[created.id].status is WorkStatus.PROPOSED
assert engine.state.work_reservations == {}
assert settlement.attributes["resources"] == {"seed": 3}
print("Filtered context:", context)
print("Safe offered actions:", handler.action_options)
print("Gateway result:", resolution.reason)
print("Created work remains proposed:", created.public_label)
