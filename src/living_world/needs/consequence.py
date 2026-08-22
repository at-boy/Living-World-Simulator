from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Protocol

from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.needs.model import (
    ConsumptionPolicy,
    ConsumptionState,
    MaintenancePolicy,
    MaintenanceState,
    NPCConsequenceInterpretation,
    StoragePolicy,
    StorageState,
)
from living_world.needs.system import owned_capacity
from living_world.state.world_state import WorldState
from living_world.systems.resource_system import ResourceSystem


class WorkMaintenanceGuard(Protocol):
    def validate_maintenance_target(self, entity_id: str) -> None: ...


class ConsequenceManager:
    def __init__(
        self,
        state: WorldState,
        resources: ResourceSystem,
        entities: EntityManager,
        events: EventManager,
        work_guard: WorkMaintenanceGuard | None = None,
    ) -> None:
        self._state, self._resources, self._entities, self._events = (
            state,
            resources,
            entities,
            events,
        )
        self._work_guard = work_guard

    def create_consumption(self, policy: ConsumptionPolicy) -> ConsumptionPolicy:
        if type(policy) is not ConsumptionPolicy:
            raise TypeError("policy must be a ConsumptionPolicy.")
        self._live(policy.owner_id)
        self._not_capability(policy.owner_id)
        if policy.id in self._state.consumption_policies or any(
            p.owner_id == policy.owner_id
            for p in self._state.consumption_policies.values()
        ):
            raise ValueError("Consumption policy id and owner must be unique.")
        return self._create(
            "consumption",
            policy,
            ConsumptionState(policy.id),
            {
                "owner_id": policy.owner_id,
                "food_per_person_per_tick": policy.food_per_person_per_tick,
                "water_per_person_per_tick": policy.water_per_person_per_tick,
            },
        )

    def create_storage(self, policy: StoragePolicy) -> StoragePolicy:
        if type(policy) is not StoragePolicy:
            raise TypeError("policy must be a StoragePolicy.")
        self._live(policy.owner_id)
        self._not_capability(policy.owner_id)
        if policy.id in self._state.storage_policies or any(
            p.owner_id == policy.owner_id for p in self._state.storage_policies.values()
        ):
            raise ValueError("Storage policy id and owner must be unique.")
        rules = tuple(
            {"resource": r.resource, "spoilage_per_tick": r.spoilage_per_tick}
            for r in policy.resources
        )
        return self._create(
            "storage",
            policy,
            StorageState(policy.id),
            {"owner_id": policy.owner_id, "resources": rules},
        )

    def create_maintenance(self, policy: MaintenancePolicy) -> MaintenancePolicy:
        if type(policy) is not MaintenancePolicy:
            raise TypeError("policy must be a MaintenancePolicy.")
        self._not_capability(policy.owner_id)
        if self._work_guard is not None:
            self._work_guard.validate_maintenance_target(policy.capability_id)
        self._validate_maintenance(policy, ownership=True)
        if policy.id in self._state.maintenance_policies or any(
            p.capability_id == policy.capability_id
            for p in self._state.maintenance_policies.values()
        ):
            raise ValueError("Maintenance policy id and capability must be unique.")
        attrs = {
            "owner_id": policy.owner_id,
            "capability_id": policy.capability_id,
            "label": policy.label,
            "upkeep": tuple(
                {"resource": r.resource, "amount": r.amount} for r in policy.upkeep
            ),
            "initial_condition": policy.initial_condition,
            "maximum_condition": policy.maximum_condition,
            "deterioration_per_unpaid_tick": policy.deterioration_per_unpaid_tick,
            "recovery_per_paid_tick": policy.recovery_per_paid_tick,
        }
        return self._create(
            "maintenance",
            policy,
            MaintenanceState(policy.id, policy.initial_condition),
            attrs,
        )

    def _create(
        self, prefix: str, policy: object, state: object, attrs: dict[str, object]
    ):
        policies, states = getattr(self._state, prefix + "_policies"), getattr(
            self._state, prefix + "_states"
        )
        events = frozenset(self._state.events)
        try:
            policies[policy.id] = policy
            states[policy.id] = state
            self._events.record(
                kind=prefix + "_policy_created", subject_id=policy.id, attributes=attrs
            )
        except Exception:
            policies.pop(policy.id, None)
            states.pop(policy.id, None)
            self._remove_events(events)
            raise
        return policy

    def apply(self) -> None:
        self.validate_loaded_state()
        self._validate_inputs()
        states = (
            *self._state.consumption_states.values(),
            *self._state.maintenance_states.values(),
            *self._state.storage_states.values(),
        )
        done = tuple(s.last_processed_tick == self._state.tick for s in states)
        if states and all(done):
            return
        if any(done):
            raise ValueError("Consequence phase is partially processed.")
        ids = (
            {p.owner_id for p in self._state.consumption_policies.values()}
            | {p.owner_id for p in self._state.storage_policies.values()}
            | {p.owner_id for p in self._state.maintenance_policies.values()}
            | {p.capability_id for p in self._state.maintenance_policies.values()}
        )
        entities = {
            i: (
                deepcopy(self._state.entities[i].attributes),
                self._state.entities[i].destroyed_tick,
            )
            for i in ids
        }
        snapshots = {
            n: deepcopy(getattr(self._state, n))
            for n in ("consumption_states", "maintenance_states", "storage_states")
        }
        events = frozenset(self._state.events)
        try:
            for key in sorted(self._state.consumption_policies):
                self._consume(key)
            for key in sorted(self._state.maintenance_policies):
                self._maintain(key)
            for key in sorted(self._state.storage_policies):
                self._store(key)
        except Exception:
            for key, (attrs, tick) in entities.items():
                self._state.entities[key].attributes.clear()
                self._state.entities[key].attributes.update(attrs)
                self._state.entities[key].destroyed_tick = tick
            for name, snapshot in snapshots.items():
                value = getattr(self._state, name)
                value.clear()
                value.update(snapshot)
            self._remove_events(events)
            raise

    def _consume(self, key: str) -> None:
        p, old = (
            self._state.consumption_policies[key],
            self._state.consumption_states[key],
        )
        owner = self._state.entities[p.owner_id]
        population = _nonnegative(owner.attributes.get("population"), "population")
        result, flags = {}, []
        for resource, rate in (
            ("food", p.food_per_person_per_tick),
            ("water", p.water_per_person_per_tick),
        ):
            required = population * rate
            available = _nonnegative(self._resources.get(owner, resource), resource)
            consumed = min(available, required)
            shortage = required - consumed
            self._resources.remove(owner, resource, consumed)
            result[resource] = {
                "required": required,
                "consumed": consumed,
                "shortage": shortage,
            }
            flags.append(shortage > 0)
        self._events.record(
            kind="consumption_applied",
            subject_id=key,
            attributes={"owner_id": p.owner_id, **result},
        )
        for resource, before, after in (
            ("food", old.food_shortage, flags[0]),
            ("water", old.water_shortage, flags[1]),
        ):
            if after and not before:
                self._events.record(
                    kind="consumption_shortage_started",
                    subject_id=key,
                    attributes={
                        "owner_id": p.owner_id,
                        "resource": resource,
                        "shortage": result[resource]["shortage"],
                    },
                )
            elif before and not after:
                self._events.record(
                    kind="consumption_shortage_recovered",
                    subject_id=key,
                    attributes={"owner_id": p.owner_id, "resource": resource},
                )
        self._state.consumption_states[key] = replace(
            old,
            last_processed_tick=self._state.tick,
            food_shortage=flags[0],
            water_shortage=flags[1],
        )

    def _maintain(self, key: str) -> None:
        p, old = (
            self._state.maintenance_policies[key],
            self._state.maintenance_states[key],
        )
        if old.condition == 0:
            self._state.maintenance_states[key] = replace(
                old, last_processed_tick=self._state.tick
            )
            return
        owner = self._state.entities[p.owner_id]
        paid = all(
            _nonnegative(self._resources.get(owner, r.resource), r.resource) >= r.amount
            for r in p.upkeep
        )
        if paid:
            for r in p.upkeep:
                self._resources.remove(owner, r.resource, r.amount)
        attrs = {"owner_id": p.owner_id, "capability_id": p.capability_id}
        self._events.record(
            kind="capability_upkeep_applied",
            subject_id=key,
            attributes={
                **attrs,
                "requirements": tuple(
                    {"resource": r.resource, "amount": r.amount} for r in p.upkeep
                ),
                "paid": paid,
            },
        )
        shortage = not paid
        if shortage != old.upkeep_shortage:
            self._events.record(
                kind=(
                    "maintenance_shortage_started"
                    if shortage
                    else "maintenance_shortage_recovered"
                ),
                subject_id=key,
                attributes=attrs,
            )
        current = (
            min(p.maximum_condition, old.condition + p.recovery_per_paid_tick)
            if paid
            else max(0, old.condition - p.deterioration_per_unpaid_tick)
        )
        if current != old.condition:
            self._events.record(
                kind=(
                    "capability_recovered"
                    if current > old.condition
                    else "capability_deteriorated"
                ),
                subject_id=key,
                attributes={
                    **attrs,
                    "previous_condition": old.condition,
                    "current_condition": current,
                },
            )
        if current == 0:
            self._entities.mark_destroyed(p.capability_id, self._state.tick)
            self._events.record(
                kind="capability_destroyed", subject_id=key, attributes=attrs
            )
        self._state.maintenance_states[key] = replace(
            old,
            condition=current,
            last_processed_tick=self._state.tick,
            upkeep_shortage=shortage,
        )

    def _store(self, key: str) -> None:
        p, old = self._state.storage_policies[key], self._state.storage_states[key]
        owner = self._state.entities[p.owner_id]
        capacity = owned_capacity(self._state, p.owner_id, "storage_capacity")
        total = sum(
            _nonnegative(self._resources.get(owner, r.resource), r.resource)
            for r in p.resources
        )
        overflow = max(0, total - capacity)
        remaining = overflow
        excesses = []
        for r in p.resources:
            amount = min(self._resources.get(owner, r.resource), remaining)
            self._resources.remove(owner, r.resource, amount)
            remaining -= amount
            excesses.append(amount)
        routines = []
        for r in p.resources:
            amount = min(self._resources.get(owner, r.resource), r.spoilage_per_tick)
            self._resources.remove(owner, r.resource, amount)
            routines.append(amount)
        spoiling = overflow > 0 or any(routines)
        if spoiling:
            details = tuple(
                {"resource": r.resource, "overflow": excess, "routine": routine}
                for r, excess, routine in zip(p.resources, excesses, routines)
            )
            self._events.record(
                kind="storage_spoilage_applied",
                subject_id=key,
                attributes={
                    "owner_id": p.owner_id,
                    "capacity": capacity,
                    "total_before": total,
                    "overflow": overflow,
                    "resources": details,
                },
            )
        self._state.storage_states[key] = replace(
            old,
            last_processed_tick=self._state.tick,
            overflowing=overflow > 0,
            spoiling=spoiling,
        )

    def npc_interpretation(self, key: str) -> NPCConsequenceInterpretation:
        if key in self._state.consumption_policies:
            s = self._state.consumption_states[key]
            desc = (
                "Food and water use has not yet been assessed."
                if s.last_processed_tick is None
                else {
                    (False, False): "Food and water use is currently supplied.",
                    (True, False): "Food use cannot currently be fully supplied.",
                    (False, True): "Water use cannot currently be fully supplied.",
                    (
                        True,
                        True,
                    ): "Food and water use cannot currently be fully supplied.",
                }[(s.food_shortage, s.water_shortage)]
            )
            return NPCConsequenceInterpretation("Food and water", desc)
        if key in self._state.storage_policies:
            s = self._state.storage_states[key]
            desc = (
                "Storage conditions have not yet been assessed."
                if s.last_processed_tick is None
                else (
                    "Stored supplies exceed available capacity."
                    if s.overflowing
                    else (
                        "Some stored supplies are being lost."
                        if s.spoiling
                        else "Stored supplies are currently stable."
                    )
                )
            )
            return NPCConsequenceInterpretation("Stored supplies", desc)
        p = self._state.maintenance_policies.get(key)
        if p is None:
            raise ValueError(f"Unknown consequence policy '{key}'.")
        s = self._state.maintenance_states[key]
        desc = (
            "Upkeep has not yet been assessed."
            if s.last_processed_tick is None
            else (
                "This capability is no longer usable."
                if s.condition == 0
                else (
                    "This capability lacks required upkeep and is deteriorating."
                    if s.upkeep_shortage
                    else (
                        "This capability is recovering but remains worn."
                        if s.condition < p.maximum_condition
                        else "This capability is sound and maintained."
                    )
                )
            )
        )
        return NPCConsequenceInterpretation(p.label, desc)

    def validate_loaded_state(self) -> None:
        all_states = []
        for prefix in ("consumption", "storage", "maintenance"):
            policies, states = getattr(self._state, prefix + "_policies"), getattr(
                self._state, prefix + "_states"
            )
            all_states.extend(states.values())
            if set(policies) != set(states):
                raise ValueError(
                    f"Persisted {prefix} policies and states must correspond."
                )
            policy_type, state_type = {
                "consumption": (ConsumptionPolicy, ConsumptionState),
                "storage": (StoragePolicy, StorageState),
                "maintenance": (MaintenancePolicy, MaintenanceState),
            }[prefix]
            for key, p in policies.items():
                s = states[key]
                if type(p) is not policy_type or type(s) is not state_type:
                    raise TypeError(f"Persisted {prefix} records have incorrect types.")
                if p.id != key or s.policy_id != key:
                    raise ValueError("Persisted consequence keys must match ids.")
                if (
                    s.last_processed_tick is not None
                    and s.last_processed_tick > self._state.tick
                ):
                    raise ValueError("Consequence tick cannot be future.")
        for policies in (
            self._state.consumption_policies,
            self._state.storage_policies,
        ):
            owners = set()
            for p in policies.values():
                self._live(p.owner_id)
                self._not_capability(p.owner_id)
                if p.owner_id in owners:
                    raise ValueError(
                        "Consequence owner must be unique per policy type."
                    )
                owners.add(p.owner_id)
        for p in self._state.consumption_policies.values():
            s = self._state.consumption_states[p.id]
            if s.last_processed_tick is None and (s.food_shortage or s.water_shortage):
                raise ValueError("Unprocessed consumption flags must be false.")
        for p in self._state.storage_policies.values():
            s = self._state.storage_states[p.id]
            if s.last_processed_tick is None and (s.overflowing or s.spoiling):
                raise ValueError("Unprocessed storage flags must be false.")
        capabilities = set()
        for p in self._state.maintenance_policies.values():
            self._validate_maintenance(p, ownership=False)
            if p.capability_id in capabilities:
                raise ValueError("Maintenance capability must be unique.")
            capabilities.add(p.capability_id)
            s = self._state.maintenance_states[p.id]
            target = self._state.entities[p.capability_id]
            if not 0 <= s.condition <= p.maximum_condition:
                raise ValueError("Maintenance condition is out of bounds.")
            if s.last_processed_tick is None and (
                s.condition != p.initial_condition
                or s.upkeep_shortage
                or target.destroyed_tick is not None
            ):
                raise ValueError("Unprocessed maintenance state must use defaults.")
            if (s.condition == 0) != (target.destroyed_tick is not None):
                raise ValueError("Terminal maintenance state disagrees with lifecycle.")
            if s.condition == 0 and (
                s.last_processed_tick is None
                or not isinstance(target.destroyed_tick, int)
                or isinstance(target.destroyed_tick, bool)
                or target.destroyed_tick < 0
                or target.destroyed_tick > s.last_processed_tick
                or s.last_processed_tick > self._state.tick
            ):
                raise ValueError("Terminal maintenance ticks are inconsistent.")
        current = tuple(s.last_processed_tick == self._state.tick for s in all_states)
        if any(current) and not all(current):
            raise ValueError("Consequence phase is partially processed.")

    def _live(self, entity_id: str) -> None:
        entity = self._state.entities.get(entity_id)
        if entity is None or entity.destroyed_tick is not None:
            raise ValueError("Consequence owner must be live.")

    def _validate_inputs(self) -> None:
        for p in self._state.consumption_policies.values():
            owner = self._state.entities[p.owner_id]
            _nonnegative(owner.attributes.get("population"), "population")
            for resource in ("food", "water"):
                _stock(owner.attributes, resource)
        for p in self._state.maintenance_policies.values():
            if self._state.maintenance_states[p.id].condition:
                owner = self._state.entities[p.owner_id]
                for requirement in p.upkeep:
                    _stock(owner.attributes, requirement.resource)
        for p in self._state.storage_policies.values():
            owned_capacity(self._state, p.owner_id, "storage_capacity")
            owner = self._state.entities[p.owner_id]
            for rule in p.resources:
                _stock(owner.attributes, rule.resource)

    def _not_capability(self, entity_id: str) -> None:
        if any(
            p.capability_id == entity_id
            for p in self._state.maintenance_policies.values()
        ):
            raise ValueError(
                "Maintenance capability cannot occupy a live-required role."
            )

    def _validate_maintenance(self, p: MaintenancePolicy, *, ownership: bool) -> None:
        self._live(p.owner_id)
        target = self._state.entities.get(p.capability_id)
        if target is None:
            raise ValueError("Maintenance capability must exist.")
        if ownership and target.destroyed_tick is not None:
            raise ValueError("Maintenance capability must be live at creation.")
        if target.attributes.get("is_constructed") is not True:
            raise ValueError("Maintenance capability must be constructed.")
        if ownership and not any(
            r.kind == "owns"
            and r.source_id == p.owner_id
            and r.target_id == p.capability_id
            and r.destroyed_tick is None
            and r.created_tick <= self._state.tick
            for r in self._state.relationships.values()
        ):
            raise ValueError("Maintenance capability must be directly owned.")
        occupied = (
            any(
                x.owner_id == p.capability_id
                for x in self._state.consumption_policies.values()
            )
            or any(
                x.owner_id == p.capability_id
                for x in self._state.storage_policies.values()
            )
            or any(
                x.owner_id == p.capability_id
                for x in self._state.maintenance_policies.values()
            )
            or any(
                x.owner_id == p.capability_id
                for x in self._state.need_definitions.values()
            )
            or any(
                x.owner_id == p.capability_id
                for x in self._state.goal_definitions.values()
            )
            or any(
                x.source_entity_id == p.capability_id
                for x in self._state.external_dispatches.values()
            )
        )
        if occupied:
            raise ValueError("Maintenance capability occupies a live-required role.")

    def _remove_events(self, before: frozenset[str]) -> None:
        for key in set(self._state.events) - before:
            self._state.events.pop(key, None)


class ConsequenceSystem:
    def __init__(self, manager: ConsequenceManager) -> None:
        self._manager = manager

    def step(self, state: WorldState) -> None:
        self._manager.apply()


def _nonnegative(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


def _stock(attributes: dict[str, object], resource: str) -> int:
    resources = attributes.get("resources")
    if resources is None:
        return 0
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dictionary.")
    return _nonnegative(resources.get(resource, 0), resource)
