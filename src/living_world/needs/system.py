from living_world.needs.manager import NeedManager
from living_world.needs.model import NeedAssessment, NeedDefinition, NeedKind, NeedLevel
from living_world.state.world_state import WorldState


class NeedAssessmentSystem:
    """Assess every registered need in stable identifier order."""

    def __init__(self, needs: NeedManager) -> None:
        self._needs = needs

    def step(self, state: WorldState) -> None:
        original_states, original_events = dict(state.need_states), frozenset(
            state.events
        )
        try:
            for definition in self._needs.all():
                self._needs.record_assessment(
                    definition.id, self._assessment(definition, state)
                )
        except Exception:
            state.need_states.clear()
            state.need_states.update(original_states)
            for event_id in set(state.events) - original_events:
                state.events.pop(event_id, None)
            raise

    @staticmethod
    def _assessment(definition: NeedDefinition, state: WorldState) -> NeedAssessment:
        owner = state.entities.get(definition.owner_id)
        if owner is None or owner.destroyed_tick is not None:
            raise ValueError("Need owner must remain live.")
        if "population" not in owner.attributes:
            return NeedAssessment(
                state.tick, NeedLevel.UNAVAILABLE, None, None, None, None
            )
        population = _nonnegative_integer(owner.attributes["population"], "population")
        available = NeedAssessmentSystem._available(definition, state)
        required = population * definition.requirement_per_person
        balance = available - required
        pressure = (
            0.0
            if required == 0 or available >= required
            else (required - available) / required
        )
        level = (
            NeedLevel.SURPLUS
            if balance > 0
            else (
                NeedLevel.SECURE
                if pressure <= definition.secure_maximum
                else (
                    NeedLevel.STRAINED
                    if pressure <= definition.strained_maximum
                    else NeedLevel.CRITICAL
                )
            )
        )
        return NeedAssessment(state.tick, level, available, required, balance, pressure)

    @staticmethod
    def _available(definition: NeedDefinition, state: WorldState) -> int:
        owner = state.entities[definition.owner_id]
        if definition.kind in (NeedKind.FOOD, NeedKind.WATER):
            resources = owner.attributes.get("resources", {})
            if not isinstance(resources, dict):
                raise TypeError("Need owner resources must be a dictionary.")
            return _nonnegative_integer(
                resources.get(definition.kind.value, 0), definition.kind.value
            )
        attribute = (
            "housing_allocated"
            if definition.kind is NeedKind.SHELTER
            else "storage_capacity"
        )
        targets = {
            r.target_id
            for r in state.relationships.values()
            if r.kind == "owns"
            and r.source_id == definition.owner_id
            and r.destroyed_tick is None
            and r.created_tick <= state.tick
            and r.target_id != definition.owner_id
        }
        entities = [owner]
        for target_id in sorted(targets):
            target = state.entities.get(target_id)
            if target is None:
                raise ValueError(
                    f"Ownership relationship targets unknown entity '{target_id}'."
                )
            if target.destroyed_tick is None:
                entities.append(target)
        return sum(
            _nonnegative_integer(entity.attributes.get(attribute, 0), attribute)
            for entity in entities
        )


def _nonnegative_integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value
