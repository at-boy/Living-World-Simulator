"""Literal contract tests for deterministic, proposal-only replay."""

import hashlib
import json
import sqlite3
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import cast

import pytest
import yaml
from fastapi.routing import APIRoute

from living_world.api.inspection import EngineWorldInspector, WorldInspector
from living_world.api.server import create_app
from living_world.cli import main
from living_world.cognition.action_resolution import ActionResolution, NPCActionHandler
from living_world.cognition.information_boundary import NPCInformationBoundary
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    ActionRequest,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.event import Event
from living_world.replay.client import RecordedProposalClient
from living_world.replay.loader import YAMLProposalTapeLoader
from living_world.replay.manager import ReplayManager
from living_world.replay.model import (
    ProposalTape,
    ProposalTapeEntry,
    ProposalTapeError,
    ReplayBinding,
    ReplayOutcome,
    ReplayState,
)
from living_world.replay.runtime import ReplayPreparation
from living_world.replay.system import ReplayActionOffers
from living_world.repositories.sqlite_repository import (
    RepositoryLoadError,
    RepositorySaveError,
    SQLiteRepository,
)
from living_world.running import (
    RunConfiguration,
    RunSimulationError,
    ScenarioRunner,
    StopReason,
)
from living_world.simulation.simulation_engine import FailedTickError, SimulationEngine
from living_world.state.world_state import WorldState
from living_world.systems.simulation_system import SimulationSystem


def test_canonical_tape_hash_and_safe_errors(tmp_path: Path) -> None:
    tape = ProposalTape(
        1,
        "camp",
        "a" * 64,
        (
            ProposalTapeEntry(
                1, "founder", NPCDecision("Héllo", None), "We should talk."
            ),
        ),
    )
    normalized = {
        "schema_version": 1,
        "scenario_key": "camp",
        "scenario_fingerprint": "a" * 64,
        "entries": [
            {
                "sequence": 1,
                "actor_label": "founder",
                "action": None,
                "speech": "Héllo",
                "rationale": "We should talk.",
            }
        ],
    }
    expected = hashlib.sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert tape.fingerprint == expected
    path = tmp_path / "private.yaml"
    path.write_text("secret: password\nsecret: other\n", encoding="utf-8")
    with pytest.raises(ProposalTapeError) as caught:
        YAMLProposalTapeLoader().load(path)
    assert str(caught.value) == "invalid_tape: Invalid proposal tape."


@pytest.mark.parametrize(
    "fragment",
    [
        "sequence: true",
        "sequence: 2",
        "actor_label: entity_000001",
        "speech: null",
        "extra: secret",
    ],
)
def test_loader_rejects_invalid_entry(tmp_path: Path, fragment: str) -> None:
    body = "sequence: 1\n    actor_label: founder\n    action: null\n    speech: Hello\n    rationale: Speak clearly"
    if fragment.startswith("extra"):
        body += "\n    " + fragment
    else:
        field = fragment.split(":")[0]
        body = "\n    ".join(
            fragment if line.strip().startswith(field + ":") else line.strip()
            for line in body.splitlines()
        )
    path = tmp_path / "tape.yaml"
    path.write_text(
        "schema_version: 1\nscenario_key: camp\nscenario_fingerprint: "
        + "a" * 64
        + "\nentries:\n  - "
        + body
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ProposalTapeError, match="invalid_tape"):
        YAMLProposalTapeLoader().load(path)


def scenario_path(tmp_path: Path) -> Path:
    (tmp_path / "world.yaml").write_text(
        "definitions:\n  - key: person\n", encoding="utf-8"
    )
    path = tmp_path / "scenario.yaml"
    path.write_text(
        "schema_version: 1\nkey: camp\nseed: 7\ndefinitions: world.yaml\nrun:\n  max_ticks: 3\nentities:\n  - label: founder\n    definition: person\n    name: Rhea\n",
        encoding="utf-8",
    )
    return path


def test_manager_cursor_tick_and_lifecycle(tmp_path: Path) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    assert engine.state.scenario_entity_bindings == {"founder": "entity_000001"}
    manager = ReplayManager(engine.state, engine.events)
    binding = ReplayBinding(
        "camp", scenario.configuration_fingerprint, "a" * 64, ("founder", "founder"), 0
    )
    manager.configure(binding)
    with pytest.raises(ProposalTapeError):
        engine.entities.mark_destroyed("entity_000001", 0)
    assert manager.consume(
        sequence=1, actor_label="founder", outcome=ReplayOutcome.NO_ACTION
    ) == ReplayState(1, 0)
    with pytest.raises(ProposalTapeError):
        manager.consume(
            sequence=2, actor_label="founder", outcome=ReplayOutcome.ACCEPTED
        )
    engine.state.tick = 1
    manager.validate_loaded_state()
    assert manager.configure(binding) == binding
    assert manager.current() == ReplayState(1, 0)
    manager.consume(sequence=2, actor_label="founder", outcome=ReplayOutcome.REJECTED)
    engine.state.tick = 2
    engine.entities.mark_destroyed("entity_000001", 2)
    with pytest.raises(ValueError):
        engine.entities.remove("entity_000001")
    assert [
        dict(event.attributes) for event in engine.events.events_for("entity_000001")
    ] == [
        {"sequence": 1, "actor_label": "founder", "outcome": "no_action"},
        {"sequence": 2, "actor_label": "founder", "outcome": "rejected"},
    ]
    with pytest.raises(ProposalTapeError, match="tape_exhausted"):
        manager.consume(
            sequence=3, actor_label="founder", outcome=ReplayOutcome.ACCEPTED
        )


class BrokenSystem(SimulationSystem):
    def step(self, state: WorldState) -> None:
        state.entities.clear()
        raise RuntimeError("tick broke")


