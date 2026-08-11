from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from living_world.cognition.action_resolution import (
    ActionResolution,
    NPCActionHandlerContractError,
    NPCActionResolver,
)
from living_world.cognition.npc_cognition_client import ActionOption, ActionRequest
from living_world.core.definition import Definition
from living_world.managers.definition_manager import DefinitionManager
from living_world.managers.entity_manager import EntityManager
from living_world.managers.event_manager import EventManager
from living_world.state.world_state import WorldState


def make_actions() -> tuple[ActionOption, ...]:
    return (
        ActionOption("wait", "Wait quietly."),
        ActionOption("inspect", "Inspect what is visible.", ("the path",)),
    )


@dataclass
class StubHandler:
    entities: EntityManager
    events: EventManager
    validation: ActionResolution = field(
        default_factory=lambda: ActionResolution(True, "The action is valid.")
    )
    application: ActionResolution = field(
        default_factory=lambda: ActionResolution(True, "The action was applied.")
    )
    apply_calls: int = 0

    def supports(self, action_key: str) -> bool:
        return action_key == "wait"

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        return self.validation

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        self.apply_calls += 1
        self.entities.set_attribute(entity_id=actor_id, key="waited", value=True)
        self.events.record(kind="npc_waited", subject_id=actor_id)
        return self.application


def make_handler() -> tuple[WorldState, str, StubHandler]:
    state = WorldState()
    definitions = DefinitionManager()
    definitions.register(Definition(key="npc", initial_attributes={}))
    entities = EntityManager(state, definitions)
    actor = entities.create(definition_key="npc", name="Erik")
    handler = StubHandler(entities, EventManager(state))
    return state, actor.id, handler


def make_untrusted_request(
    *,
    action_key: object,
    target_label: object,
    rationale: object,
    arguments: object,
) -> ActionRequest:
    """Construct malformed external input that bypasses value-object checks."""

    request = object.__new__(ActionRequest)
    object.__setattr__(request, "action_key", action_key)
    object.__setattr__(request, "target_label", target_label)
    object.__setattr__(request, "rationale", rationale)
    object.__setattr__(request, "arguments", arguments)
    return request


def test_valid_handler_mutates_through_manager_and_records_one_event() -> None:
    state, actor_id, handler = make_handler()
    resolver = NPCActionResolver(make_actions(), (handler,))

    result = resolver.resolve(
        actor_id=actor_id,
        request=ActionRequest("wait", None, "I should pause."),
    )

    assert result == ActionResolution(True, "The action was applied.")
    assert state.entities[actor_id].attributes["waited"] is True
    assert next(iter(state.events.values())).kind == "npc_waited"
    assert len(state.events) == 1


def test_rejected_validation_does_not_apply_or_record_an_event() -> None:
    state, actor_id, handler = make_handler()
    handler.validation = ActionResolution(False, "The action is not allowed now.")

    result = NPCActionResolver(make_actions(), (handler,)).resolve(
        actor_id=actor_id,
        request=ActionRequest("wait", None, "I should pause."),
    )

    assert result == handler.validation
    assert handler.apply_calls == 0
    assert state.entities[actor_id].attributes == {}
    assert state.events == {}


@pytest.mark.parametrize(
    "proposal",
    [
        ActionRequest("unknown", None, "I should pause."),
        ActionRequest("wait", "the path", "I should pause."),
        ActionRequest("inspect", "unknown", "I should pause."),
        make_untrusted_request(
            action_key="inspect",
            target_label="entity_000001",
            rationale="I should pause.",
            arguments={},
        ),
        make_untrusted_request(
            action_key="wait",
            target_label=None,
            rationale="I should pause.",
            arguments={"manner": 1},
        ),
        object(),
    ],
)
def test_untrusted_or_unsupported_request_cannot_mutate(
    proposal: object,
) -> None:
    state, actor_id, handler = make_handler()

    result = NPCActionResolver(make_actions(), (handler,)).resolve(
        actor_id=actor_id,
        request=proposal,  # type: ignore[arg-type]
    )

    assert result.accepted is False
    assert handler.apply_calls == 0
    assert state.entities[actor_id].attributes == {}
    assert state.events == {}


def test_rejected_application_is_a_handler_contract_violation() -> None:
    state, actor_id, handler = make_handler()
    handler.application = ActionResolution(False, "This must not be returned.")

    with pytest.raises(NPCActionHandlerContractError, match="cannot reject"):
        NPCActionResolver(make_actions(), (handler,)).resolve(
            actor_id=actor_id,
            request=ActionRequest("wait", None, "I should pause."),
        )

    assert len(state.events) == 1
