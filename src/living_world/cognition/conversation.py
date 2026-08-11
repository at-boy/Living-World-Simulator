"""Bounded NPC dialogue that remains within the cognition information boundary."""

from __future__ import annotations

from dataclasses import dataclass

from living_world.cognition.action_resolution import ActionResolution, NPCActionResolver
from living_world.cognition.decision_engine import DecisionEngine
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.managers.observation_manager import ObservationManager


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """One visible utterance, labelled without revealing internal identity."""

    speaker_label: str
    utterance: str

    def __post_init__(self) -> None:
        _require_prose(self.speaker_label, "speaker_label")
        _require_prose(self.utterance, "utterance")


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """Visible dialogue and authoritative results of any separate proposals."""

    turns: tuple[ConversationTurn, ...]
    resolutions: tuple[ActionResolution, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.turns, tuple) or not all(
            isinstance(turn, ConversationTurn) for turn in self.turns
        ):
            raise TypeError("turns must be a tuple of ConversationTurn values.")
        if not isinstance(self.resolutions, tuple) or not all(
            isinstance(resolution, ActionResolution) for resolution in self.resolutions
        ):
            raise TypeError("resolutions must be a tuple of ActionResolution values.")


class ConversationService:
    """Conduct visible NPC dialogue without granting cognition state authority."""

    def __init__(
        self,
        context_assembler: NPCContextAssembler,
        decision_engine: DecisionEngine,
        action_resolver: NPCActionResolver,
        observations: ObservationManager,
        action_options: tuple[ActionOption, ...],
    ) -> None:
        if not isinstance(context_assembler, NPCContextAssembler):
            raise TypeError("context_assembler must be an NPCContextAssembler.")
        if not isinstance(decision_engine, DecisionEngine):
            raise TypeError("decision_engine must be a DecisionEngine.")
        if not isinstance(action_resolver, NPCActionResolver):
            raise TypeError("action_resolver must be an NPCActionResolver.")
        if not isinstance(observations, ObservationManager):
            raise TypeError("observations must be an ObservationManager.")
        _validate_action_options(action_options)
        self._context_assembler = context_assembler
        self._decision_engine = decision_engine
        self._action_resolver = action_resolver
        self._observations = observations
        self._action_options = action_options

    def conduct(
        self,
        *,
        participant_ids: tuple[str, ...],
        topic: str,
        max_turns: int,
    ) -> ConversationResult:
        """Conduct at most ``max_turns`` deterministic, visible dialogue turns."""

        self._validate_participants(participant_ids)
        topic_preamble = self._topic_preamble(topic)
        self._validate_max_turns(max_turns)

        history: list[str] = [topic_preamble]
        turns: list[ConversationTurn] = []
        resolutions: list[ActionResolution] = []
        for turn_index in range(max_turns):
            speaker_id = participant_ids[turn_index % len(participant_ids)]
            context = self._context_assembler.assemble(
                holder_id=speaker_id,
                conversation_history=tuple(history),
            )
            decision = self._decision_engine.decide(context, self._action_options)
            if decision.spoken_text is not None:
                utterance = self._context_assembler.validate_conversation_prose(
                    decision.spoken_text
                )
                turn = ConversationTurn(
                    speaker_label=context.identity,
                    utterance=utterance,
                )
                turns.append(turn)
                self._record_for_recipients(
                    participant_ids=participant_ids,
                    speaker_id=speaker_id,
                    utterance=utterance,
                )
                history.append(
                    self._context_assembler.validate_conversation_prose(
                        f"{turn.speaker_label}: {utterance}"
                    )
                )
            if decision.action_request is not None:
                resolutions.append(
                    self._action_resolver.resolve(
                        actor_id=speaker_id,
                        request=decision.action_request,
                    )
                )
        return ConversationResult(turns=tuple(turns), resolutions=tuple(resolutions))

    def _validate_participants(self, participant_ids: object) -> None:
        if not isinstance(participant_ids, tuple):
            raise TypeError("participant_ids must be a tuple of entity IDs.")
        if not participant_ids:
            raise ValueError("participant_ids cannot be empty.")
        if not all(
            isinstance(participant_id, str) for participant_id in participant_ids
        ):
            raise TypeError("participant_ids must contain only entity IDs.")
        if any(not participant_id.strip() for participant_id in participant_ids):
            raise ValueError("participant_ids cannot contain empty entity IDs.")
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participant_ids must be unique.")
        if any(
            not self._context_assembler.has_known_entity(participant_id)
            for participant_id in participant_ids
        ):
            raise ValueError("participant_ids must identify known entities.")

    def _topic_preamble(self, topic: object) -> str:
        _require_prose(topic, "topic")
        return self._context_assembler.validate_conversation_prose(
            f"Conversation topic: {topic}"
        )

    @staticmethod
    def _validate_max_turns(value: object) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("max_turns must be a non-boolean integer.")
        if value < 0:
            raise ValueError("max_turns cannot be negative.")

    def _record_for_recipients(
        self,
        *,
        participant_ids: tuple[str, ...],
        speaker_id: str,
        utterance: str,
    ) -> None:
        for recipient_id in participant_ids:
            if recipient_id == speaker_id:
                continue
            self._observations.record(
                observer=recipient_id,
                subject=speaker_id,
                description=utterance,
                confidence=1.0,
                evidence={},
                metadata={},
            )


def _require_prose(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _validate_action_options(value: object) -> None:
    if not isinstance(value, tuple):
        raise TypeError("action_options must be a tuple of ActionOption values.")
    if not all(isinstance(action, ActionOption) for action in value):
        raise TypeError("action_options must contain only ActionOption values.")
    keys = tuple(action.key for action in value)
    if len(keys) != len(set(keys)):
        raise ValueError("action_options must have unique keys.")