def test_failed_tick_refuses_save_and_advance_with_cause(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    engine = SimulationEngine(repository)
    engine.load_scenario(scenario_path(tmp_path))
    engine.save_world()
    engine.register_system(BrokenSystem())
    with pytest.raises(RuntimeError, match="tick broke") as original:
        engine.step()
    for operation in (engine.step, engine.save_world, lambda: engine.run(0)):
        with pytest.raises(FailedTickError) as caught:
            operation()
        assert caught.value.__cause__ is original.value
        assert (
            str(caught.value)
            == "Cannot advance or save a failed tick; reload the last checkpoint."
        )
    restored = SimulationEngine(repository)
    assert restored.state.tick == 0
    assert set(restored.state.entities) == {"entity_000001"}


def speech_tape(engine: SimulationEngine, count: int = 3) -> ProposalTape:
    metadata = engine.state.run_metadata
    assert metadata is not None
    return ProposalTape(
        1,
        "camp",
        metadata.configuration_fingerprint,
        tuple(
            ProposalTapeEntry(
                n,
                "founder",
                NPCDecision("Let us talk.", None),
                "A useful conversation.",
            )
            for n in range(1, count + 1)
        ),
    )


def test_replay_checkpoint_resume_and_idle(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    path = scenario_path(tmp_path)
    engine = SimulationEngine(repository)
    engine.load_scenario(path)
    tape = speech_tape(engine)
    first = ScenarioRunner(engine, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=1, finalize_proposals=False)
    )
    assert first.proposals_finalized is False
    assert engine.replay.current() == ReplayState(1, 0)
    resumed = SimulationEngine(repository)
    assert resumed.state.scenario_entity_bindings == {"founder": "entity_000001"}
    with pytest.raises(ProposalTapeError, match="missing_replay_preparation"):
        ScenarioRunner(resumed).run(path, RunConfiguration(max_ticks=0))
    second = ScenarioRunner(resumed, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=4)
    )
    assert second.proposals_finalized is True
    assert second.end_tick == 5
    assert resumed.replay.current() == ReplayState(3, 2)
    assert (
        len(
            [
                event
                for event in resumed.state.events.values()
                if event.kind == "replay_proposal_resolved"
            ]
        )
        == 3
    )


def test_unused_entries_prevent_stopping_checkpoint(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    path = scenario_path(tmp_path)
    engine = SimulationEngine(repository)
    engine.load_scenario(path)
    tape = speech_tape(engine)
    with pytest.raises(ProposalTapeError, match="unused_entries"):
        ScenarioRunner(engine, ReplayPreparation(tape)).run(
            path, RunConfiguration(max_ticks=2)
        )
    loaded = repository.load_world()
    assert loaded.tick == 1
    assert loaded.replay_state == ReplayState(1, 0)


class GatewayHandler:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.applied = False

    def supports(self, action_key: str) -> bool:
        return action_key == "greet"

    def validate(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        return ActionResolution(
            self.accepted, "Allowed" if self.accepted else "Unavailable"
        )

    def apply(self, *, actor_id: str, request: ActionRequest) -> ActionResolution:
        self.applied = True
        return ActionResolution(True, "Completed")


class GatewayOffers:
    def __init__(self, handler: GatewayHandler) -> None:
        self.handler = handler

    def offers(self, *, actor_id: str, inspector: WorldInspector) -> ReplayActionOffers:
        assert inspector.entity(actor_id) is not None
        return ReplayActionOffers(
            actor_id, (ActionOption("greet", "Greet someone"),), (self.handler,)
        )


@pytest.mark.parametrize(
    "accepted, expected", [(True, "accepted"), (False, "rejected")]
)
def test_runtime_ordinary_gateway(
    tmp_path: Path, accepted: bool, expected: str
) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = ProposalTape(
        1,
        "camp",
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1,
                "founder",
                NPCDecision(None, ActionRequest("greet", None, "Be friendly")),
                "Be friendly",
            ),
        ),
    )
    handler = GatewayHandler(accepted)
    ReplayPreparation(tape, GatewayOffers(handler)).prepare(engine, scenario)
    engine.step()
    assert handler.applied is accepted
    event = next(
        event
        for event in engine.state.events.values()
        if event.kind == "replay_proposal_resolved"
    )
    assert event.attributes["outcome"] == expected


def test_detached_inspection_and_npc_filter(tmp_path: Path) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = speech_tape(engine, 1)
    ReplayPreparation(tape).prepare(engine, scenario)
    inspector = EngineWorldInspector(engine)
    snapshot = inspector.replay()
    assert snapshot["state"] == {"next_index": 0, "last_attempt_tick": None}
    labels = cast(MutableMapping[str, object], snapshot["entity_bindings"])
    labels["founder"] = "changed"
    assert engine.state.scenario_entity_bindings == {"founder": "entity_000001"}
    assert inspector.world_summary()["replay_configured"] is True
    boundary = NPCInformationBoundary(engine.state)
    for text in (
        tape.fingerprint,
        scenario.configuration_fingerprint,
        "next_index",
        "configured_tick",
        "0",
    ):
        with pytest.raises(ValueError):
            boundary.validate_conversation_prose(text)
    assert boundary.validate_conversation_prose("founder") == "founder"
    route = next(
        route
        for route in create_app(engine).routes
        if isinstance(route, APIRoute) and route.path == "/world/replay"
    )
    assert route.methods == {"GET"}


