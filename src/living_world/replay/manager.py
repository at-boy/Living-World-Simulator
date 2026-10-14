"""Exclusive durable replay mutation and lifecycle validation."""

from __future__ import annotations

from living_world.managers.event_manager import EventManager
from living_world.replay.model import (
    ProposalTapeError,
    ReplayBinding,
    ReplayOutcome,
    ReplayState,
    integer,
    prose,
)
from living_world.state.world_state import WorldState


class ReplayManager:
    def __init__(self, state: WorldState, events: EventManager) -> None:
        self._state = state
        self._events = events

    def configure(self, binding: ReplayBinding) -> ReplayBinding:
        if not isinstance(binding, ReplayBinding):
            raise ProposalTapeError("replay_state_invalid")
        if self._state.replay_binding is not None:
            self.validate_loaded_state()
            if self._state.replay_binding != binding:
                raise ProposalTapeError("scenario_mismatch")
            return binding
        if (
            self._state.replay_state is not None
            or binding.configured_tick != self._state.tick
        ):
            raise ProposalTapeError("replay_state_invalid")
        self._validate(binding, ReplayState(0), completed=True)
        self._state.replay_binding = binding
        self._state.replay_state = ReplayState(0)
        return binding

    def current(self) -> ReplayState | None:
        return self._state.replay_state

    def consume(
        self, *, sequence: int, actor_label: str, outcome: ReplayOutcome
    ) -> ReplayState:
        binding, current = self._required()
        if current.next_index >= len(binding.actor_sequence):
            raise ProposalTapeError("tape_exhausted")
        self._validate(binding, current, completed=True)
        if (
            not integer(sequence)
            or sequence != current.next_index + 1
            or actor_label != binding.actor_sequence[current.next_index]
            or not isinstance(outcome, ReplayOutcome)
        ):
            raise ProposalTapeError("replay_state_invalid")
        following = ReplayState(current.next_index + 1, self._state.tick)
        self._validate(binding, following, completed=False)
        event_ids = set(self._state.events)
        try:
            self._events.record(
                kind="replay_proposal_resolved",
                subject_id=self._state.scenario_entity_bindings[actor_label],
                attributes={
                    "sequence": sequence,
                    "actor_label": actor_label,
                    "outcome": outcome.value,
                },
            )
            self._state.replay_state = following
        except Exception:
            self._state.replay_state = current
            for key in set(self._state.events) - event_ids:
                self._state.events.pop(key)
            raise
        return following

    def validate_loaded_state(self) -> None:
        self._validate_labels()
        if self._state.replay_binding is None and self._state.replay_state is None:
            return
        binding, current = self._required()
        self._validate(binding, current, completed=True)

    def _required(self) -> tuple[ReplayBinding, ReplayState]:
        binding, current = self._state.replay_binding, self._state.replay_state
        if not isinstance(binding, ReplayBinding) or not isinstance(
            current, ReplayState
        ):
            raise ProposalTapeError("replay_state_invalid")
        return binding, current

    def _validate_labels(self) -> None:
        labels = self._state.scenario_entity_bindings
        if not isinstance(labels, dict) or len(set(labels.values())) != len(labels):
            raise ProposalTapeError("replay_state_invalid")
        for label, entity_id in labels.items():
            prose(label, code="replay_state_invalid")
            if not isinstance(entity_id, str) or entity_id not in self._state.entities:
                raise ProposalTapeError("replay_state_invalid")
        if labels and self._state.run_metadata is None:
            raise ProposalTapeError("replay_state_invalid")

    def _validate(
        self, binding: ReplayBinding, current: ReplayState, *, completed: bool
    ) -> None:
        self._validate_labels()
        # Revalidate even frozen records supplied by a corrupt snapshot/test.
        binding.__post_init__()
        current.__post_init__()
        metadata = self._state.run_metadata
        if (
            metadata is None
            or metadata.scenario_key != binding.scenario_key
            or metadata.configuration_fingerprint != binding.scenario_fingerprint
        ):
            raise ProposalTapeError("scenario_mismatch")
        tick = self._state.tick
        n = current.next_index
        count = len(binding.actor_sequence)
        if not integer(tick) or binding.configured_tick > tick or n > count:
            raise ProposalTapeError("replay_state_invalid")
        expected_last = None if n == 0 else binding.configured_tick + n - 1
        if current.last_attempt_tick != expected_last or (
            expected_last is not None and expected_last > tick
        ):
            raise ProposalTapeError("replay_state_invalid")
        boundary_tick = binding.configured_tick + n
        if completed:
            if (n < count and tick != boundary_tick) or (
                n == count and tick < boundary_tick
            ):
                raise ProposalTapeError("replay_state_invalid")
        elif n == 0 or tick != boundary_tick - 1:
            raise ProposalTapeError("replay_state_invalid")
        for index, label in enumerate(binding.actor_sequence):
            entity_id = self._state.scenario_entity_bindings.get(label)
            entity = self._state.entities.get(entity_id or "")
            if entity is None or (index >= n and entity.destroyed_tick is not None):
                raise ProposalTapeError("actor_mismatch")
        if completed:
            self._validate_history(binding, current)

    def _validate_history(self, binding: ReplayBinding, current: ReplayState) -> None:
        resolutions = tuple(
            event
            for event in self._state.events.values()
            if event.kind == "replay_proposal_resolved"
        )
        if len(resolutions) != current.next_index:
            raise ProposalTapeError("replay_state_invalid")
        sequences: set[int] = set()
        for event in resolutions:
            attributes = event.attributes
            if set(attributes) != {"sequence", "actor_label", "outcome"}:
                raise ProposalTapeError("replay_state_invalid")
            sequence = attributes["sequence"]
            outcome = attributes["outcome"]
            if (
                not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence < 1
                or sequence > current.next_index
                or sequence in sequences
                or not isinstance(outcome, str)
                or outcome not in {item.value for item in ReplayOutcome}
            ):
                raise ProposalTapeError("replay_state_invalid")
            label = binding.actor_sequence[sequence - 1]
            if (
                not integer(event.tick)
                or event.tick != binding.configured_tick + sequence - 1
                or attributes["actor_label"] != label
                or event.subject_id != self._state.scenario_entity_bindings[label]
            ):
                raise ProposalTapeError("replay_state_invalid")
            sequences.add(sequence)

    def validate_entity_removal(self, entity_id: str) -> None:
        if entity_id in self._state.scenario_entity_bindings.values():
            raise ProposalTapeError("replay_state_invalid")

    def validate_entity_destruction(self, entity_id: str) -> None:
        if self._state.replay_binding is None:
            return
        binding, current = self._required()
        if any(
            self._state.scenario_entity_bindings.get(label) == entity_id
            for label in binding.actor_sequence[current.next_index :]
        ):
            raise ProposalTapeError("actor_mismatch")

    def _restore_preparation(
        self, binding: ReplayBinding | None, current: ReplayState | None
    ) -> None:
        """Private composition rollback; never a public binding-clear operation."""
        self._state.replay_binding = binding
        self._state.replay_state = current
