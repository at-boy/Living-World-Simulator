"""Holder-scoped qualitative founders feedback on detached runtime candidates."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import cast
from weakref import WeakKeyDictionary

from living_world.api.inspection import EngineWorldInspector
from living_world.archives import Checkpoint, JournalEntry
from living_world.archives.model import canonical
from living_world.cognition.action_resolution import NPCActionHandler
from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.local_llm_cognition_format import serialize_decision_request
from living_world.cognition.npc_cognition_client import ActionOption
from living_world.cognition.npc_context import NPCContext, NPCContextAssembler
from living_world.cognition.retrieval import RetrievalQuery, RetrievedCognition
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.observation import Observation
from living_world.founders.model import canonical_policy
from living_world.founders.runtime import FoundersLiveOfferProvider
from living_world.founders.setup import FoundersSetupManager
from living_world.goals.model import GoalOwnerKind
from living_world.npc.identity import NPCIdentity
from living_world.repositories.world_snapshot import decode_world, encode_world
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.state.world_state import WorldState


class RuntimePreparationError(ValueError):
    """Safe classified preparation failure; never carries source prose."""

    def __init__(self, code: str) -> None:
        if code not in {
            "invalid_feedback",
            "invalid_cursor",
            "invalid_outcomes",
            "context_budget_exceeded",
            "invalid_request_size",
            "candidate_mismatch",
        }:
            code = "invalid_feedback"
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DecisionInput:
    actor_id: str
    actor_label: str
    context: NPCContext
    options: tuple[ActionOption, ...]
    handlers: tuple[NPCActionHandler, ...]
    input_fingerprint: str

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.actor_id, self.actor_label)
        ):
            raise RuntimePreparationError("invalid_feedback")
        if (
            not isinstance(self.context, NPCContext)
            or type(self.options) is not tuple
            or any(not isinstance(item, ActionOption) for item in self.options)
        ):
            raise RuntimePreparationError("invalid_feedback")
        if type(self.handlers) is not tuple or any(
            not all(
                callable(getattr(item, method, None))
                for method in ("supports", "validate", "apply")
            )
            for item in self.handlers
        ):
            raise RuntimePreparationError("invalid_feedback")
        if (
            not isinstance(self.input_fingerprint, str)
            or re.fullmatch("[0-9a-f]{64}", self.input_fingerprint) is None
        ):
            raise RuntimePreparationError("invalid_feedback")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _empty() -> dict[str, object]:
    return {
        "format": 1,
        "mode": "founders_feedback",
        "holders": {},
        "pending_results": [],
    }


def _inside(engine: SimulationEngine, entity_id: str, camp: str) -> bool:
    state = engine.state
    camp_entity, camp_placement = state.entities.get(camp), state.placements.get(camp)
    if (
        camp_entity is None
        or camp_entity.destroyed_tick is not None
        or camp_placement is None
        or camp_placement.geometry is None
    ):
        return False
    current: str | None = entity_id
    seen: set[str] = set()
    while current is not None and current not in seen:
        entity, placement = state.entities.get(current), state.placements.get(current)
        if (
            entity is None
            or entity.destroyed_tick is not None
            or placement is None
            or placement.geometry is None
        ):
            return False
        if current == camp:
            return True
        seen.add(current)
        current = placement.containing_entity_id
    return False


class _HolderRetriever:
    """Explicit memory-only fixed policy, independent of generic retrieval defaults."""

    def __init__(self, holder: str, records: tuple[Memory, ...]) -> None:
        self._holder, self.records = holder, records

    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedCognition, ...]:
        if query.holder_id != self._holder:
            raise RuntimePreparationError("invalid_feedback")
        return tuple(
            RetrievedCognition(
                "memory", item.summary, item.salience.importance, item.salience.is_core
            )
            for item in self.records
            if item.salience.is_core
        )


@dataclass(frozen=True, slots=True)
class _Stage:
    base_revision: int
    tick: int
    base_identity: str
    prepared_digest: str
    actors: tuple[str, ...]
    cursor_json: str


class FoundersFeedback:
    def __init__(
        self, request_size: Callable[[NPCContext, tuple[ActionOption, ...]], int]
    ) -> None:
        if not callable(request_size):
            raise TypeError("Expected request size function.")
        self._request_size = request_size
        self._staged: WeakKeyDictionary[SimulationEngine, _Stage] = WeakKeyDictionary()

    def _cursor(self, value: Mapping[str, object]) -> dict[str, object]:
        try:
            cursor = json.loads(canonical(value))
            if (
                set(cursor) != {"format", "mode", "holders", "pending_results"}
                or type(cursor["format"]) is not int
                or cursor["format"] != 1
                or cursor["mode"] != "founders_feedback"
            ):
                raise ValueError
            holders, pending = cursor["holders"], cursor["pending_results"]
            if type(holders) is not dict or type(pending) is not list:
                raise ValueError
            for label, holder in holders.items():
                if (
                    label not in canonical_policy().founder_labels
                    or type(holder) is not dict
                    or set(holder) != {"sources"}
                    or type(holder["sources"]) is not dict
                ):
                    raise ValueError
                for kind, sources in holder["sources"].items():
                    if (
                        kind not in ("mandate", "need", "work")
                        or type(sources) is not dict
                    ):
                        raise ValueError
                    for key, digest in sources.items():
                        if (
                            not isinstance(key, str)
                            or not key.strip()
                            or not isinstance(digest, str)
                            or re.fullmatch("[0-9a-f]{64}", digest) is None
                        ):
                            raise ValueError
            seen: set[tuple[int, str]] = set()
            for result in pending:
                if (
                    type(result) is not dict
                    or set(result) != {"actor_label", "source_tick", "outcome"}
                    or result["actor_label"] not in canonical_policy().founder_labels
                    or type(result["source_tick"]) is not int
                    or result["source_tick"] < 0
                    or result["outcome"] not in ("accepted", "rejected", "no_action")
                ):
                    raise ValueError
                key = (result["source_tick"], result["actor_label"])
                if key in seen:
                    raise ValueError
                seen.add(key)
            cursor["holders"] = {
                label: {
                    "sources": {
                        kind: dict(sorted(sources.items()))
                        for kind, sources in sorted(holder["sources"].items())
                    }
                }
                for label, holder in sorted(holders.items())
            }
            cursor["pending_results"] = sorted(
                pending, key=lambda item: (item["source_tick"], item["actor_label"])
            )
            return cast(dict[str, object], cursor)
        except Exception:  # noqa: BLE001
            raise RuntimePreparationError("invalid_cursor") from None

    def _validate_provenance(
        self, state: WorldState, cursor: dict[str, object], tick: int
    ) -> None:
        holders = cast(
            dict[str, dict[str, dict[str, dict[str, str]]]], cursor["holders"]
        )
        for label, holder in holders.items():
            actor = state.scenario_entity_bindings[label]
            for kind, sources in holder["sources"].items():
                if kind == "mandate" and set(sources) != {"goal_founding"}:
                    raise RuntimePreparationError("invalid_cursor")
                for key, digest in sources.items():
                    observations = [
                        item
                        for item in (
                            item
                            for item in state.observations.values()
                            if item.observer == actor
                        )
                        if item.evidence.get("source_kind") == kind
                        and item.evidence.get("source_id") == key
                        and item.evidence.get("qualitative_hash") == digest
                        and _hash(item.description) == digest
                        and item.tick <= tick
                    ]
                    if not any(
                        memory.holder_id == actor
                        and memory.summary == observation.description
                        and observation.id in memory.source_observation_ids
                        and memory.subject_id == observation.subject
                        for observation in observations
                        for memory in (
                            item
                            for item in state.memories.values()
                            if item.holder_id == actor
                        )
                    ):
                        raise RuntimePreparationError("invalid_cursor")
        # The cursor is the latest source boundary, not an arbitrary historical
        # subset. Missing holders/sources must never silently reset communication.
        by_actor = {
            state.scenario_entity_bindings[label]: label
            for label in canonical_policy().founder_labels
        }
        latest: dict[tuple[str, str, str], Observation] = {}
        for observation in state.observations.values():
            label = by_actor.get(observation.observer)
            kind, key = observation.evidence.get(
                "source_kind"
            ), observation.evidence.get("source_id")
            if (
                label is None
                or kind not in ("mandate", "need", "work")
                or not isinstance(key, str)
            ):
                continue
            source = (label, cast(str, kind), key)
            previous = latest.get(source)
            if previous is None or (observation.tick, observation.id) > (
                previous.tick,
                previous.id,
            ):
                latest[source] = observation
        for (label, kind, key), observation in latest.items():
            recorded = holders.get(label, {}).get("sources", {}).get(kind, {}).get(key)
            if recorded != _hash(observation.description) or observation.tick > tick:
                raise RuntimePreparationError("invalid_cursor")
        for result in cast(list[dict[str, object]], cursor["pending_results"]):
            actor = state.scenario_entity_bindings[cast(str, result["actor_label"])]
            if cast(int, result["source_tick"]) >= tick or any(
                observation.observer == actor
                and observation.evidence.get("source_kind") == "result"
                and observation.evidence.get("source_id") == str(result["source_tick"])
                for observation in state.observations.values()
            ):
                raise RuntimePreparationError("invalid_cursor")

    def _actors(
        self, engine: SimulationEngine
    ) -> tuple[tuple[str, str, NPCIdentity], ...]:
        policy = canonical_policy()
        FoundersSetupManager(engine.state, engine.definitions).validate_live(policy)
        camp = engine.state.scenario_entity_bindings["camp"]
        actors = []
        for label in sorted(policy.founder_labels):
            actor_id = engine.state.scenario_entity_bindings.get(label)
            actor = engine.state.entities.get(actor_id or "")
            if (
                actor is None
                or actor.destroyed_tick is not None
                or not _inside(engine, actor.id, camp)
            ):
                continue
            identity = NPCIdentity.from_attribute(actor.attributes.get("npc_identity"))
            actors.append((label, actor.id, identity))
        return tuple(actors)

    def _sources(
        self, engine: SimulationEngine
    ) -> tuple[tuple[str, str, str, str], ...]:
        state = engine.state
        camp = state.scenario_entity_bindings["camp"]
        goal = state.goal_definitions["goal_founding"]
        if goal.owner_kind is not GoalOwnerKind.SETTLEMENT or goal.owner_id != camp:
            raise RuntimePreparationError("invalid_feedback")
        boundary = NPCInformationBoundary(state)
        projection = engine.goals.npc_interpretation(goal.id)
        boundary.validate_conversation_prose(projection.label)
        boundary.validate_conversation_prose(projection.description)
        sources = [
            (
                "mandate",
                goal.id,
                camp,
                f"You were asked to help the camp: {projection.description}",
            )
        ]
        for key, need in sorted(state.need_definitions.items()):
            if need.owner_id == camp:
                projection = engine.needs.npc_interpretation(key)
                boundary.validate_conversation_prose(projection.label)
                boundary.validate_conversation_prose(projection.description)
                sources.append(
                    ("need", key, camp, f"{projection.label}: {projection.description}")
                )
        for key, work in sorted(state.work_definitions.items()):
            if work.settlement_id == camp and _inside(engine, work.location_id, camp):
                projection = engine.work.npc_interpretation(key)
                boundary.validate_conversation_prose(projection.label)
                boundary.validate_conversation_prose(projection.description)
                sources.append(
                    (
                        "work",
                        key,
                        work.location_id,
                        f"{projection.label}: {projection.description}",
                    )
                )
        for _, _, _, prose in sources:
            boundary.validate_conversation_prose(prose)
        return tuple(sources)

    def _record(
        self,
        engine: SimulationEngine,
        actor: str,
        kind: str,
        key: str,
        subject: str,
        prose: str,
        prior_observations: frozenset[str],
    ) -> Observation:
        boundary = NPCInformationBoundary(engine.state)
        boundary.validate_conversation_prose(prose)
        provenance: dict[str, object] = {
            "source_kind": kind,
            "source_id": key,
            "qualitative_hash": _hash(prose),
        }
        # A repeat prepare on the very same detached candidate is idempotent.
        existing = [
            item
            for item in engine.observations.observations_for(actor)
            if item.tick == engine.state.tick
            and item.id not in prior_observations
            and dict(item.evidence) == provenance
            and item.description == prose
        ]
        if existing:
            observation = max(existing, key=lambda item: item.id)
        else:
            observation = engine.observations.record(
                observer=actor,
                subject=subject,
                description=prose,
                confidence=1.0,
                evidence=provenance,
            )
        if not engine.memories.has_observation_provenance(actor, observation.id):
            engine.memories.record(
                holder_id=actor,
                subject_id=subject,
                summary=prose,
                salience=CognitiveSalience(
                    0.8 if kind == "mandate" else 0.6, kind == "mandate"
                ),
                source_observation_ids=(observation.id,),
            )
        return observation

    def _observe(
        self,
        engine: SimulationEngine,
        cursor: dict[str, object],
        prior_observations: frozenset[str] = frozenset(),
    ) -> dict[str, tuple[Observation, ...]]:
        sources = self._sources(engine)
        holders = cast(
            dict[str, dict[str, dict[str, dict[str, str]]]], cursor["holders"]
        )
        pending = cast(list[dict[str, object]], cursor["pending_results"])
        current: dict[str, tuple[Observation, ...]] = {}
        consumed: list[dict[str, object]] = []
        for label, actor, _ in self._actors(engine):
            fingerprints = holders.setdefault(label, {"sources": {}})["sources"]
            visible: list[Observation] = []
            for kind, key, subject, prose in sources:
                known = fingerprints.setdefault(kind, {})
                digest = _hash(prose)
                if key not in known or (kind != "mandate" and known[key] != digest):
                    self._record(
                        engine, actor, kind, key, subject, prose, prior_observations
                    )
                    known[key] = digest
                matches = [
                    item
                    for item in engine.observations.observations_for(actor)
                    if item.evidence.get("source_kind") == kind
                    and item.evidence.get("source_id") == key
                    and item.evidence.get("qualitative_hash") == known[key]
                ]
                if not matches:
                    raise RuntimePreparationError("invalid_cursor")
                visible.append(min(matches, key=lambda item: (-item.tick, item.id)))
            for result in pending:
                if result["actor_label"] != label:
                    continue
                prose = {
                    "accepted": "Your proposal was accepted.",
                    "rejected": "Your proposal could not be carried out.",
                    "no_action": "You chose not to propose an action.",
                }[str(result["outcome"])]
                visible.append(
                    self._record(
                        engine,
                        actor,
                        "result",
                        str(result["source_tick"]),
                        actor,
                        prose,
                        prior_observations,
                    )
                )
                consumed.append(result)
            current[label] = tuple(
                sorted(visible, key=lambda item: (-item.tick, item.id))[:8]
            )
        cursor["pending_results"] = [item for item in pending if item not in consumed]
        return current

    def initialize(self, candidate: SimulationEngine) -> Mapping[str, object]:
        try:
            cursor = _empty()
            self._observe(candidate, cursor)
            return self._cursor(cursor)
        except RuntimePreparationError:
            raise
        except Exception:  # noqa: BLE001
            raise RuntimePreparationError("invalid_feedback") from None

    def _context(
        self,
        engine: SimulationEngine,
        actor: str,
        identity: NPCIdentity,
        observations: tuple[Observation, ...],
        options: tuple[ActionOption, ...],
    ) -> NPCContext:
        memories = engine.memories.memories_for(actor)
        mandates = [
            memory
            for memory in memories
            if memory.salience.is_core
            and any(
                engine.state.observations[key].observer == actor
                and engine.state.observations[key].evidence.get("source_kind")
                == "mandate"
                and engine.state.observations[key].evidence.get("source_id")
                == "goal_founding"
                and engine.state.observations[key].description == memory.summary
                for key in memory.source_observation_ids
                if key in engine.state.observations
            )
        ]
        if not mandates:
            raise RuntimePreparationError("invalid_feedback")
        required = min(mandates, key=lambda item: (item.tick, item.id))
        selected = (required,) + tuple(
            sorted(
                (item for item in memories if item.id != required.id),
                key=lambda item: (-item.salience.importance, -item.tick, item.id),
            )[:7]
        )
        assembler = NPCContextAssembler(
            engine.state, retriever=_HolderRetriever(actor, selected)
        )
        shell = assembler.assemble(
            holder_id=actor,
            capability_descriptions=(identity.description,)
            + identity.capability_descriptions,
            max_perceptions=0,
        )
        perceptions = list(observations)
        optional = list(selected[1:])
        while True:
            records = (required,) + tuple(optional)
            context = replace(
                shell,
                current_perceptions=tuple(item.description for item in perceptions),
                core_cognition=tuple(
                    RetrievedCognition(
                        "memory", item.summary, item.salience.importance, True
                    )
                    for item in records
                    if item.salience.is_core
                ),
                retrieved_information=tuple(
                    RetrievedCognition(
                        "memory", item.summary, item.salience.importance, False
                    )
                    for item in records
                    if not item.salience.is_core
                ),
            )
            NPCInformationBoundary(engine.state).validate_context(context)
            boundary = NPCInformationBoundary(engine.state)
            for option in options:
                boundary.validate_conversation_prose(option.key)
                boundary.validate_conversation_prose(option.description)
                for label in option.target_labels:
                    boundary.validate_conversation_prose(label)
            serialize_decision_request(context, options)
            size = self._request_size(context, options)
            if type(size) is not int or size < 0:
                raise RuntimePreparationError("invalid_request_size")
            if size <= 16000:
                return context
            candidates = [(item.tick, item.id, 0, item) for item in perceptions] + [
                (item.tick, item.id, 1, item) for item in optional
            ]
            if not candidates:
                raise RuntimePreparationError("context_budget_exceeded")
            _, _, kind, oldest = min(candidates, key=lambda item: item[:3])
            if kind == 0:
                perceptions.remove(oldest)
            else:
                optional.remove(oldest)

    def prepare(
        self, candidate: SimulationEngine, base: Checkpoint
    ) -> tuple[DecisionInput, ...]:
        try:
            cursor = self._cursor(base.feedback_cursor)
            base_state = decode_world(base.snapshot)
            self._validate_provenance(base_state, cursor, base_state.tick)
            identity = _hash(
                canonical(
                    {
                        "snapshot": base.snapshot.digest,
                        "driver": base.driver_cursor,
                        "feedback": base.feedback_cursor,
                    }
                )
            )
            staged = self._staged.get(candidate)
            actual = encode_world(candidate.state)
            if (staged is None and actual != base.snapshot) or (
                staged is not None
                and (
                    staged.base_identity != identity
                    or staged.base_revision != base.revision
                    or staged.prepared_digest != actual.digest
                )
            ):
                raise RuntimePreparationError("candidate_mismatch")
            current = self._observe(
                candidate, cursor, frozenset(base_state.observations)
            )
            decisions = []
            for label, actor, npc_identity in self._actors(candidate):
                offers = FoundersLiveOfferProvider(
                    candidate, canonical_policy()
                ).offers(actor_id=actor, inspector=EngineWorldInspector(candidate))
                context = self._context(
                    candidate, actor, npc_identity, current[label], offers.options
                )
                fingerprint = _hash(
                    canonical(
                        {
                            "input": serialize_decision_request(
                                context, offers.options
                            ),
                            "base": identity,
                        }
                    )
                )
                decisions.append(
                    DecisionInput(
                        actor,
                        label,
                        context,
                        offers.options,
                        offers.handlers,
                        fingerprint,
                    )
                )
            self._staged[candidate] = _Stage(
                base.revision,
                candidate.state.tick,
                identity,
                encode_world(candidate.state).digest,
                tuple(item.actor_label for item in decisions),
                canonical(self._cursor(cursor)),
            )
            return tuple(decisions)
        except RuntimePreparationError:
            raise
        except Exception:  # noqa: BLE001
            raise RuntimePreparationError("invalid_feedback") from None

    def after_tick(
        self, candidate: SimulationEngine, outcomes: tuple[JournalEntry, ...]
    ) -> Mapping[str, object]:
        try:
            stage = self._staged.get(candidate)
            if (
                stage is None
                or candidate.state.tick != stage.tick + 1
                or type(outcomes) is not tuple
                or len(outcomes) != len(stage.actors)
            ):
                raise ValueError
            cursor = self._cursor(json.loads(stage.cursor_json))
            pending = cast(list[dict[str, object]], cursor["pending_results"])
            seen: set[str] = set()
            for entry in outcomes:
                if (
                    not isinstance(entry, JournalEntry)
                    or entry.kind != "action_resolved"
                ):
                    raise ValueError
                JournalEntry(entry.kind, entry.payload)
                payload = entry.payload
                label = payload["actor_label"]
                if (
                    payload["base_revision"] != stage.base_revision
                    or payload["source_tick"] != stage.tick
                    or label not in stage.actors
                    or label in seen
                    or any(
                        key not in candidate.state.events
                        or candidate.state.events[key].tick != stage.tick
                        for key in payload["event_references"]
                    )
                ):
                    raise ValueError
                seen.add(label)
                pending.append(
                    {
                        "actor_label": label,
                        "source_tick": stage.tick,
                        "outcome": payload["outcome"],
                    }
                )
            result = self._cursor(cursor)
            del self._staged[candidate]
            return result
        except Exception:  # noqa: BLE001
            raise RuntimePreparationError("invalid_outcomes") from None