def test_cli_speech_only_checkpoint_and_resume(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = scenario_path(tmp_path)
    engine = SimulationEngine()
    scenario = engine.load_scenario(path)
    tape_path = tmp_path / "tape.yaml"
    tape_path.write_text(
        "schema_version: 1\nscenario_key: camp\nscenario_fingerprint: "
        + scenario.configuration_fingerprint
        + "\nentries:\n  - sequence: 1\n    actor_label: founder\n    action: null\n    speech: Hello\n    rationale: Talk first\n",
        encoding="utf-8",
    )
    args = [
        "run",
        str(path),
        "--database",
        str(tmp_path / "run.sqlite3"),
        "--proposal-tape",
        str(tape_path),
    ]
    assert main([*args, "--max-ticks", "0", "--checkpoint-only"]) == 0
    assert "proposals_finalized=False" in capsys.readouterr().out
    assert main([*args, "--max-ticks", "1"]) == 0
    assert "proposals_finalized=True" in capsys.readouterr().out


def test_direct_engine_requires_preparation_on_resume(tmp_path: Path) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = speech_tape(engine, 1)
    ReplayPreparation(tape).prepare(engine, scenario)
    engine.step()
    engine.save_world()
    restored = SimulationEngine(repository)
    for operation in (restored.step, restored.save_world, lambda: restored.run(0)):
        with pytest.raises(ProposalTapeError, match="missing_replay_preparation"):
            operation()
    restored.load_scenario(tmp_path / "scenario.yaml")
    ReplayPreparation(tape).prepare(restored, scenario)
    restored.step()
    assert restored.state.tick == 2


def test_atomic_preparation_install_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = speech_tape(engine)

    def fail_install(system: SimulationSystem | None) -> None:
        raise RuntimeError("installation failed")

    monkeypatch.setattr(engine, "configure_proposal_system", fail_install)
    with pytest.raises(RuntimeError, match="installation failed"):
        ReplayPreparation(tape).prepare(engine, scenario)
    assert engine.state.replay_binding is None
    assert engine.state.replay_state is None
    assert engine.state.events == {}


class TickStop:
    def __init__(self, engine: SimulationEngine, tick: int) -> None:
        self.engine = engine
        self.tick = tick

    def stop_requested(self) -> bool:
        return self.engine.state.tick >= self.tick


def test_operator_terminal_allows_leftovers(tmp_path: Path) -> None:
    path = scenario_path(tmp_path)
    text = path.read_text(encoding="utf-8").replace(
        "  max_ticks: 3", "  max_ticks: 3\n  terminal_conditions: [operator_stop]"
    )
    path.write_text(text, encoding="utf-8")
    engine = SimulationEngine(SQLiteRepository(str(tmp_path / "world.sqlite3")))
    engine.load_scenario(path)
    result = ScenarioRunner(engine, ReplayPreparation(speech_tape(engine))).run(
        path, RunConfiguration(continuous=True), stop_control=TickStop(engine, 1)
    )
    assert result.proposals_finalized is False
    assert result.terminal_condition == "operator_stop"
    assert engine.replay.current() == ReplayState(1, 0)


def valid_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "scenario_key": "camp",
        "scenario_fingerprint": "a" * 64,
        "entries": [
            {
                "sequence": 1,
                "actor_label": "founder",
                "action": None,
                "speech": "Hello",
                "rationale": "Talk first",
            }
        ],
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("scenario_fingerprint", "A" * 64),
        ("scenario_fingerprint", "private"),
        ("scenario_key", ""),
        ("entries", []),
        ("entries", {}),
    ],
)
def test_invalid_header_is_safe(tmp_path: Path, field: str, value: object) -> None:
    document = valid_document()
    document[field] = value
    path = tmp_path / "private.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ProposalTapeError) as caught:
        YAMLProposalTapeLoader().load(path)
    assert str(caught.value) == "invalid_tape: Invalid proposal tape."
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "text",
    [
        "!!python/object/apply:os.system [echo secret]",
        "? [secret, private]\n: secret",
        "schema_version: 1\nschema_version: 1",
        "[]",
        "null",
    ],
)
def test_loader_rejects_unsafe_yaml_without_payload(tmp_path: Path, text: str) -> None:
    path = tmp_path / "secret.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ProposalTapeError) as caught:
        YAMLProposalTapeLoader().load(path)
    assert str(caught.value) == "invalid_tape: Invalid proposal tape."


@pytest.mark.parametrize(
    "action",
    [
        {"key": "greet", "target_label": None},
        {"key": "greet", "target_label": None, "arguments": {}, "extra": "private"},
        {
            "key": "greet",
            "target_label": None,
            "arguments": {"subject": "entity_000001"},
        },
        {"key": "greet", "target_label": None, "arguments": {"subject": 2}},
        {"key": "greet", "target_label": 2, "arguments": {}},
        {"key": "", "target_label": None, "arguments": {}},
        "private",
    ],
)
def test_loader_rejects_malformed_actions(tmp_path: Path, action: object) -> None:
    document = valid_document()
    entries = cast(list[dict[str, object]], document["entries"])
    entries[0]["action"] = action
    path = tmp_path / "tape.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ProposalTapeError, match="invalid_tape"):
        YAMLProposalTapeLoader().load(path)


def test_loader_action_and_explicit_null_canonicalization(tmp_path: Path) -> None:
    document = valid_document()
    entry = cast(list[dict[str, object]], document["entries"])[0]
    entry["action"] = {
        "key": "greet",
        "target_label": "Neighbor",
        "arguments": {"tone": "Kind"},
    }
    del entry["speech"]
    path = tmp_path / "tape.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    first = YAMLProposalTapeLoader().load(path)
    assert first.entries[0].decision == NPCDecision(
        None, ActionRequest("greet", "Neighbor", "Talk first", {"tone": "Kind"})
    )
    entry["speech"] = None
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert YAMLProposalTapeLoader().load(path).fingerprint == first.fingerprint


