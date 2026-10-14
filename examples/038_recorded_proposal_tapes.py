"""Replay an untrusted greeting through filtered context and a manager gateway."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.api.inspection import WorldInspector
from living_world.cognition.action_resolution import ActionResolution, NPCActionHandler
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.managers.entity_manager import EntityManager
from living_world.replay.model import ProposalTape, ProposalTapeEntry, ReplayState
from living_world.replay.runtime import ReplayPreparation
from living_world.replay.system import ReplayActionOffers
from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.running import RunConfiguration, ScenarioRunner
from living_world.simulation.simulation_engine import SimulationEngine


class GreetingHandler:
    """Engine-authored sample policy; the tape cannot supply arbitrary attributes."""

    def __init__(self, entities: EntityManager, actor_id: str) -> None:
        self._entities = entities
        self._actor_id = actor_id

    def supports(self, action_key: str) -> bool:
        return action_key == "greet"

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        entity = self._entities.get(actor_id)
        return ActionResolution(
            actor_id == self._actor_id
            and entity is not None
            and entity.destroyed_tick is None
            and not request.arguments,
            "The greeting follows the settlement's policy.",
        )

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        self._entities.set_attribute(
            entity_id=actor_id, key="greeting", value="Hello, neighbor."
        )
        return ActionResolution(True, "The greeting was delivered.")


class GreetingOffers:
    def __init__(self, factory: Callable[[str], NPCActionHandler]) -> None:
        self._factory = factory

    def offers(self, *, actor_id: str, inspector: WorldInspector) -> ReplayActionOffers:
        assert inspector.entity(actor_id) is not None
        return ReplayActionOffers(
            actor_id,
            (ActionOption("greet", "Greet a neighbor."),),
            (self._factory(actor_id),),
        )


def preparation(engine: SimulationEngine, tape: ProposalTape) -> ReplayPreparation:
    return ReplayPreparation(
        tape, GreetingOffers(lambda actor: GreetingHandler(engine.entities, actor))
    )


with TemporaryDirectory() as temporary:
    directory = Path(temporary)
    (directory / "world.yaml").write_text(
        "definitions:\n  - key: person\n", encoding="utf-8"
    )
    scenario_path = directory / "scenario.yaml"
    scenario_path.write_text(
        "schema_version: 1\nkey: greeting_demo\nseed: 7\ndefinitions: world.yaml\n"
        "run:\n  max_ticks: 2\nentities:\n  - label: speaker\n    definition: person\n    name: Rhea\n",
        encoding="utf-8",
    )
    repository = SQLiteRepository(str(directory / "world.sqlite3"))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path)
    actor_id = engine.scenarios.entity_bindings()["speaker"]
    context = NPCContextAssembler(engine.state).assemble(holder_id=actor_id)
    assert context.identity == "Rhea" and actor_id not in repr(context)
    tape = ProposalTape(
        1,
        scenario.key,
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1,
                "speaker",
                NPCDecision(None, ActionRequest("greet", None, "A friendly start.")),
                "A friendly start.",
            ),
            ProposalTapeEntry(
                2,
                "speaker",
                NPCDecision("Welcome, neighbor.", None),
                "Share a welcome.",
            ),
        ),
    )
    checkpoint = ScenarioRunner(engine, preparation(engine, tape)).run(
        scenario_path, RunConfiguration(max_ticks=1, finalize_proposals=False)
    )
    assert checkpoint.proposals_finalized is False
    restored = SimulationEngine(repository)
    final = ScenarioRunner(restored, preparation(restored, tape)).run(
        scenario_path, RunConfiguration(max_ticks=1)
    )
    assert final.proposals_finalized is True
    assert restored.replay.current() == ReplayState(2, 1)
    actor = restored.entities.get(actor_id)
    assert actor is not None and actor.attributes["greeting"] == "Hello, neighbor."
    outcomes = tuple(
        event.attributes["outcome"]
        for event in restored.state.events.values()
        if event.kind == "replay_proposal_resolved"
    )
    assert outcomes == ("accepted", "no_action")
    assert restored.state.memories == {}
    print("Recorded greeting accepted through the ordinary manager gateway.")
    print("Checkpoint resumed at the next entry; speech remains a proposal.")
