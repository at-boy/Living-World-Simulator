"""Consumption, storage, maintenance, inspection, and safe interpretation."""

from living_world.api.inspection import EngineWorldInspector
from living_world.core.definition import Definition
from living_world.needs import (
    ConsumptionPolicy,
    MaintenancePolicy,
    MaintenanceRequirement,
    NeedDefinition,
    NeedKind,
    StoragePolicy,
    StorageResourceRule,
)
from living_world.simulation.simulation_engine import SimulationEngine

engine = SimulationEngine()
engine.definitions.register(Definition("settlement"))
owner = engine.entities.create(
    definition_key="settlement",
    name="Harbor",
    attributes={
        "population": 2,
        "resources": {"food": 8, "water": 6, "wood": 1},
        "storage_capacity": 8,
    },
)
well = engine.entities.create(
    definition_key="settlement", name="Well", attributes={"is_constructed": True}
)
engine.relationships.create(kind="owns", source_id=owner.id, target_id=well.id)
engine.needs.create(
    NeedDefinition("need_food", owner.id, NeedKind.FOOD, 1, 0.2, 0.5, 3)
)
engine.consequences.create_consumption(
    ConsumptionPolicy("consumption_harbor", owner.id, 1, 1)
)
engine.consequences.create_storage(
    StoragePolicy(
        "storage_harbor",
        owner.id,
        (StorageResourceRule("food", 1), StorageResourceRule("water", 0)),
    )
)
engine.consequences.create_maintenance(
    MaintenancePolicy(
        "maintenance_well",
        owner.id,
        well.id,
        "Village well",
        (MaintenanceRequirement("wood", 1),),
        2,
        3,
        1,
        1,
    )
)
for _ in range(2):
    engine.step()
inspector = EngineWorldInspector(engine)
print("resources", engine.state.entities[owner.id].attributes["resources"])
print("consequences", inspector.consequences())
print("need", inspector.needs())
print("events", inspector.events())
print(
    "npc safe",
    tuple(
        engine.consequences.npc_interpretation(key)
        for key in ("consumption_harbor", "storage_harbor", "maintenance_well")
    ),
)
