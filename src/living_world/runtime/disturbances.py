"""Bounded engine-only effects on a detached completed candidate."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from living_world.archives.model import (
    ArchiveFormatError,
    AttemptConfig,
    BoundaryDisturbance,
    JournalEntry,
    integer,
    parse_boundary_disturbance,
)
from living_world.founders.runtime import founders_terminal_conditions
from living_world.simulation.simulation_engine import SimulationEngine
from living_world.work.interruption import WorkInterruptionRequest
from living_world.work.model import WorkStatus


@dataclass(frozen=True)
class PreparedBoundaryDisturbance:
    policy: BoundaryDisturbance
    request: WorkInterruptionRequest | None
    terminal_before_step: bool


def _validate_binding(
    candidate: SimulationEngine, config: AttemptConfig
) -> BoundaryDisturbance:
    policy = parse_boundary_disturbance(config.settings["boundary_disturbance"])
    metadata = candidate.state.run_metadata
    if (
        config.mode != "ollama"
        or config.settings.get("disturbance") != policy.kind
        or metadata is None
        or metadata.scenario_key != config.scenario_key
        or metadata.seed != config.seed
        or config.scenario_key != "canonical_founders_v1"
    ):
        raise ArchiveFormatError("Boundary candidate binding mismatch.")
    return policy


def _camp(candidate: SimulationEngine) -> str:
    camp = candidate.state.scenario_entity_bindings.get("camp")
    entity = candidate.entities.get(camp) if isinstance(camp, str) else None
    if (
        entity is None
        or entity.id != camp
        or entity.definition_key != "settlement"
        or entity.destroyed_tick is not None
    ):
        raise ArchiveFormatError("Boundary camp binding mismatch.")
    assert isinstance(camp, str)
    return camp


def prepare_boundary_disturbance(
    candidate: SimulationEngine, config: AttemptConfig
) -> PreparedBoundaryDisturbance | None:
    if "boundary_disturbance" not in config.settings:
        return None
    policy = _validate_binding(candidate, config)
    if policy.format != 2 or integer(candidate.state.tick) + 1 != policy.at_tick:
        return None
    camp = _camp(candidate)
    terminal = any(
        predicate(candidate) for predicate in founders_terminal_conditions().values()
    )
    request = (
        None
        if terminal
        else WorkInterruptionRequest(
            settlement_id=camp, execution_tick=candidate.state.tick
        )
    )
    candidate.configure_work_interruption(request)
    return PreparedBoundaryDisturbance(policy, request, terminal)


def apply_boundary_disturbance(
    candidate: SimulationEngine,
    config: AttemptConfig,
    *,
    base_revision: int,
    prepared: PreparedBoundaryDisturbance | None = None,
) -> tuple[JournalEntry, ...]:
    """Apply the fixed policy before commit; callers discard failed candidates."""
    integer(base_revision)
    if "boundary_disturbance" not in config.settings:
        return ()
    policy = _validate_binding(candidate, config)
    if integer(candidate.state.tick) != policy.at_tick:
        return ()
    payload: dict[str, object] = {
        "base_revision": base_revision,
        "boundary_tick": candidate.state.tick,
        "kind": policy.kind,
        "schedule_fingerprint": policy.fingerprint,
        "outcome": "terminal",
        "target_id": None,
        "resource": None,
        "quantity_before": None,
        "quantity_after": None,
        "event_references": (),
    }
    if policy.format == 2:
        camp = _camp(candidate)
        if (
            not isinstance(prepared, PreparedBoundaryDisturbance)
            or prepared.policy != policy
            or type(prepared.terminal_before_step) is not bool
        ):
            raise ArchiveFormatError(
                "Missing or inconsistent prepared boundary policy."
            )
        if prepared.terminal_before_step:
            if (
                prepared.request is not None
                or candidate.work_interruption_result is not None
            ):
                raise ArchiveFormatError("Inconsistent terminal boundary preparation.")
        else:
            expected = WorkInterruptionRequest(
                settlement_id=camp, execution_tick=policy.at_tick - 1
            )
            result = candidate.work_interruption_result
            if (
                prepared.request != expected
                or result is None
                or result.request != expected
            ):
                raise ArchiveFormatError(
                    "Missing or inconsistent work interruption result."
                )
            if result.outcome == "applied":
                definition = candidate.work.get(result.work_id)
                events = tuple(
                    candidate.state.events.get(ref) for ref in result.event_references
                )
                if (
                    definition is None
                    or definition.settlement_id != camp
                    or any(
                        event is None or event.tick != expected.execution_tick
                        for event in events
                    )
                    or tuple(event.kind for event in events)
                    not in (
                        ("work_order_blocked",),
                        ("work_reservation_released", "work_order_blocked"),
                    )
                    or events[-1].subject_id != result.work_id
                    or events[-1].attributes.get("reason")
                    != "External work interruption"
                    or (
                        len(events) == 2
                        and (
                            events[0].attributes.get("work_id") != result.work_id
                            or events[0].attributes.get("release_status") != "blocked"
                        )
                    )
                ):
                    raise ArchiveFormatError(
                        "Invalid work interruption event evidence."
                    )
            payload.update(
                outcome=result.outcome,
                target_id=result.work_id,
                event_references=result.event_references,
            )
        return (JournalEntry("boundary_disturbance", payload),)
    if any(
        predicate(candidate) for predicate in founders_terminal_conditions().values()
    ):
        return (JournalEntry("boundary_disturbance", payload),)
    camp = candidate.state.scenario_entity_bindings.get("camp")
    entity = candidate.entities.get(camp) if isinstance(camp, str) else None
    if (
        entity is None
        or entity.id != camp
        or entity.definition_key != "settlement"
        or entity.destroyed_tick is not None
    ):
        raise ArchiveFormatError("Boundary camp binding mismatch.")
    before_events = set(candidate.state.events)
    if policy.kind == "resource_loss":
        resources = entity.attributes.get("resources")
        if not isinstance(resources, Mapping) or set(resources) != {
            "food",
            "water",
            "timber",
        }:
            raise ArchiveFormatError("Boundary resource vocabulary mismatch.")
        updated = {key: integer(value) for key, value in resources.items()}
        before = updated["timber"]
        payload.update(
            target_id=camp,
            resource="timber",
            quantity_before=before,
            quantity_after=0,
            outcome="applied" if before else "empty_stock",
        )
        if before:
            updated["timber"] = 0
            candidate.entities.set_attribute(
                entity_id=camp, key="resources", value=updated
            )
            candidate.events.record(
                kind="runtime_resource_loss",
                subject_id=camp,
                attributes={
                    "resource": "timber",
                    "quantity_before": before,
                    "quantity_after": 0,
                    "quantity_removed": before,
                },
            )
    else:
        selected = next(
            (
                work
                for work in candidate.work.all()
                if work.settlement_id == camp
                and candidate.state.work_states[work.id].status
                in (WorkStatus.READY, WorkStatus.ASSIGNED, WorkStatus.ACTIVE)
            ),
            None,
        )
        payload["outcome"] = "no_eligible_work" if selected is None else "applied"
        if selected is not None:
            candidate.work.block(selected.id, "External work interruption")
            payload["target_id"] = selected.id
    payload["event_references"] = tuple(
        event_id for event_id in candidate.state.events if event_id not in before_events
    )
    return (JournalEntry("boundary_disturbance", payload),)
