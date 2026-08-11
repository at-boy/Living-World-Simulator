from living_world.core.entity import Entity
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


class ResourceSystem(SimulationSystem):
    """Provides generic resource quantity operations."""

    def step(self, state: WorldState) -> None:
        """
        Resource operations are invoked explicitly by other systems.

        The ResourceSystem currently performs no automatic per-tick
        behavior.
        """

    def get(
        self,
        entity: Entity,
        resource: str,
    ) -> int:
        resources = self._resources(entity)

        return self._resource_as_int(
            resources,
            resource,
            default=0,
        )

    def set(
        self,
        entity: Entity,
        resource: str,
        quantity: int,
    ) -> None:
        self._validate_quantity(quantity)
        resources = self._resources(entity)

        resources[resource] = quantity

    def add(
        self,
        entity: Entity,
        resource: str,
        amount: int,
    ) -> None:
        self._validate_amount(amount)
        quantity = self.get(
            entity,
            resource,
        )

        self.set(
            entity,
            resource,
            quantity + amount,
        )

    def remove(
        self,
        entity: Entity,
        resource: str,
        amount: int,
    ) -> None:
        self._validate_amount(amount)
        quantity = self.get(
            entity,
            resource,
        )

        if amount > quantity:
            raise ValueError("Resource quantity cannot be negative.")

        self.set(
            entity,
            resource,
            quantity - amount,
        )

    def transfer(
        self,
        source: Entity,
        target: Entity,
        resource: str,
        amount: int,
    ) -> None:
        self._validate_amount(amount)
        source_quantity = self.get(source, resource)

        if amount > source_quantity:
            raise ValueError("Resource quantity cannot be negative.")

        self.remove(
            source,
            resource,
            amount,
        )

        self.add(
            target,
            resource,
            amount,
        )

    def _resources(
        self,
        entity: Entity,
    ) -> dict[str, object]:
        resources = entity.attributes.setdefault(
            "resources",
            {},
        )

        if not isinstance(resources, dict):
            raise TypeError(
                "'resources' must be a dictionary.",
            )

        return resources

    def _resource_as_int(
        self,
        resources: dict[str, object],
        resource: str,
        *,
        default: int,
    ) -> int:
        value = resources.get(
            resource,
            default,
        )

        if not isinstance(value, int):
            raise TypeError(f"Resource '{resource}' must be an integer.")

        if value < 0:
            raise ValueError(f"Resource '{resource}' cannot be negative.")

        return value

    def _validate_quantity(self, quantity: int) -> None:
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise TypeError("Resource quantity must be an integer.")

        if quantity < 0:
            raise ValueError("Resource quantity cannot be negative.")

    def _validate_amount(self, amount: int) -> None:
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise TypeError("Resource amount must be an integer.")

        if amount < 0:
            raise ValueError("Resource amount cannot be negative.")