def test_client_identity_uses_name_and_filtered_context(tmp_path: Path) -> None:
    engine = SimulationEngine()
    engine.load_scenario(scenario_path(tmp_path))
    other = engine.entities.create(definition_key="person", name="Rhea")
    from living_world.core.memory import CognitiveSalience

    engine.memories.record(
        holder_id=other.id,
        subject_id=other.id,
        summary="Private other memory",
        salience=CognitiveSalience(importance=1, is_core=True),
    )
    context = NPCContextAssembler(engine.state).assemble(holder_id="entity_000001")
    assert context.identity == "Rhea"
    assert "Private other memory" not in repr(context)
    entry = speech_tape(engine, 1).entries[0]
    client = RecordedProposalClient(entry, expected_identity="Rhea")
    assert client.decide(context, ()) == NPCDecision("Let us talk.", None)
    assert client.provider_name == "recorded_proposals"
    with pytest.raises(ProposalTapeError, match="actor_mismatch"):
        RecordedProposalClient(entry, expected_identity="founder").decide(context, ())
    assert set(vars(client)) == {"_entry", "_expected_identity"}


class FixedOffers:
    def __init__(
        self,
        options: tuple[ActionOption, ...],
        handlers: tuple[NPCActionHandler, ...],
        actor_id: str = "entity_000001",
    ) -> None:
        self.options, self.handlers, self.actor_id = options, handlers, actor_id

    def offers(self, *, actor_id: str, inspector: WorldInspector) -> ReplayActionOffers:
        return ReplayActionOffers(self.actor_id, self.options, self.handlers)


@pytest.mark.parametrize(
    "case", ["actor", "missing", "duplicate", "keys", "targets", "vocabulary"]
)
def test_bad_offers_never_consume(tmp_path: Path, case: str) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = ProposalTape(
        1,
        "camp",
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1,
                "founder",
                NPCDecision(None, ActionRequest("greet", None, "Be friendly")),
                "Be friendly",
            ),
        ),
    )
    handler = GatewayHandler(True)
    options = (ActionOption("greet", "Greet"),)
    handlers = (handler,)
    actor_id = "entity_000001"
    if case == "actor":
        actor_id = "entity_000002"
    elif case == "missing":
        handlers = ()
    elif case == "duplicate":
        handlers = (handler, handler)
    elif case == "keys":
        options = (ActionOption("z", "Last"), ActionOption("greet", "Greet"))
    elif case == "targets":
        options = (ActionOption("greet", "Greet", ("Zed", "Amy")),)
    else:
        options, handlers = (), ()
    ReplayPreparation(tape, FixedOffers(options, handlers, actor_id)).prepare(
        engine, scenario
    )
    with pytest.raises(ProposalTapeError):
        engine.step()
    assert engine.replay.current() == ReplayState(0)
    assert handler.applied is False
    assert engine.state.events == {}


def test_hidden_decision_prose_does_not_consume(tmp_path: Path) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = ProposalTape(
        1,
        "camp",
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1,
                "founder",
                NPCDecision(scenario.configuration_fingerprint, None),
                "Talk first",
            ),
        ),
    )
    ReplayPreparation(tape).prepare(engine, scenario)
    with pytest.raises(ValueError, match="fingerprints"):
        engine.step()
    assert engine.replay.current() == ReplayState(0)
    assert engine.state.events == {}


def test_consume_event_failure_rolls_back_only_new_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    existing = engine.events.record(kind="existing")
    original = engine.events.record

    def fail_record(
        *,
        kind: str,
        subject_id: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> Event:
        original(kind=kind, subject_id=subject_id, attributes=attributes)
        raise RuntimeError("event failure")

    monkeypatch.setattr(engine.events, "record", fail_record)
    with pytest.raises(RuntimeError):
        engine.replay.consume(
            sequence=1, actor_label="founder", outcome=ReplayOutcome.NO_ACTION
        )
    assert engine.replay.current() == ReplayState(0)
    assert engine.state.events == {existing.id: existing}
    monkeypatch.setattr(engine.events, "record", original)
    engine.replay.consume(
        sequence=1, actor_label="founder", outcome=ReplayOutcome.NO_ACTION
    )
    assert engine.replay.current() == ReplayState(1, 0)


def payload_from(database: Path) -> dict[str, object]:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT payload FROM world_snapshots WHERE id=1"
        ).fetchone()
    assert row is not None
    return cast(dict[str, object], json.loads(row[0]))


def replace_payload(
    database: Path, payload: Mapping[str, object], schema: int = 12
) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE world_snapshots SET schema_version=?, payload=? WHERE id=1",
            (schema, json.dumps(payload)),
        )


@pytest.mark.parametrize("schema", range(1, 12))
def test_legacy_defaults_do_not_infer_labels(tmp_path: Path, schema: int) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    engine.save_world()
    payload = payload_from(database)
    for key in ("scenario_entity_bindings", "replay_binding", "replay_state"):
        del payload[key]
    replace_payload(database, payload, schema)
    loaded = repository.load_world()
    assert loaded.scenario_entity_bindings == {}
    assert loaded.replay_binding is loaded.replay_state is None
    repository.save_world(loaded)
    assert payload_from(database)["scenario_entity_bindings"] == {}
    restored = SimulationEngine(repository)
    restored.load_scenario(tmp_path / "scenario.yaml")
    with pytest.raises(ProposalTapeError, match="actor_mismatch"):
        ReplayPreparation(speech_tape(engine)).prepare(restored, scenario)


