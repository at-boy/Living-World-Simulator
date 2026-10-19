"""Canonical orchestration; existing managers retain all domain mutation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields

from living_world.core.resource_definition import ResourceDefinition
from living_world.external_world.manager import ExternalWorldReferenceManager
from living_world.external_world.model import ContactState
from living_world.goals.manager import GoalManager
from living_world.goals.model import (
    CapacityCriterion,
    ConstructedCapabilityCriterion,
    ExternalConnectionCriterion,
    GoalDefinition,
    GoalOwnerKind,
    MaintainedCapabilityCriterion,
    ObjectiveDefinition,
    PopulationMinimumCriterion,
    SustainedNeedCriterion,
)
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.managers.relationship_manager import RelationshipManager
from living_world.managers.resource_definition_manager import ResourceDefinitionManager
from living_world.needs.consequence import ConsequenceManager
from living_world.needs.manager import NeedManager
from living_world.needs.model import (
    ConsumptionPolicy,
    MaintenancePolicy,
    MaintenanceRequirement,
    NeedDefinition,
    NeedKind,
    StoragePolicy,
    StorageResourceRule,
)
from living_world.npc.identity import NPCIdentity
from living_world.spatial.manager import SpatialManager
from living_world.stages.manager import SettlementStageManager
from living_world.stages.model import (
    SettlementStage,
    SettlementStageDefinition,
    SettlementStageProgram,
    StageObjectiveRequirement,
    StageRequirementKind,
)
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem
from living_world.work.manager import WorkManager

from .model import (
    FoundersConfigurationError,
    FoundersPolicy,
    _canonical,
    canonical_policy,
)

_DOMAINS = (
    "need_definitions",
    "need_states",
    "goal_definitions",
    "goal_states",
    "objective_definitions",
    "objective_states",
    "consumption_policies",
    "consumption_states",
    "settlement_stage_programs",
    "settlement_stage_states",
    "external_world_references",
    "storage_policies",
    "storage_states",
    "maintenance_policies",
    "maintenance_states",
)


def _shadow(state: WorldState) -> WorldState:
    shadow = WorldState()
    for field in fields(WorldState):
        value = getattr(state, field.name)
        if field.name in {"entities", "relationships"}:
            value = deepcopy(value)
        elif isinstance(value, dict):
            value = dict(value)
        setattr(shadow, field.name, value)
    return shadow


def _commit(state: WorldState, staged: WorldState) -> None:
    for field in fields(WorldState):
        setattr(state, field.name, getattr(staged, field.name))


class FoundersSetupManager:
    def __init__(self, state: WorldState, definitions: DefinitionManager) -> None:
        self._state, self._definitions = state, definitions

    def _managers(
        self, state: WorldState
    ) -> tuple[
        EventManager, WorkManager, SpatialManager, EntityManager, ConsequenceManager
    ]:
        events = EventManager(state)
        work = WorkManager(state, events)
        spatial = SpatialManager(state, events, work)
        entities = EntityManager(state, self._definitions, spatial, work)
        return (
            events,
            work,
            spatial,
            entities,
            ConsequenceManager(state, ResourceSystem(), entities, events, work),
        )

    def _check_definitions(self, policy: FoundersPolicy) -> None:
        if _canonical(policy.to_manifest()) != _canonical(
            canonical_policy().to_manifest()
        ):
            raise ValueError
        definitions = self._definitions
        if tuple(d.key for d in definitions.all()) != (
            "area",
            "settlement",
            "founder",
            "shelter",
            "storage",
        ):
            raise ValueError
        expected = {
            "area": ((), {}),
            "settlement": (("production",), {}),
            "founder": ((), {}),
            "shelter": (
                ("housing",),
                {"housing_capacity": policy.rules.housing_capacity},
            ),
            "storage": ((), {"storage_capacity": policy.rules.storage_capacity}),
        }
        for key, (systems, attrs) in expected.items():
            definition = definitions.get(key)
            if definition.systems != systems or _canonical(
                definition.initial_attributes
            ) != _canonical(attrs):
                raise ValueError

    def _install(self, state: WorldState, policy: FoundersPolicy) -> None:
        events, _work, spatial, _entities, consequences = self._managers(state)
        r = policy.rules
        bindings = state.scenario_entity_bindings
        camp = bindings["camp"]
        for placement in policy.placements:
            spatial.place(
                entity_id=bindings[placement.label],
                geometry=placement.geometry,
                containing_entity_id=bindings.get(placement.containing_label or ""),
                bounds_kind=placement.bounds_kind,
                overlap_policy=placement.overlap_policy,
            )
        needs = NeedManager(state, events)
        for kind in NeedKind:
            needs.create(
                NeedDefinition(
                    "need_founders_" + kind.value,
                    camp,
                    kind,
                    r.need_requirement_per_person,
                    r.need_secure_maximum,
                    r.need_strained_maximum,
                    r.need_window_ticks,
                )
            )
        consequences.create_consumption(
            ConsumptionPolicy(
                "consumption_founders",
                camp,
                r.food_per_person_per_tick,
                r.water_per_person_per_tick,
            )
        )
        reference = ExternalWorldReferenceManager(state, events).create(
            name="The homeland",
            role="homeland",
            allowed_imports=r.homeland_allowed_imports,
            allowed_exports=r.homeland_allowed_exports,
            capacity=r.homeland_capacity,
            delay_ticks=r.homeland_delay_ticks,
            cost_per_unit=r.homeland_cost_per_unit,
            reliability=r.homeland_reliability,
            contact_state=ContactState.KNOWN,
        )
        criteria = {
            "water": (
                SustainedNeedCriterion(
                    "water", r.need_secure_maximum, r.need_duration_ticks
                ),
            ),
            "food": (
                SustainedNeedCriterion(
                    "food", r.need_secure_maximum, r.need_duration_ticks
                ),
            ),
            "shelter": (
                ConstructedCapabilityCriterion("shelter", r.modest_shelter_count),
                CapacityCriterion("housing", r.housing_capacity),
                SustainedNeedCriterion(
                    "shelter", r.need_secure_maximum, r.need_duration_ticks
                ),
            ),
            "storage": (
                ConstructedCapabilityCriterion("storage", r.storage_count),
                CapacityCriterion("storage", r.storage_capacity),
                SustainedNeedCriterion(
                    "storage", r.need_secure_maximum, r.need_duration_ticks
                ),
            ),
            "maintenance": (
                MaintainedCapabilityCriterion(
                    "shelter", r.modest_shelter_count, r.maintenance_minimum_condition
                ),
            ),
            "connection": (ExternalConnectionCriterion("homeland", "contactable"),),
            "population": (PopulationMinimumCriterion(r.town_population),),
        }
        categories = {
            "water": "gather_water",
            "food": "produce_food",
            "shelter": "build_shelter",
            "storage": "build_storage",
            "maintenance": "maintain_capability",
            "connection": "establish_external_trade_connection",
        }
        objectives = tuple(
            ObjectiveDefinition(
                "objective_founders_" + key,
                key.title(),
                "Establish a lasting home.",
                "Help the settlement become secure.",
                value,
                authorized_action_categories=(
                    ("settlement_work",)
                    if key not in categories
                    else (categories[key],)
                ),
            )
            for key, value in criteria.items()
        )
        goals = GoalManager(state, events)
        for name, items, deadline in (
            ("founding", objectives[:6], r.deadline_tick),
            ("growth", objectives[6:], None),
        ):
            goals.create(
                GoalDefinition(
                    "goal_" + name,
                    GoalOwnerKind.SETTLEMENT,
                    camp,
                    name.title(),
                    "Establish a lasting home.",
                    "Help the settlement become secure.",
                    tuple(x.id for x in items),
                    deadline_tick=deadline,
                    authorized_action_categories=("settlement_work",),
                ),
                items,
            )
        roles = (
            StageRequirementKind.WATER,
            StageRequirementKind.FOOD,
            StageRequirementKind.SHELTER,
            StageRequirementKind.STORAGE,
            StageRequirementKind.MAINTENANCE,
            StageRequirementKind.EXTERNAL_CONNECTION,
            StageRequirementKind.POPULATION,
        )
        requirements = tuple(
            StageObjectiveRequirement(role, obj.id)
            for role, obj in zip(roles, objectives)
        )
        SettlementStageManager(state, events).configure(
            SettlementStageProgram(
                camp,
                (
                    SettlementStageDefinition(SettlementStage.FOUNDING_CAMP, ()),
                    SettlementStageDefinition(
                        SettlementStage.SETTLEMENT, requirements[:6]
                    ),
                    SettlementStageDefinition(SettlementStage.TOWN, requirements),
                ),
            )
        )
        events.record(
            kind="canonical_setup_completed",
            subject_id=camp,
            attributes={
                "policy_version": policy.version,
                "policy_fingerprint": policy.fingerprint,
                "homeland_reference_id": reference.id,
            },
        )

    def initialize_or_validate(self, policy: FoundersPolicy) -> None:
        state = self._state
        if any(
            event.kind == "canonical_setup_completed" for event in state.events.values()
        ):
            self.validate_existing(policy)
            return
        try:
            self._check_definitions(policy)
            if (
                state.tick != 0
                or state.placements
                or any(getattr(state, key) for key in _DOMAINS)
                or state.work_definitions
                or state.work_states
                or state.work_reservations
                or state.external_dispatches
                or state.replay_binding is not None
                or state.replay_state is not None
                or tuple(state.scenario_entity_bindings)
                != ("valley", "camp", "ada", "bryn")
                or set(state.entities) != set(state.scenario_entity_bindings.values())
                or state.relationships
            ):
                raise ValueError
            camp = state.entities[state.scenario_entity_bindings["camp"]]
            if (
                _canonical(camp.attributes.get("resources"))
                != _canonical({"food": 0, "water": 0, "timber": 10})
                or type(camp.attributes.get("population")) is not int
                or camp.attributes["population"] != 2
                or _canonical(camp.attributes.get("production_inputs"))
                != _canonical({"food": 1})
                or _canonical(camp.attributes.get("production_outputs"))
                != _canonical({"food": 4, "water": 2})
            ):
                raise ValueError
            for name in ("housing_capacity", "storage_capacity"):
                if (
                    type(camp.attributes.get(name)) is not int
                    or camp.attributes[name] != 0
                ):
                    raise ValueError
            staged = _shadow(state)
            self._install(staged, policy)
            FoundersSetupManager(staged, self._definitions).validate_existing(policy)
        except (TypeError, ValueError, KeyError):
            raise FoundersConfigurationError("setup_mismatch") from None
        _commit(state, staged)

    def validate_existing(self, policy: FoundersPolicy) -> None:
        state = self._state
        try:
            self._check_definitions(policy)
            bindings = state.scenario_entity_bindings
            if set(bindings) != {"valley", "camp", "ada", "bryn"}:
                raise ValueError
            for label, key in (
                ("valley", "area"),
                ("camp", "settlement"),
                ("ada", "founder"),
                ("bryn", "founder"),
            ):
                entity = state.entities[bindings[label]]
                if entity.definition_key != key or entity.destroyed_tick is not None:
                    raise ValueError
                if label in policy.founder_labels:
                    NPCIdentity.from_attribute(entity.attributes.get("npc_identity"))
            if _canonical(
                state.entities[bindings["camp"]].attributes.get("founders_policy")
            ) != _canonical(policy.to_manifest()):
                raise ValueError
            expected = _shadow(state)
            expected.tick = 0
            expected.placements = {}
            expected.events = {}
            for key in _DOMAINS:
                setattr(expected, key, {})
            self._install(expected, policy)
            for key in (
                "need_definitions",
                "goal_definitions",
                "objective_definitions",
                "consumption_policies",
                "settlement_stage_programs",
            ):
                if getattr(state, key) != getattr(expected, key):
                    raise ValueError
            for key in (
                "need_states",
                "goal_states",
                "objective_states",
                "consumption_states",
                "settlement_stage_states",
            ):
                partner = {
                    "need_states": "need_definitions",
                    "goal_states": "goal_definitions",
                    "objective_states": "objective_definitions",
                    "consumption_states": "consumption_policies",
                    "settlement_stage_states": "settlement_stage_programs",
                }[key]
                if set(getattr(state, key)) != set(getattr(expected, partner)):
                    raise ValueError
            refs = tuple(state.external_world_references.values())
            wanted = next(iter(expected.external_world_references.values()))
            if len(refs) != 1 or any(
                getattr(refs[0], field.name) != getattr(wanted, field.name)
                for field in fields(wanted)
                if field.name != "contact_state"
            ):
                raise ValueError
            markers = [
                event
                for event in state.events.values()
                if event.kind == "canonical_setup_completed"
            ]
            wanted_marker = next(
                event
                for event in expected.events.values()
                if event.kind == "canonical_setup_completed"
            )
            if (
                len(markers) != 1
                or markers[0].tick != 0
                or markers[0].subject_id != wanted_marker.subject_id
                or _canonical(dict(markers[0].attributes))
                != _canonical(dict(wanted_marker.attributes))
            ):
                raise ValueError
            for key, value in expected.placements.items():
                if state.placements.get(key) != value:
                    raise ValueError
            events, work, spatial, _entities, consequences = self._managers(state)
            spatial.validate_loaded_state()
            work.validate_loaded_state()
            NeedManager(state, events).validate_loaded_state()
            GoalManager(state, events).validate_loaded_state()
            SettlementStageManager(state, events).validate_loaded_state()
            consequences.validate_loaded_state()
            self._attachments(state, policy, create=False)
        except (TypeError, ValueError, KeyError):
            raise FoundersConfigurationError("setup_mismatch") from None

    def _attachments(
        self, state: WorldState, policy: FoundersPolicy, *, create: bool
    ) -> None:
        r = policy.rules
        camp = state.scenario_entity_bindings["camp"]
        occupants = tuple(
            state.scenario_entity_bindings[x] for x in policy.founder_labels
        )
        owned = {
            rel.target_id
            for rel in state.relationships.values()
            if rel.kind == "owns"
            and rel.source_id == camp
            and rel.destroyed_tick is None
            and rel.created_tick <= state.tick
            and rel.target_id != camp
        }
        capabilities = sorted(
            (
                entity
                for entity in state.entities.values()
                if entity.id in owned
                and entity.destroyed_tick is None
                and entity.attributes.get("is_constructed") is True
            ),
            key=lambda entity: entity.id,
        )
        events, _work, _spatial, entities, consequences = self._managers(state)
        relationships = RelationshipManager(state, entities)
        maintenance_ids = set()
        shelter_ids = set()
        for entity in capabilities:
            if entity.definition_key != "shelter":
                continue
            shelter_ids.add(entity.id)
            pid = "maintenance_founders_" + entity.id
            expected = MaintenancePolicy(
                pid,
                camp,
                entity.id,
                "Founders shelter",
                (MaintenanceRequirement("food", r.maintenance_food_upkeep),),
                r.maintenance_initial_condition,
                r.maintenance_maximum_condition,
                r.maintenance_deterioration,
                r.maintenance_recovery,
            )
            attrs = {
                "settlement_id": camp,
                "occupant_ids": occupants,
                "maintenance_policy_id": pid,
            }
            markers = [
                e
                for e in state.events.values()
                if e.kind == "founders_shelter_composed" and e.subject_id == entity.id
            ]
            edges = [
                rel
                for rel in state.relationships.values()
                if rel.kind == "housed_in" and rel.target_id == entity.id
            ]
            present = bool(
                markers
                or edges
                or pid in state.maintenance_policies
                or pid in state.maintenance_states
            )
            if present:
                if (
                    state.maintenance_policies.get(pid) != expected
                    or pid not in state.maintenance_states
                    or len(markers) != 1
                    or type(markers[0].tick) is not int
                    or markers[0].tick != entity.created_tick + 1
                    or markers[0].tick > state.tick
                    or dict(markers[0].attributes) != attrs
                    or len(edges) != 2
                    or {edge.source_id for edge in edges} != set(occupants)
                ):
                    raise ValueError
                maintenance_ids.add(pid)
            else:
                if state.tick > entity.created_tick + 1:
                    raise ValueError
                if create:
                    for actor in occupants:
                        relationships.create(
                            kind="housed_in", source_id=actor, target_id=entity.id
                        )
                    consequences.create_maintenance(expected)
                    events.record(
                        kind="founders_shelter_composed",
                        subject_id=entity.id,
                        attributes=attrs,
                    )
                    maintenance_ids.add(pid)
        if (
            set(state.maintenance_policies) != maintenance_ids
            or set(state.maintenance_states) != maintenance_ids
        ):
            raise ValueError
        if any(
            e.kind == "founders_shelter_composed" and e.subject_id not in shelter_ids
            for e in state.events.values()
        ):
            raise ValueError
        storages = [
            entity for entity in capabilities if entity.definition_key == "storage"
        ]
        markers = [
            e for e in state.events.values() if e.kind == "founders_storage_composed"
        ]
        expected_storage = StoragePolicy(
            "storage_founders",
            camp,
            tuple(
                StorageResourceRule(name, r.storage_spoilage_per_tick)
                for name in ("food", "water")
            ),
        )
        present = bool(state.storage_policies or state.storage_states or markers)
        if present:
            if (
                not storages
                or state.storage_policies != {"storage_founders": expected_storage}
                or set(state.storage_states) != {"storage_founders"}
                or len(markers) != 1
                or type(markers[0].tick) is not int
                or markers[0].tick != storages[0].created_tick + 1
                or markers[0].tick > state.tick
                or markers[0].subject_id != storages[0].id
                or dict(markers[0].attributes)
                != {"settlement_id": camp, "storage_policy_id": "storage_founders"}
            ):
                raise ValueError
        elif storages:
            if state.tick > storages[0].created_tick + 1:
                raise ValueError
            if create:
                consequences.create_storage(expected_storage)
                events.record(
                    kind="founders_storage_composed",
                    subject_id=storages[0].id,
                    attributes={
                        "settlement_id": camp,
                        "storage_policy_id": "storage_founders",
                    },
                )

    def compose(self, policy: FoundersPolicy) -> None:
        self.validate_existing(policy)
        staged = _shadow(self._state)
        try:
            self._attachments(staged, policy, create=True)
            FoundersSetupManager(staged, self._definitions).validate_existing(policy)
        except (TypeError, ValueError, KeyError):
            raise FoundersConfigurationError("setup_mismatch") from None
        _commit(self._state, staged)

    def restore_resource_vocabulary(
        self, policy: FoundersPolicy, registry: ResourceDefinitionManager
    ) -> None:
        self.validate_existing(policy)
        for name in ("food", "water", "timber"):
            registry.register(ResourceDefinition(name))
