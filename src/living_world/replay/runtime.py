"""Ephemeral replay composition and stopping-boundary finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.replay.model import ProposalTape, ProposalTapeError, ReplayBinding
from living_world.replay.system import (
    EmptyReplayOfferProvider,
    ReplayOfferProvider,
    ReplayProposalSystem,
)
from living_world.scenarios.scenario import LoadedScenario

if TYPE_CHECKING:
    from living_world.running.runner import RunResult
    from living_world.simulation.simulation_engine import SimulationEngine


class ReplayPreparation:
    def __init__(
        self, tape: ProposalTape, offer_provider: ReplayOfferProvider | None = None
    ) -> None:
        if not isinstance(tape, ProposalTape):
            raise ProposalTapeError("invalid_tape")
        if offer_provider is not None and not callable(
            getattr(offer_provider, "offers", None)
        ):
            raise ProposalTapeError("offered_action_mismatch")
        self._tape = tape
        self._provider = (
            EmptyReplayOfferProvider() if offer_provider is None else offer_provider
        )

    def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
        from living_world.api.inspection import EngineWorldInspector

        tape = self._tape
        if (
            scenario.key != tape.scenario_key
            or scenario.configuration_fingerprint != tape.scenario_fingerprint
        ):
            raise ProposalTapeError("scenario_mismatch")
        old_binding, old_state = engine.state.replay_binding, engine.replay.current()
        tick = engine.state.tick if old_binding is None else old_binding.configured_tick
        binding = ReplayBinding(
            tape.scenario_key,
            tape.scenario_fingerprint,
            tape.fingerprint,
            tuple(entry.actor_label for entry in tape.entries),
            tick,
        )
        # Build all ephemeral inputs before changing manager-owned binding.
        system = ReplayProposalSystem(
            tape,
            engine.replay,
            self._provider,
            engine=engine,
            inspector=EngineWorldInspector(engine),
            context_assembler=NPCContextAssembler(engine.state),
            boundary=NPCInformationBoundary(engine.state),
        )
        try:
            engine.replay.configure(binding)
            engine.configure_proposal_system(system)
        except Exception:
            engine.replay._restore_preparation(old_binding, old_state)
            raise

    def finish(
        self, engine: SimulationEngine, result: RunResult, *, finalize_proposals: bool
    ) -> None:
        from living_world.running.runner import StopReason

        self.prepare_identity(engine)
        current = engine.replay.current()
        assert current is not None
        if (
            finalize_proposals
            and result.stop_reason != StopReason.OPERATOR_STOP
            and result.terminal_condition != "operator_stop"
            and current.next_index != len(self._tape.entries)
        ):
            raise ProposalTapeError("unused_entries")

    def prepare_identity(self, engine: SimulationEngine) -> None:
        """Fail closed if the durable driver differs from this preparation."""
        binding = engine.state.replay_binding
        if (
            binding is None
            or binding.scenario_key != self._tape.scenario_key
            or binding.scenario_fingerprint != self._tape.scenario_fingerprint
            or binding.tape_fingerprint != self._tape.fingerprint
            or binding.actor_sequence
            != tuple(entry.actor_label for entry in self._tape.entries)
        ):
            raise ProposalTapeError("missing_replay_preparation")
        engine.replay.validate_loaded_state()