@pytest.mark.parametrize(
    "case",
    [
        "pair",
        "future",
        "cursor",
        "last",
        "fingerprint",
        "actor",
        "destroyed",
        "extra",
        "bool",
    ],
)
def test_schema12_corruption_fails_closed(tmp_path: Path, case: str) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    engine.save_world()
    payload = payload_from(database)
    binding = cast(dict[str, object], payload["replay_binding"])
    cursor = cast(dict[str, object], payload["replay_state"])
    if case == "pair":
        payload["replay_state"] = None
    elif case == "future":
        binding["configured_tick"] = 1
    elif case == "cursor":
        cursor["next_index"] = 4
    elif case == "last":
        cursor["last_attempt_tick"] = 0
    elif case == "fingerprint":
        binding["tape_fingerprint"] = "private"
    elif case == "actor":
        binding["actor_sequence"] = ["unknown"]
    elif case == "destroyed":
        cast(list[dict[str, object]], payload["entities"])[0]["destroyed_tick"] = 0
    elif case == "extra":
        cursor["private"] = "secret"
    else:
        cursor["next_index"] = False
    replace_payload(database, payload)
    with pytest.raises(RepositoryLoadError, match="malformed"):
        repository.load_world()


def test_failed_save_preserves_snapshot(tmp_path: Path) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    engine.save_world()
    engine.state.replay_state = ReplayState(2, 1)
    with pytest.raises(RepositorySaveError):
        repository.save_world(engine.state)
    loaded = repository.load_world()
    assert loaded.replay_state == ReplayState(0)
    assert loaded.tick == 0


@pytest.mark.parametrize("checkpoint", [0, 1, 2, 3])
def test_fresh_and_resumed_runs_converge(tmp_path: Path, checkpoint: int) -> None:
    path = scenario_path(tmp_path)
    fresh_db = tmp_path / "fresh.sqlite3"
    resumed_db = tmp_path / "resumed.sqlite3"
    fresh = SimulationEngine(SQLiteRepository(str(fresh_db)))
    fresh.load_scenario(path)
    tape = speech_tape(fresh)
    ScenarioRunner(fresh, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=4)
    )
    split = SimulationEngine(SQLiteRepository(str(resumed_db)))
    ScenarioRunner(split, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=checkpoint, finalize_proposals=False)
    )
    restored = SimulationEngine(SQLiteRepository(str(resumed_db)))
    ScenarioRunner(restored, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=4 - checkpoint)
    )
    assert payload_from(resumed_db) == payload_from(fresh_db)
    assert fresh.replay.current() == restored.replay.current() == ReplayState(3, 2)


def test_late_tick_failure_recovers_cursor_and_domain_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = speech_tape(engine)
    ReplayPreparation(tape).prepare(engine, scenario)
    engine.save_world()

    class LateFailure:
        def step(self, state: WorldState) -> None:
            state.entities["entity_000001"].name = "Changed"
            raise RuntimeError("late failure")

    assert engine._settlement_stage_evaluation_system is not None
    monkeypatch.setattr(
        engine._settlement_stage_evaluation_system, "step", LateFailure().step
    )
    with pytest.raises(RuntimeError, match="late failure"):
        engine.step()
    assert engine.replay.current() == ReplayState(1, 0)
    with pytest.raises(FailedTickError):
        engine.save_world()
    restored = SimulationEngine(repository)
    restored.load_scenario(tmp_path / "scenario.yaml")
    ReplayPreparation(tape).prepare(restored, scenario)
    assert restored.replay.current() == ReplayState(0)
    actor = restored.entities.get("entity_000001")
    assert actor is not None and actor.name == "Rhea"
    restored.step()
    assert restored.replay.current() == ReplayState(1, 0)


class TraceSystem:
    def __init__(self, name: str, trace: list[tuple[str, int]]) -> None:
        self.name, self.trace = name, trace

    def step(self, state: WorldState) -> None:
        self.trace.append((self.name, state.tick))


def test_proposal_slot_replaces_and_exact_phase_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine()
    trace: list[tuple[str, int]] = []
    engine.register_system(TraceSystem("ordinary", trace))
    phases = (
        ("work", engine._work_execution_system),
        ("consequences", engine._consequence_system),
        ("needs", engine._need_assessment_system),
        ("goals", engine._goal_evaluation_system),
        ("stages", engine._settlement_stage_evaluation_system),
    )
    for name, system in phases:
        assert system is not None
        monkeypatch.setattr(system, "step", TraceSystem(name, trace).step)
    engine.configure_proposal_system(TraceSystem("discarded", trace))
    engine.configure_proposal_system(TraceSystem("proposal", trace))
    engine.step()
    assert trace == [
        ("ordinary", 0),
        ("proposal", 0),
        ("work", 0),
        ("consequences", 0),
        ("needs", 0),
        ("goals", 0),
        ("stages", 0),
    ]
    assert engine.state.tick == 1
    engine.configure_proposal_system(None)
    trace.clear()
    engine.step()
    assert trace == [
        ("ordinary", 1),
        ("work", 1),
        ("consequences", 1),
        ("needs", 1),
        ("goals", 1),
        ("stages", 1),
    ]


def test_prepare_is_idempotent_and_changed_tape_atomic(tmp_path: Path) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = speech_tape(engine)
    preparation = ReplayPreparation(tape)
    preparation.prepare(engine, scenario)
    engine.step()
    binding = engine.state.replay_binding
    preparation.prepare(engine, scenario)
    assert engine.state.replay_binding is binding
    assert engine.replay.current() == ReplayState(1, 0)
    changed = ProposalTape(
        1,
        "camp",
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1, "founder", NPCDecision("Changed story", None), "Talk first"
            ),
        ),
    )
    with pytest.raises(ProposalTapeError, match="scenario_mismatch"):
        ReplayPreparation(changed).prepare(engine, scenario)
    assert engine.state.replay_binding is binding
    assert engine.replay.current() == ReplayState(1, 0)
    engine.entities.set_attribute(
        entity_id="entity_000001", key="safe_note", value="History"
    )
    engine.state.entities["entity_000001"].name = "Renamed"
    engine.load_scenario(tmp_path / "scenario.yaml")
    engine.step()
    assert engine.replay.current() == ReplayState(2, 1)


