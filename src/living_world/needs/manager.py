from dataclasses import replace

from living_world.managers.event_manager import EventManager
from living_world.needs.model import (
    NeedAssessment,
    NeedDefinition,
    NeedKind,
    NeedLevel,
    NeedState,
    NPCNeedInterpretation,
)
from living_world.state.world_state import WorldState

_LABELS = {
    NeedKind.FOOD: "Food",
    NeedKind.WATER: "Water",
    NeedKind.SHELTER: "Shelter",
    NeedKind.STORAGE: "Storage",
}
_DESCRIPTIONS = {
    NeedLevel.UNAVAILABLE: "This need cannot yet be assessed.",
    NeedLevel.CRITICAL: "This need is critically unmet.",
    NeedLevel.STRAINED: "This need is under strain.",
    NeedLevel.SECURE: "This need is currently met.",
    NeedLevel.SURPLUS: "This need has more provision than currently required.",
}


class NeedManager:
    """Own authoritative need definitions and bounded assessment histories."""

    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state, self._events = state, events

    def create(self, definition: NeedDefinition) -> NeedDefinition:
        self._validate_definition(definition)
        if definition.id in self._state.need_definitions:
            raise ValueError(f"Need '{definition.id}' already exists.")
        if any(
            item.owner_id == definition.owner_id and item.kind is definition.kind
            for item in self._state.need_definitions.values()
        ):
            raise ValueError("A need kind may occur only once for an owner.")
        original_events = frozenset(self._state.events)
        try:
            self._events.record(
                kind="need_created",
                subject_id=definition.id,
                attributes={
                    "owner_id": definition.owner_id,
                    "kind": definition.kind.value,
                },
            )
            self._state.need_definitions[definition.id] = definition
            self._state.need_states[definition.id] = NeedState(definition.id)
        except Exception:
            for event_id in set(self._state.events) - original_events:
                self._state.events.pop(event_id, None)
            self._state.need_definitions.pop(definition.id, None)
            self._state.need_states.pop(definition.id, None)
            raise
        return definition

    def record_assessment(self, need_id: str, assessment: NeedAssessment) -> NeedState:
        definition = self._definition(need_id)
        if assessment.tick != self._state.tick:
            raise ValueError(
                "Need assessments may be recorded only at the current tick."
            )
        self._validate_assessment(definition, assessment)
        old = self._state.need_states[need_id]
        if old.current is not None and assessment.tick < old.current.tick:
            raise ValueError("Need assessment ticks must increase.")
        if old.current is not None and old.current.tick == assessment.tick:
            if old.current == assessment:
                return old
            raise ValueError("A need cannot have conflicting assessments at one tick.")
        updated = replace(
            old,
            current=assessment,
            history=(old.history + (assessment,))[
                -definition.assessment_window_ticks :
            ],
        )
        changed = (
            assessment.level is not NeedLevel.UNAVAILABLE
            if old.current is None
            else old.current.level is not assessment.level
        )
        original_events = frozenset(self._state.events)
        try:
            if changed:
                self._events.record(
                    kind="need_level_changed",
                    subject_id=need_id,
                    attributes={
                        "old_level": (
                            None if old.current is None else old.current.level.value
                        ),
                        "new_level": assessment.level.value,
                        "available": assessment.available,
                        "required": assessment.required,
                        "balance": assessment.balance,
                        "pressure": assessment.pressure,
                    },
                )
            self._state.need_states[need_id] = updated
        except Exception:
            for event_id in set(self._state.events) - original_events:
                self._state.events.pop(event_id, None)
            self._state.need_states[need_id] = old
            raise
        return updated

    def get(self, need_id: str) -> NeedDefinition | None:
        return self._state.need_definitions.get(need_id)

    def state_for(self, need_id: str) -> NeedState | None:
        return self._state.need_states.get(need_id)

    def all(self) -> tuple[NeedDefinition, ...]:
        return tuple(
            self._state.need_definitions[key]
            for key in sorted(self._state.need_definitions)
        )

    def for_owner(self, owner_id: str) -> tuple[NeedDefinition, ...]:
        return tuple(item for item in self.all() if item.owner_id == owner_id)

    def for_owner_kind(self, owner_id: str, kind: NeedKind) -> NeedDefinition | None:
        matches = [
            item
            for item in self._state.need_definitions.values()
            if item.owner_id == owner_id and item.kind is kind
        ]
        if len(matches) > 1:
            raise ValueError("Need owner and kind must be unique.")
        return matches[0] if matches else None

    def npc_interpretation(self, need_id: str) -> NPCNeedInterpretation:
        definition = self._definition(need_id)
        current = self._state.need_states[need_id].current
        return NPCNeedInterpretation(
            _LABELS[definition.kind],
            _DESCRIPTIONS[NeedLevel.UNAVAILABLE if current is None else current.level],
        )

    def npc_interpretations(self, owner_id: str) -> tuple[NPCNeedInterpretation, ...]:
        return tuple(
            self.npc_interpretation(definition.id)
            for definition in self.for_owner(owner_id)
        )

    def validate_loaded_state(self) -> None:
        if set(self._state.need_definitions) != set(self._state.need_states):
            raise ValueError("Persisted need definitions and states must correspond.")
        pairs: set[tuple[str, NeedKind]] = set()
        for key, definition in self._state.need_definitions.items():
            state = self._state.need_states[key]
            if key != definition.id or key != state.need_id:
                raise ValueError(
                    "Persisted need dictionary keys must match record ids."
                )
            self._validate_definition(definition)
            pair = (definition.owner_id, definition.kind)
            if pair in pairs:
                raise ValueError("Persisted need owner and kind must be unique.")
            pairs.add(pair)
            if len(state.history) > definition.assessment_window_ticks:
                raise ValueError(
                    "Persisted need history exceeds its assessment window."
                )
            ticks = tuple(item.tick for item in state.history)
            if ticks != tuple(sorted(set(ticks))):
                raise ValueError(
                    "Persisted need history ticks must be unique and ordered."
                )
            for assessment in state.history:
                if assessment.tick > self._state.tick:
                    raise ValueError(
                        "Persisted need assessment cannot be in the future."
                    )
                self._validate_assessment(definition, assessment)

    def _definition(self, need_id: str) -> NeedDefinition:
        definition = self._state.need_definitions.get(need_id)
        if definition is None:
            raise ValueError(f"Unknown need '{need_id}'.")
        return definition

    def _validate_definition(self, definition: NeedDefinition) -> None:
        if not isinstance(definition, NeedDefinition):
            raise TypeError("definition must be a NeedDefinition.")
        owner = self._state.entities.get(definition.owner_id)
        if owner is None or owner.destroyed_tick is not None:
            raise ValueError("Need owner must be a live entity.")
        if any(
            policy.capability_id == definition.owner_id
            for policy in self._state.maintenance_policies.values()
        ):
            raise ValueError("A maintenance capability cannot own a need.")

    @staticmethod
    def _validate_assessment(
        definition: NeedDefinition, assessment: NeedAssessment
    ) -> None:
        if not isinstance(assessment, NeedAssessment):
            raise TypeError("assessment must be a NeedAssessment.")
        if assessment.level is NeedLevel.UNAVAILABLE:
            return
        assert (
            assessment.available is not None
            and assessment.required is not None
            and assessment.balance is not None
            and assessment.pressure is not None
        )
        if assessment.balance != assessment.available - assessment.required:
            raise ValueError("Need assessment balance is inconsistent.")
        expected = (
            0.0
            if assessment.required == 0 or assessment.available >= assessment.required
            else (assessment.required - assessment.available) / assessment.required
        )
        if assessment.pressure != expected:
            raise ValueError("Need assessment pressure is inconsistent.")
        level = (
            NeedLevel.SURPLUS
            if assessment.balance > 0
            else (
                NeedLevel.SECURE
                if assessment.pressure <= definition.secure_maximum
                else (
                    NeedLevel.STRAINED
                    if assessment.pressure <= definition.strained_maximum
                    else NeedLevel.CRITICAL
                )
            )
        )
        if assessment.level is not level:
            raise ValueError("Need assessment level is inconsistent.")
