"""One proposal per tick through filtered context and the ordinary gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from living_world.cognition.action_resolution import NPCActionHandler, NPCActionResolver
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.external_world.dispatch_action import DISPATCH_ACTION_KEY
from living_world.replay.client import RecordedProposalClient
from living_world.replay.manager import ReplayManager
from living_world.replay.model import ProposalTape, ProposalTapeError, ReplayOutcome
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem

if TYPE_CHECKING:
    from living_world.api.inspection import WorldInspector
    from living_world.simulation.simulation_engine import SimulationEngine


@dataclass(frozen=True, slots=True)
class ReplayActionOffers:
    actor_id: str
    options: tuple[ActionOption, ...]
    handlers: tuple[NPCActionHandler, ...]


class ReplayOfferProvider(Protocol):
    def offers(
        self, *, actor_id: str, inspector: WorldInspector
    ) -> ReplayActionOffers: ...


class EmptyReplayOfferProvider:
    def offers(self, *, actor_id: str, inspector: WorldInspector) -> ReplayActionOffers:
        return ReplayActionOffers(actor_id, (), ())


class ReplayProposalSystem(SimulationSystem):
    def __init__(
        self,
        tape: ProposalTape,
        manager: ReplayManager,
        offer_provider: ReplayOfferProvider,
        *,
        engine: SimulationEngine,
        inspector: WorldInspector,
        context_assembler: NPCContextAssembler,
        boundary: NPCInformationBoundary,
    ) -> None:
        self._tape = tape
        self._manager = manager
        self._provider = offer_provider
        self._engine = engine
        self._inspector = inspector
        self._assembler = context_assembler
        self._boundary = boundary

    def validate_preparation(self, state: WorldState) -> None:
        binding = state.replay_binding
        if (
            state is not self._engine.state
            or binding is None
            or binding.tape_fingerprint != self._tape.fingerprint
            or binding.scenario_key != self._tape.scenario_key
            or binding.scenario_fingerprint != self._tape.scenario_fingerprint
            or binding.actor_sequence
            != tuple(entry.actor_label for entry in self._tape.entries)
        ):
            raise ProposalTapeError("missing_replay_preparation")
        self._manager.validate_loaded_state()

    def step(self, state: WorldState) -> None:
        self._manager.validate_loaded_state()
        current = self._manager.current()
        if current is None:
            raise ProposalTapeError("missing_replay_preparation")
        if current.next_index == len(self._tape.entries):
            return
        entry = self._tape.entries[current.next_index]
        actor_id = state.scenario_entity_bindings.get(entry.actor_label)
        actor = state.entities.get(actor_id or "")
        if actor_id is None or actor is None or actor.destroyed_tick is not None:
            raise ProposalTapeError("actor_mismatch")
        context = self._assembler.assemble(holder_id=actor_id)
        offers = self._provider.offers(actor_id=actor_id, inspector=self._inspector)
        self._validate_offers(offers, actor_id)
        decision = DecisionEngine(
            RecordedProposalClient(entry, expected_identity=actor.name)
        ).decide(context, offers.options)
        for text in (entry.rationale, decision.spoken_text):
            if text is not None:
                self._boundary.validate_conversation_prose(text)
        request = decision.action_request
        if request is None:
            outcome = ReplayOutcome.NO_ACTION
        else:
            self._validate_action_key(request.action_key)
            for text in (
                request.target_label,
                request.rationale,
                *request.arguments.keys(),
                *request.arguments.values(),
            ):
                if text is not None:
                    self._boundary.validate_conversation_prose(text)
            resolution = self._engine.resolve_npc_action(
                resolver=NPCActionResolver(offers.options, offers.handlers),
                actor_id=actor_id,
                request=request,
            )
            outcome = (
                ReplayOutcome.ACCEPTED
                if resolution.accepted
                else ReplayOutcome.REJECTED
            )
        self._manager.consume(
            sequence=entry.sequence, actor_label=entry.actor_label, outcome=outcome
        )

    def _validate_offers(self, bundle: ReplayActionOffers, actor_id: str) -> None:
        if not isinstance(bundle, ReplayActionOffers) or bundle.actor_id != actor_id:
            raise ProposalTapeError("actor_mismatch")
        if (
            not isinstance(bundle.options, tuple)
            or not isinstance(bundle.handlers, tuple)
            or any(not isinstance(option, ActionOption) for option in bundle.options)
        ):
            raise ProposalTapeError("offered_action_mismatch")
        # Also validate the ordinary gateway's structural contract before mutation.
        try:
            NPCActionResolver(bundle.options, bundle.handlers)
        except (TypeError, ValueError):
            raise ProposalTapeError("offered_action_mismatch") from None
        keys = tuple(option.key for option in bundle.options)
        if keys != tuple(sorted(set(keys))):
            raise ProposalTapeError("offered_action_mismatch")
        for option in bundle.options:
            if option.target_labels != tuple(
                sorted(
                    set(option.target_labels),
                    key=lambda value: (value.strip().casefold(), value),
                )
            ):
                raise ProposalTapeError("offered_action_mismatch")
            if sum(handler.supports(option.key) for handler in bundle.handlers) != 1:
                raise ProposalTapeError("offered_action_mismatch")
            self._validate_action_key(option.key)
            for text in (option.description, *option.target_labels):
                self._boundary.validate_conversation_prose(text)

    def _validate_action_key(self, key: str) -> None:
        # This existing public key is structured vocabulary, never a prose exemption.
        if key != DISPATCH_ACTION_KEY:
            self._boundary.validate_conversation_prose(key)