def test_preparation_rebuild_failure_restores_previous_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    trace: list[tuple[str, int]] = []
    previous = TraceSystem("previous", trace)
    engine.configure_proposal_system(previous)
    original = engine._rebuild_scheduler
    calls = 0

    def fail_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("install failed")
        original()

    monkeypatch.setattr(engine, "_rebuild_scheduler", fail_once)
    with pytest.raises(RuntimeError, match="install failed"):
        ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    assert engine.state.replay_binding is engine.state.replay_state is None
    engine.step()
    assert trace == [("previous", 0)]


def test_zero_tick_stop_and_terminal_final_save_order(tmp_path: Path) -> None:
    path = scenario_path(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "  max_ticks: 3", "  max_ticks: 3\n  terminal_conditions: [tick_limit]"
        ),
        encoding="utf-8",
    )
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    engine.load_scenario(path)
    tape = speech_tape(engine)
    with pytest.raises(ProposalTapeError, match="unused_entries"):
        ScenarioRunner(engine, ReplayPreparation(tape)).run(
            path, RunConfiguration(max_ticks=0)
        )
    assert repository.load_world().run_metadata is None
    result = ScenarioRunner(engine, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=0), stop_control=TickStop(engine, 0)
    )
    assert result.stop_reason is StopReason.OPERATOR_STOP
    assert result.proposals_finalized is False
    with pytest.raises(ProposalTapeError, match="unused_entries"):
        ScenarioRunner(engine, ReplayPreparation(tape)).run(
            path, RunConfiguration(max_ticks=1)
        )
    assert repository.load_world().tick == 0
    result = ScenarioRunner(engine, ReplayPreparation(tape)).run(
        path, RunConfiguration(max_ticks=2)
    )
    assert result.proposals_finalized is True
    assert result.terminal_condition == "tick_limit"
    assert repository.load_world().replay_state == ReplayState(3, 2)


def test_simulation_failure_skips_finish_and_saving(tmp_path: Path) -> None:
    from living_world.running import RunResult
    from living_world.scenarios.scenario import LoadedScenario

    engine = SimulationEngine(SQLiteRepository(str(tmp_path / "world.sqlite3")))
    path = scenario_path(tmp_path)

    class Preparation:
        finished = False

        def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
            engine.register_system(BrokenSystem())

        def finish(
            self,
            engine: SimulationEngine,
            result: RunResult,
            *,
            finalize_proposals: bool,
        ) -> None:
            self.finished = True

    preparation = Preparation()
    with pytest.raises(RunSimulationError):
        ScenarioRunner(engine, preparation).run(path, RunConfiguration(max_ticks=1))
    assert preparation.finished is False
    assert SQLiteRepository(str(tmp_path / "world.sqlite3")).load_world().tick == 0


def test_offer_build_is_read_only_and_no_speech_history_injection(
    tmp_path: Path,
) -> None:
    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    tape = speech_tape(engine, 1)
    ReplayPreparation(tape).prepare(engine, scenario)
    engine.step()
    assert (
        engine.state.memories
        == engine.state.observations
        == engine.state.experiences
        == {}
    )
    context = NPCContextAssembler(engine.state).assemble(holder_id="entity_000001")
    assert context.conversation_history == ()
    assert "Let us talk" not in repr(context)


def test_config_boolean_rejects_truthy_values() -> None:
    with pytest.raises(TypeError, match="boolean"):
        RunConfiguration(finalize_proposals=cast(bool, 1))


@pytest.mark.parametrize("sequences", [(1, 1), (2, 1), (1, 3)])
def test_input_sequence_cannot_be_sorted_or_skipped(
    tmp_path: Path, sequences: tuple[int, int]
) -> None:
    document = valid_document()
    entry = cast(list[dict[str, object]], document["entries"])[0]
    document["entries"] = [dict(entry, sequence=n) for n in sequences]
    path = tmp_path / "tape.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ProposalTapeError, match="invalid_tape"):
        YAMLProposalTapeLoader().load(path)


def test_unicode_codepoints_remain_distinct() -> None:
    composed = ProposalTape(
        1,
        "camp",
        "a" * 64,
        (ProposalTapeEntry(1, "founder", NPCDecision("é", None), "Talk first"),),
    )
    decomposed = ProposalTape(
        1,
        "camp",
        "a" * 64,
        (ProposalTapeEntry(1, "founder", NPCDecision("e\u0301", None), "Talk first"),),
    )
    assert composed.fingerprint != decomposed.fingerprint


def test_noop_preparation_cannot_resume_bound_world(tmp_path: Path) -> None:
    from living_world.running import RunResult
    from living_world.scenarios.scenario import LoadedScenario

    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    engine = SimulationEngine(repository)
    path = scenario_path(tmp_path)
    scenario = engine.load_scenario(path)
    ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    engine.save_world()
    restored = SimulationEngine(repository)

    class NoopPreparation:
        finished = False

        def prepare(self, engine: SimulationEngine, scenario: LoadedScenario) -> None:
            pass

        def finish(
            self,
            engine: SimulationEngine,
            result: RunResult,
            *,
            finalize_proposals: bool,
        ) -> None:
            self.finished = True

    preparation = NoopPreparation()
    with pytest.raises(ProposalTapeError, match="missing_replay_preparation"):
        ScenarioRunner(restored, preparation).run(path, RunConfiguration(max_ticks=0))
    assert preparation.finished is False
    assert restored.state.tick == 0


