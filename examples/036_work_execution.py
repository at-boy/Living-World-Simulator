"""Demonstrate deterministic manager-owned work execution."""

from living_world.core.definition import Definition
from living_world.goals import (
    GoalDefinition,
    GoalOwnerKind,
    ObjectiveDefinition,
    ResourceMinimumCriterion,
)
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.spatial import Bounds, BoundsKind, Point
from living_world.work import ResourceRequirement, ResourceWorkTarget, WorkCategory

engine = SimulationEngine()
for key in ("settlement", "npc"):
    engine.definitions.register(Definition(key))
settlement = engine.entities.create(
    definition_key="settlement", name="Oakford", attributes={"resources": {"seed": 2}}
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
    entity_id=settlement.id, geometry=Bounds(0, 0, 8, 8), bounds_kind=BoundsKind.AREA
)
engine.spatial.place(
    entity_id=worker.id, geometry=Point(1, 1), containing_entity_id=settlement.id
)
objective = ObjectiveDefinition(
    "objective_food",
    "Produce food",
    "Produce food",
    "Secure food.",
    (ResourceMinimumCriterion("food", 5),),
    authorized_action_categories=("produce_food",),
)
engine.goals.create(
    GoalDefinition(
        "goal_home",
        GoalOwnerKind.SETTLEMENT,
        settlement.id,
        "Found a home",
        "Found a home",
        "Help the settlement thrive.",
        (objective.id,),
        authorized_action_categories=("settlement_work",),
    ),
    (objective,),
)
work = engine.work.create(
    category=WorkCategory.PRODUCE_FOOD,
    target=ResourceWorkTarget("food", 5),
    public_label="Plant a crop",
    settlement_id=settlement.id,
    objective_id=objective.id,
    location_id=settlement.id,
    labor_required=1,
    resources=(ResourceRequirement("seed", 2),),
    required_progress=2,
)
engine.run(2)
print("Work:", engine.work.npc_interpretation(work.id).description)
print("Resources:", engine.state.entities[settlement.id].attributes["resources"])
