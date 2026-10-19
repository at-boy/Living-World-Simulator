from __future__ import annotations

import re
from dataclasses import dataclass

from living_world.cognition.action_resolution import ActionResolution
from living_world.cognition.npc_cognition_client import ActionOption, ActionRequest
from living_world.external_world.dispatch import DispatchDirection, ExternalDispatch
from living_world.external_world.dispatch_manager import ExternalDispatchManager

DISPATCH_ACTION_KEY = "dispatch_external_trade"
_INTERNAL_ID = re.compile(
    r"(?:entity|relationship|event|observation|belief|experience|memory|"
    r"knowledge|npc_relationship|external_reference|external_dispatch)_\d+"
)


@dataclass(frozen=True, slots=True)
class DispatchOffer:
    label: str
    reference_id: str
    direction: DispatchDirection
    good: str
    quantity: int

    def __post_init__(self) -> None:
        for name in ("label", "reference_id", "good"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            if not value.strip():
                raise ValueError(f"{name} cannot be empty.")
        if not isinstance(self.direction, DispatchDirection):
            raise TypeError("direction must be a DispatchDirection.")
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool):
            raise TypeError("quantity must be an integer.")
        if self.quantity < 1:
            raise ValueError("quantity must be positive.")
        if _INTERNAL_ID.search(self.label):
            raise ValueError("label cannot contain an internal ID.")


class ExternalDispatchActionHandler:
    """Resolve only engine-authored qualitative labels to dispatch policy."""

    def __init__(
        self, manager: ExternalDispatchManager, offers: tuple[DispatchOffer, ...]
    ) -> None:
        if not isinstance(offers, tuple) or not all(
            isinstance(offer, DispatchOffer) for offer in offers
        ):
            raise TypeError("offers must be a tuple of DispatchOffer values.")
        labels = tuple(offer.label for offer in offers)
        if len(labels) != len(set(labels)):
            raise ValueError("offer labels must be unique.")
        self._manager = manager
        self._offers = {offer.label: offer for offer in offers}
        self._created: ExternalDispatch | None = None

    @property
    def action_option(self) -> ActionOption:
        return ActionOption(
            key=DISPATCH_ACTION_KEY,
            description="Propose one of the offered external exchanges.",
            target_labels=tuple(self._offers),
        )

    @property
    def last_created(self) -> ExternalDispatch | None:
        return self._created

    def supports(self, action_key: str) -> bool:
        return action_key == DISPATCH_ACTION_KEY

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        offer = self._offers.get(request.target_label or "")
        if request.action_key != DISPATCH_ACTION_KEY or offer is None:
            return ActionResolution(False, "Dispatch proposal is not offered.")
        if request.arguments:
            return ActionResolution(
                False, "Dispatch proposal cannot set policy values."
            )
        try:
            self._manager.validate_create(
                source_entity_id=actor_id,
                reference_id=offer.reference_id,
                direction=offer.direction,
                good=offer.good,
                quantity=offer.quantity,
            )
        except (TypeError, ValueError) as exc:
            return ActionResolution(False, str(exc))
        return ActionResolution(True, "Dispatch proposal is valid.")

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        offer = self._offers[request.target_label or ""]
        self._created = self._manager.create(
            source_entity_id=actor_id,
            reference_id=offer.reference_id,
            direction=offer.direction,
            good=offer.good,
            quantity=offer.quantity,
        )
        return ActionResolution(True, "Dispatch was created through the manager.")