def test_actor_tape_order_is_global_not_alphabetical(tmp_path: Path) -> None:
    path = scenario_path(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + "  - label: ally\n    definition: person\n    name: Rhea\n",
        encoding="utf-8",
    )
    engine = SimulationEngine()
    scenario = engine.load_scenario(path)
    tape = ProposalTape(
        1,
        "camp",
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1,
                "founder",
                NPCDecision("We should speak first", None),
                "Begin the conversation",
            ),
            ProposalTapeEntry(
                2,
                "ally",
                NPCDecision("I will answer", None),
                "Continue the conversation",
            ),
        ),
    )
    ReplayPreparation(tape).prepare(engine, scenario)
    engine.step()
    engine.entities.mark_destroyed("entity_000001", 1)
    with pytest.raises(ProposalTapeError, match="actor_mismatch"):
        engine.entities.mark_destroyed("entity_000002", 1)
    engine.step()
    events = tuple(
        (event.tick, event.subject_id, event.attributes["actor_label"])
        for event in engine.state.events.values()
        if event.kind == "replay_proposal_resolved"
    )
    assert events == ((0, "entity_000001", "founder"), (1, "entity_000002", "ally"))
    assert engine.replay.current() == ReplayState(2, 1)


@pytest.mark.parametrize(
    "corruption",
    (
        "missing",
        "duplicate",
        "gap",
        "extra",
        "tick",
        "future_tick",
        "actor",
        "subject",
        "extra_attribute",
        "missing_attribute",
        "outcome",
        "bool_sequence",
    ),
)
def test_complete_cursor_history_corruption_fails_closed(
    tmp_path: Path, corruption: str
) -> None:
    database = tmp_path / "world.sqlite3"
    repository = SQLiteRepository(str(database))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    engine.run(2)
    engine.save_world()
    payload = payload_from(database)
    events = cast(list[dict[str, object]], payload["events"])
    resolutions = [
        event for event in events if event["kind"] == "replay_proposal_resolved"
    ]
    assert len(resolutions) == 2
    first = resolutions[0]
    attributes = cast(dict[str, object], first["attributes"])
    if corruption == "missing":
        events.remove(first)
    elif corruption == "duplicate":
        cast(dict[str, object], resolutions[1]["attributes"])["sequence"] = 1
    elif corruption == "gap":
        cast(dict[str, object], resolutions[1]["attributes"])["sequence"] = 3
    elif corruption == "extra":
        events.append(dict(first, id="event_000099"))
    elif corruption == "tick":
        first["tick"] = 1
    elif corruption == "future_tick":
        first["tick"] = 3
    elif corruption == "actor":
        attributes["actor_label"] = "other"
    elif corruption == "subject":
        first["subject_id"] = None
    elif corruption == "extra_attribute":
        attributes["private"] = "secret"
    elif corruption == "missing_attribute":
        del attributes["outcome"]
    elif corruption == "outcome":
        attributes["outcome"] = "private"
    else:
        attributes["sequence"] = True
    replace_payload(database, payload)
    with pytest.raises(RepositoryLoadError) as caught:
        repository.load_world()
    cause = caught.value.__cause__
    assert isinstance(cause, ProposalTapeError)
    assert cause.code == "replay_state_invalid"


