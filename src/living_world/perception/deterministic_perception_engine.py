from collections.abc import Mapping

from living_world.core.observation import Observation
from living_world.perception.perception_context import PerceptionContext


class DeterministicPerceptionEngine:
    """Produces deterministic observations from world state and capabilities."""

    def perceive(
        self,
        context: PerceptionContext,
    ) -> Observation:
        subject = context.subject
        capabilities = context.capabilities

        woodcraft = self._numeric_capability(capabilities, "woodcraft")

        growth = self._numeric_attribute(subject.attributes, "growth")
        health = self._numeric_attribute(subject.attributes, "health")

        description = self._describe_subject(
            subject.name,
            growth,
            health,
            woodcraft,
        )

        confidence = self._calculate_confidence(
            growth=growth,
            health=health,
            woodcraft=woodcraft,
        )

        evidence = {
            "subject_attributes": dict(subject.attributes),
            "observer_capabilities": dict(capabilities),
        }

        metadata = {
            "engine": "deterministic",
        }

        return Observation(
            id="",
            tick=context.tick,
            observer=context.observer.id,
            subject=subject.id,
            description=description,
            confidence=confidence,
            evidence=evidence,
            metadata=metadata,
        )

    @staticmethod
    def _numeric_capability(
        capabilities: Mapping[str, object],
        key: str,
    ) -> int:
        value = capabilities.get(key, 0)

        if isinstance(value, (int, float)):
            return int(value)

        return 0

    @staticmethod
    def _numeric_attribute(
        attributes: dict[str, object],
        key: str,
    ) -> int | None:
        value = attributes.get(key)

        if isinstance(value, (int, float)):
            return int(value)

        return None

    @staticmethod
    def _describe_subject(
        name: str,
        growth: int | None,
        health: int | None,
        woodcraft: int,
    ) -> str:
        if (
            woodcraft >= 70
            and growth is not None
            and growth >= 75
            and health is not None
            and health >= 75
        ):
            return (
                f"The {name} appears mature and healthy "
                "and looks suitable for harvesting."
            )

        if woodcraft >= 70 and growth is not None and growth >= 75:
            return f"The {name} appears mature and suitable for harvesting."

        if woodcraft >= 30 and growth is not None and growth >= 75:
            return f"The {name} appears mature."

        if woodcraft >= 30:
            return f"The {name} appears to be growing."

        return f"The {name} is a tree."

    @staticmethod
    def _calculate_confidence(
        *,
        growth: int | None,
        health: int | None,
        woodcraft: int,
    ) -> float:
        confidence = 0.3

        if growth is not None:
            confidence += 0.2

        if health is not None:
            confidence += 0.1

        confidence += min(woodcraft, 100) / 250

        return min(confidence, 1.0)
