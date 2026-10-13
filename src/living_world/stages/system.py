from __future__ import annotations

from typing import TYPE_CHECKING

from living_world.goals.model import GoalStatus
from living_world.stages.manager import SettlementStageManager
from living_world.stages.model import SettlementStage

if TYPE_CHECKING:
    from living_world.state.world_state import WorldState


class SettlementStageEvaluationSystem:
    def __init__(self, stages: SettlementStageManager) -> None:
        if not isinstance(stages, SettlementStageManager):
            raise TypeError("stages must be a SettlementStageManager.")
        self._stages = stages

    def step(self, state: WorldState) -> None:
        original = dict(state.settlement_stage_states)
        events = frozenset(state.events)
        try:
            self._stages.validate_loaded_state()
            for program in self._stages.all():
                current = state.settlement_stage_states[program.settlement_id]
                if (
                    current.current_stage is SettlementStage.TOWN
                    or current.last_transition_tick == state.tick
                ):
                    continue
                next_stage = program.stages[
                    tuple(SettlementStage).index(current.current_stage) + 1
                ]
                if all(
                    state.objective_states[item.objective_id].status
                    is GoalStatus.COMPLETED
                    for item in next_stage.requirements
                ):
                    self._stages.transition_to_next(
                        program.settlement_id,
                        self._stages.requirement_evidence(program.settlement_id),
                    )
        except Exception:
            state.settlement_stage_states.clear()
            state.settlement_stage_states.update(original)
            for event_id in set(state.events) - events:
                state.events.pop(event_id, None)
            raise