def test_reserved_history_cannot_configure_or_invent_legacy_progress(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(str(tmp_path / "world.sqlite3"))
    engine = SimulationEngine(repository)
    scenario = engine.load_scenario(scenario_path(tmp_path))
    engine.events.record(
        kind="replay_proposal_resolved",
        subject_id="entity_000001",
        attributes={"sequence": 1, "actor_label": "founder", "outcome": "no_action"},
    )
    repository.save_world(engine.state)
    legacy = repository.load_world()
    assert legacy.replay_binding is legacy.replay_state is None
    assert legacy.tick == 0
    with pytest.raises(ProposalTapeError, match="replay_state_invalid"):
        ReplayPreparation(speech_tape(engine)).prepare(engine, scenario)
    assert engine.state.replay_binding is engine.replay.current() is None


@pytest.mark.parametrize(
    "field",
    (
        "scenario_key",
        "actor_label",
        "speech",
        "rationale",
        "key",
        "target_label",
        "argument_key",
        "argument_value",
    ),
)
def test_loader_rejects_escaped_lone_surrogate_safely(
    tmp_path: Path, field: str
) -> None:
    document = valid_document()
    entry = cast(list[dict[str, object]], document["entries"])[0]
    if field == "scenario_key":
        document[field] = "\ud800"
    elif field in {"actor_label", "speech", "rationale"}:
        entry[field] = "\ud800"
    else:
        action: dict[str, object] = {
            "key": "greet",
            "target_label": "Neighbor",
            "arguments": {"tone": "Kind"},
        }
        entry["action"] = action
        if field in {"key", "target_label"}:
            action[field] = "\ud800"
        elif field == "argument_key":
            action["arguments"] = {"\ud800": "Kind"}
        else:
            action["arguments"] = {"tone": "\ud800"}
    path = tmp_path / "private.yaml"
    path.write_text(yaml.safe_dump(document, allow_unicode=False), encoding="utf-8")
    with pytest.raises(ProposalTapeError) as caught:
        YAMLProposalTapeLoader().load(path)
    assert str(caught.value) == "invalid_tape: Invalid proposal tape."
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_direct_tape_rejects_unencodable_speech_before_fingerprinting() -> None:
    with pytest.raises(ProposalTapeError) as caught:
        ProposalTape(
            1,
            "camp",
            "a" * 64,
            (
                ProposalTapeEntry(
                    1, "founder", NPCDecision("\udfff", None), "Speak first"
                ),
            ),
        )
    assert str(caught.value) == "invalid_tape: Invalid proposal tape."
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_supplementary_unicode_has_exact_utf8_identity(tmp_path: Path) -> None:
    document = valid_document()
    entry = cast(list[dict[str, object]], document["entries"])[0]
    entry["speech"] = "Welcome \U0001f30d"
    path = tmp_path / "tape.yaml"
    path.write_text(yaml.safe_dump(document, allow_unicode=False), encoding="utf-8")
    loaded = YAMLProposalTapeLoader().load(path)
    direct = ProposalTape(
        1,
        "camp",
        "a" * 64,
        (
            ProposalTapeEntry(
                1, "founder", NPCDecision("Welcome \U0001f30d", None), "Talk first"
            ),
        ),
    )
    expected = hashlib.sha256(
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert loaded.entries[0].decision.spoken_text == "Welcome \U0001f30d"
    assert loaded.fingerprint == direct.fingerprint == expected


def test_public_dispatch_action_key_replays_through_real_domain_gateway(
    tmp_path: Path,
) -> None:
    from living_world.external_world import ContactState
    from living_world.external_world.dispatch import DispatchDirection
    from living_world.external_world.dispatch_action import (
        DISPATCH_ACTION_KEY,
        DispatchOffer,
        ExternalDispatchActionHandler,
    )

    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    reference = engine.external_world_references.create(
        name="Homeland",
        role="homeland",
        allowed_exports=("food",),
        capacity=1,
        delay_ticks=2,
        cost_per_unit=0,
        reliability=1.0,
        contact_state=ContactState.CONTACTABLE,
    )
    handler = ExternalDispatchActionHandler(
        engine.external_dispatches,
        (
            DispatchOffer(
                "Request supplies", reference.id, DispatchDirection.INBOUND, "food", 1
            ),
        ),
    )
    tape = ProposalTape(
        1,
        scenario.key,
        scenario.configuration_fingerprint,
        (
            ProposalTapeEntry(
                1,
                "founder",
                NPCDecision(
                    None,
                    ActionRequest(
                        DISPATCH_ACTION_KEY, "Request supplies", "Bring supplies."
                    ),
                ),
                "Bring supplies.",
            ),
        ),
    )
    ReplayPreparation(tape, FixedOffers((handler.action_option,), (handler,))).prepare(
        engine, scenario
    )
    engine.step()
    assert len(engine.state.external_dispatches) == 1
    assert (
        next(iter(engine.state.external_dispatches.values())).source_entity_id
        == engine.state.scenario_entity_bindings["founder"]
    )
    assert engine.replay.current() == ReplayState(1, 0)


@pytest.mark.parametrize(
    "text", ["dispatch_external_trade", "dispatch_000123", "entity_000001"]
)
def test_public_dispatch_exception_does_not_change_conversation_boundary(
    text: str,
) -> None:
    with pytest.raises(ValueError):
        NPCInformationBoundary(WorldState()).validate_conversation_prose(text)


@pytest.mark.parametrize(
    "field",
    [
        "description",
        "option_target",
        "request_target",
        "rationale",
        "speech",
        "argument_key",
        "argument_value",
        "unknown_key",
        "internal_key",
        "unoffered_key",
    ],
)
def test_dispatch_structured_key_exception_never_admits_hidden_prose_or_other_keys(
    tmp_path: Path, field: str
) -> None:
    from dataclasses import replace

    from living_world.external_world import ContactState
    from living_world.external_world.dispatch import DispatchDirection
    from living_world.external_world.dispatch_action import (
        DISPATCH_ACTION_KEY,
        DispatchOffer,
        ExternalDispatchActionHandler,
    )

    engine = SimulationEngine()
    scenario = engine.load_scenario(scenario_path(tmp_path))
    reference = engine.external_world_references.create(
        name="Homeland",
        role="homeland",
        allowed_exports=("food",),
        capacity=1,
        delay_ticks=2,
        cost_per_unit=0,
        reliability=1.0,
        contact_state=ContactState.CONTACTABLE,
    )
    handler = ExternalDispatchActionHandler(
        engine.external_dispatches,
        (
            DispatchOffer(
                "Request supplies", reference.id, DispatchDirection.INBOUND, "food", 1
            ),
        ),
    )
    option = handler.action_option
    request = ActionRequest(DISPATCH_ACTION_KEY, "Request supplies", "Bring supplies.")
    speech = None
    rationale = "Bring supplies."
    if field == "description":
        option = replace(option, description=DISPATCH_ACTION_KEY)
    elif field == "option_target":
        option = replace(option, target_labels=(DISPATCH_ACTION_KEY,))
    elif field == "request_target":
        request = replace(request, target_label=DISPATCH_ACTION_KEY)
    elif field == "rationale":
        request = replace(request, rationale=DISPATCH_ACTION_KEY)
        rationale = DISPATCH_ACTION_KEY
    elif field == "speech":
        speech = DISPATCH_ACTION_KEY
    elif field == "argument_key":
        request = replace(request, arguments={DISPATCH_ACTION_KEY: "supplies"})
    elif field == "argument_value":
        request = replace(request, arguments={"purpose": DISPATCH_ACTION_KEY})
    elif field == "unknown_key":
        option = replace(option, key="dispatch_other")
        request = replace(request, action_key="dispatch_other")
    elif field == "internal_key":
        option = replace(option, key="dispatch_secret")
    else:
        request = replace(request, action_key="unoffered")
    tape = ProposalTape(
        1,
        scenario.key,
        scenario.configuration_fingerprint,
        (ProposalTapeEntry(1, "founder", NPCDecision(speech, request), rationale),),
    )
    ReplayPreparation(tape, FixedOffers((option,), (handler,))).prepare(
        engine, scenario
    )
    with pytest.raises(ValueError):
        engine.step()
    assert not engine.state.external_dispatches
    assert engine.replay.current() == ReplayState(0)
    assert not any(
        e.kind == "replay_proposal_resolved" for e in engine.state.events.values()
    )
