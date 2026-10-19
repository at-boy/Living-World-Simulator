"""Fixed version-one canonical policy; public labels never contain engine IDs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import ClassVar

from living_world.npc.identity import NPCIdentity
from living_world.scenarios.scenario import LoadedScenario, mutable_attributes
from living_world.spatial.model import Bounds, BoundsKind, OverlapPolicy, Point


class FoundersOutcome(StrEnum):
    SUCCESS = "success"
    STALL = "stall"
    FAILURE = "failure"


class FoundersConfigurationError(ValueError):
    _MESSAGES: ClassVar[dict[str, str]] = {
        "invalid_policy": "Invalid founders policy.",
        "setup_mismatch": "Founders setup does not match.",
        "missing_tape": "Founders run requires a proposal tape.",
    }

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code + ": " + self._MESSAGES[code])


@dataclass(frozen=True, slots=True)
class FoundersRules:
    deadline_tick: int = 12
    need_window_ticks: int = 3
    need_duration_ticks: int = 3
    need_requirement_per_person: int = 1
    need_secure_maximum: float = 0.0
    need_strained_maximum: float = 0.5
    food_per_person_per_tick: int = 1
    water_per_person_per_tick: int = 1
    food_work_quantity: int = 10
    water_work_quantity: int = 8
    required_progress: int = 1
    normal_labor: int = 1
    modest_shelter_count: int = 1
    modest_shelter_timber: int = 2
    large_shelter_count: int = 2
    large_shelter_labor: int = 3
    large_shelter_timber: int = 4
    storage_count: int = 1
    storage_timber: int = 2
    housing_capacity: int = 2
    storage_capacity: int = 20
    maintenance_initial_condition: int = 3
    maintenance_maximum_condition: int = 3
    maintenance_minimum_condition: int = 2
    maintenance_deterioration: int = 1
    maintenance_recovery: int = 1
    maintenance_food_upkeep: int = 1
    storage_spoilage_per_tick: int = 0
    town_population: int = 3
    homeland_capacity: int = 1
    homeland_delay_ticks: int = 2
    homeland_cost_per_unit: int = 0
    homeland_reliability: float = 1.0
    homeland_allowed_imports: tuple[str, ...] = ("timber",)
    homeland_allowed_exports: tuple[str, ...] = ("food",)
    dispatch_quantity: int = 1


@dataclass(frozen=True, slots=True)
class FoundersPlacement:
    label: str
    geometry: Point | Bounds
    containing_label: str | None = None
    bounds_kind: BoundsKind | None = None
    overlap_policy: OverlapPolicy = OverlapPolicy.REJECT


@dataclass(frozen=True, slots=True)
class FoundersPolicy:
    version: int
    area_label: str
    founder_labels: tuple[str, ...]
    rules: FoundersRules
    placements: tuple[FoundersPlacement, ...]

    def to_manifest(self) -> dict[str, object]:
        try:
            placements: dict[str, object] = {}
            for entry in self.placements:
                geometry = asdict(entry.geometry)
                geometry["kind"] = (
                    "point" if isinstance(entry.geometry, Point) else "bounds"
                )
                placements[entry.label] = {
                    "geometry": geometry,
                    "containing_label": entry.containing_label,
                    "bounds_kind": (
                        None if entry.bounds_kind is None else entry.bounds_kind.value
                    ),
                    "overlap_policy": entry.overlap_policy.value,
                }
            normalized = _canonical(
                {
                    "version": self.version,
                    "area_label": self.area_label,
                    "founder_labels": self.founder_labels,
                    "rules": asdict(self.rules),
                    "placements": placements,
                }
            )
            # Validate UTF8 here too: callers may request a manifest without a digest.
            return json.loads(normalized.encode("utf-8", "strict"))
        except (
            TypeError,
            ValueError,
            KeyError,
            UnicodeError,
            RecursionError,
            AttributeError,
        ):
            raise FoundersConfigurationError("invalid_policy") from None

    @property
    def fingerprint(self) -> str:
        try:
            return hashlib.sha256(
                _canonical(self.to_manifest()).encode("utf-8", "strict")
            ).hexdigest()
        except (TypeError, ValueError, UnicodeError, RecursionError):
            raise FoundersConfigurationError("invalid_policy") from None

    @classmethod
    def from_scenario(cls, scenario: LoadedScenario) -> FoundersPolicy:
        try:
            expected = canonical_policy()
            if (
                scenario.key != "canonical_founders_v1"
                or scenario.schema_version != 1
                or scenario.seed != 42
                or scenario.default_max_ticks != 16
                or scenario.terminal_conditions
                != ("founding_failure", "settlement_success")
                or tuple((e.label, e.definition_key) for e in scenario.entities)
                != (
                    ("valley", "area"),
                    ("camp", "settlement"),
                    ("ada", "founder"),
                    ("bryn", "founder"),
                )
                or scenario.relationships
            ):
                raise ValueError
            attrs = mutable_attributes(scenario.entities[1].attributes)
            if _canonical(attrs.get("founders_policy")) != _canonical(
                expected.to_manifest()
            ):
                raise ValueError
            if _canonical(attrs.get("resources")) != _canonical(
                {"food": 0, "water": 0, "timber": 10}
            ):
                raise ValueError
            if type(attrs.get("population")) is not int or attrs["population"] != 2:
                raise ValueError
            if _canonical(attrs.get("production_inputs")) != _canonical(
                {"food": 1}
            ) or _canonical(attrs.get("production_outputs")) != _canonical(
                {"food": 4, "water": 2}
            ):
                raise ValueError
            for name in ("housing_capacity", "storage_capacity"):
                if type(attrs.get(name)) is not int or attrs[name] != 0:
                    raise ValueError
            for entity in scenario.entities[2:]:
                NPCIdentity.from_attribute(
                    mutable_attributes(entity.attributes).get("npc_identity")
                )
            if len({e.name for e in scenario.entities[2:]}) != 2:
                raise ValueError
            return expected
        except (TypeError, ValueError, KeyError, UnicodeError, RecursionError):
            raise FoundersConfigurationError("invalid_policy") from None


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_policy() -> FoundersPolicy:
    return FoundersPolicy(
        1,
        "valley",
        ("ada", "bryn"),
        FoundersRules(),
        (
            FoundersPlacement(
                "valley", Bounds(-10, -10, 40, 40), bounds_kind=BoundsKind.AREA
            ),
            FoundersPlacement("camp", Bounds(0, 0, 12, 8), "valley", BoundsKind.AREA),
            FoundersPlacement("ada", Point(1, 1), "camp"),
            FoundersPlacement("bryn", Point(2, 1), "camp"),
        ),
    )
