"""Simulation-owned gateway for applying validated NPC action proposals."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from living_world.cognition.npc_cognition_client import ActionOption, ActionRequest


@dataclass(frozen=True, slots=True)
class ActionResolution:
    """The authoritative gateway result for one proposed NPC action."""

    accepted: bool
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be a bool.")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string.")
        if not self.reason.strip():
            raise ValueError("reason cannot be empty.")


class NPCActionHandler(Protocol):
    """Domain-specific action validation and application boundary."""

    def supports(self, action_key: str) -> bool:
        """Return whether this handler owns the offered action key."""

    def validate(
        self,
        *,
        actor_id: str,
        request: ActionRequest,
    ) -> ActionResolution:
        """Validate without mutating state or recording an event."""

    def apply(
        self,
        *,
        actor_id: str,
        request: ActionRequest,
    ) -> ActionResolution:
        """Apply one previously accepted request through domain managers."""


class NPCActionHandlerContractError(RuntimeError):
    """Raised when a handler violates the validation-before-application protocol."""


class NPCActionResolver:
    """Validate offered vocabulary then dispatch only to a domain handler."""

    def __init__(
        self,
        actions: tuple[ActionOption, ...],
        handlers: tuple[NPCActionHandler, ...] = (),
    ) -> None:
        _validate_actions(actions)
        _validate_handlers(handlers)
        self._actions = actions
        self._handlers = handlers

    def resolve(
        self,
        *,
        actor_id: str,
        request: ActionRequest,
    ) -> ActionResolution:
        """Validate and apply a proposal without granting it action authority."""

        if not isinstance(actor_id, str):
            raise TypeError("actor_id must be a string.")
        if not actor_id.strip():
            raise ValueError("actor_id cannot be empty.")
        if not isinstance(request, ActionRequest):
            return ActionResolution(False, "Action request has an invalid shape.")
        if not _request_is_offered(request, self._actions):
            return ActionResolution(
                False, "Action request is outside offered vocabulary."
            )

        handler = next(
            (
                candidate
                for candidate in self._handlers
                if candidate.supports(request.action_key)
            ),
            None,
        )
        if handler is None:
            return ActionResolution(False, "No handler supports the requested action.")

        validation = handler.validate(actor_id=actor_id, request=request)
        if not isinstance(validation, ActionResolution):
            return ActionResolution(
                False, "Handler validation violated the action contract."
            )
        if not validation.accepted:
            return validation

        application = handler.apply(actor_id=actor_id, request=request)
        if not isinstance(application, ActionResolution):
            raise NPCActionHandlerContractError(
                "Handler application must return an ActionResolution."
            )
        if not application.accepted:
            raise NPCActionHandlerContractError(
                "Handler application cannot reject an action after validation accepted it."
            )
        return application


def _validate_actions(actions: object) -> None:
    if not isinstance(actions, tuple):
        raise TypeError("actions must be a tuple of ActionOption values.")
    if not all(isinstance(action, ActionOption) for action in actions):
        raise TypeError("actions must contain only ActionOption values.")
    keys = tuple(action.key for action in actions)
    if len(keys) != len(set(keys)):
        raise ValueError("actions must have unique keys.")


def _validate_handlers(handlers: object) -> None:
    if not isinstance(handlers, tuple):
        raise TypeError("handlers must be a tuple of NPCActionHandler values.")
    for handler in handlers:
        if not all(
            callable(getattr(handler, method_name, None))
            for method_name in ("supports", "validate", "apply")
        ):
            raise TypeError(
                "handlers must provide supports, validate, and apply methods."
            )


def _request_is_offered(
    request: ActionRequest,
    actions: tuple[ActionOption, ...],
) -> bool:
    if not isinstance(request.action_key, str) or not request.action_key.strip():
        return False
    if request.target_label is not None and (
        not isinstance(request.target_label, str) or not request.target_label.strip()
    ):
        return False
    if not isinstance(request.rationale, str) or not request.rationale.strip():
        return False
    if not isinstance(request.arguments, Mapping) or any(
        not isinstance(key, str)
        or not key.strip()
        or not isinstance(value, str)
        or not value.strip()
        for key, value in request.arguments.items()
    ):
        return False
    option = next(
        (action for action in actions if action.key == request.action_key), None
    )
    if option is None:
        return False
    if option.target_labels:
        return request.target_label in option.target_labels
    return request.target_label is None
