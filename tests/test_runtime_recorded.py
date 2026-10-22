"""Recorded controller preserves legacy worlds and survives process boundaries."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from living_world.archives import (
    AttemptConfig,
    AttemptLease,
    AttemptRef,
    RunCatalog,
    load_retained_inputs,
    retain_inputs,
)
from living_world.founders.assets import materialize_founders_assets
from living_world.repositories.sqlite_repository import RepositorySaveError
from living_world.repositories.world_snapshot import decode_world, encode_world
from living_world.runtime import (
    CommandEnvelope,
    RunController,
    RuntimeState,
    RuntimeStatus,
)
from living_world.runtime.recorded import (
    RecordedFoundersComposition,
    RecordedTickDriver,
    SnapshotRepository,
)
from living_world.state.world_state import WorldState

ROWS = [
    (
        "success",
        10,
        "08e45db464eeec34249d8e5349849f0a4cd03cea299e1f43836547960785bd09",
        152,
    ),
    (
        "stall",
        5,
        "1ac4b3d42faab2697464169bf184299e260309a033581bafd4d0eb17b953fee0",
        77,
    ),
    (
        "failure",
        13,
        "1bf0b8f37ff43a13b8c6ad0e63327844c0196d73b39e817eda2ed02d4b046dc6",
        56,
    ),
]


def reserve(tmp_path: Path, outcome: str) -> tuple[RunCatalog, AttemptRef]:
    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        from living_world.scenarios.scenario import YAMLScenarioLoader

        scenario = YAMLScenarioLoader().load(assets.scenario)
        ref = catalog.reserve(
            AttemptConfig("recorded", scenario.key, scenario.seed, "test", {})
        )
        retain_inputs(ref, assets.scenario, tape_path=getattr(assets, outcome))
    return catalog, ref


def drive(controller: RunController, max_polls: int = 100) -> RuntimeStatus:
    for _ in range(max_polls):
        status = controller.poll()
        if status.state in (
            RuntimeState.COMPLETED,
            RuntimeState.FAILED,
            RuntimeState.STOPPED,
        ):
            return status
    return controller.status()


@pytest.mark.parametrize("outcome,tick,digest,event_count", ROWS)
def test_exact_old_complete_recorded_world(
    tmp_path: Path, outcome: str, tick: int, digest: str, event_count: int
) -> None:
    catalog, ref = reserve(tmp_path, outcome)
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        controller = RunController(
            archive,
            RecordedFoundersComposition(load_retained_inputs(ref)),
            RecordedTickDriver(),
            max_ticks=5 if outcome == "stall" else None,
            start_paused=False,
        )
        status = drive(controller)
        assert status.state is RuntimeState.COMPLETED, status
        checkpoint = controller.published()
        state = decode_world(checkpoint.snapshot)
        assert state.tick == tick
        assert checkpoint.snapshot.schema_version == 12
        assert checkpoint.snapshot.digest == digest
        from hashlib import sha256

        payload_pins = {
            "success": "ec4a908de25253fa56872c5b5db9cd3c7a65d640c5be5c9b0b398b3a9f78fad0",
            "stall": "6fcb0e0003c59faa1eb661329ea55fbbb4ed21e297ff6cef180733e302e6ec3d",
            "failure": "fd80996bb1e122cd38e9f16fcb96ad1ecccf0dd5dcb530529a59aa3806024f2f",
        }
        assert (
            sha256(checkpoint.snapshot.payload.encode()).hexdigest()
            == payload_pins[outcome]
        )
        assert len(state.events) == event_count
        assert checkpoint.driver_cursor["next_index"] == tick
        assert checkpoint.driver_cursor["next_tick"] == tick


def test_snapshot_repository_is_detached_and_cannot_save() -> None:
    repository = SnapshotRepository(encode_world(WorldState()))
    first = repository.load_world()
    first.tick = 55
    assert repository.load_world().tick == 0
    with pytest.raises(RepositorySaveError):
        repository.save_world(first)


def test_recorded_continuous_intent_is_closed_metadata() -> None:
    from living_world.archives import ArchiveFormatError

    assert AttemptConfig("recorded", "s", 0, "test", {"limits": {"continuous": True}})
    for mode, limits in (
        ("ollama", {"continuous": False}),
        ("recorded", {"continuous": 1}),
        ("recorded", {"continuous": True, "max_ticks": 1}),
    ):
        with pytest.raises(ArchiveFormatError):
            AttemptConfig(mode, "s", 0, "test", {"limits": limits})


def test_legacy_recorded_cursor_is_preserved_and_validation_is_pure(
    tmp_path: Path,
) -> None:
    from living_world.runtime.legacy import legacy_cursor

    catalog, ref = reserve(tmp_path, "success")
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        composition = RecordedFoundersComposition(load_retained_inputs(ref))
        engine = composition.initialize()
        driver = RecordedTickDriver(cursor_kind="legacy_recorded")
        commit = driver.initialize(engine, archive)
        assert dict(commit.driver_cursor) == legacy_cursor(engine)
        saved = archive.commit(
            encode_world(engine.state),
            expected_revision=None,
            driver_cursor=commit.driver_cursor,
            feedback_cursor={},
            entries=(),
        )
        before = encode_world(engine.state)
        driver.validate_checkpoint(engine, saved, archive)
        assert encode_world(engine.state) == before
        assert (
            driver.prepare(engine, saved, archive).finish_tick().driver_cursor
            == saved.driver_cursor
        )


def test_paused_parent_fork_reproduces_world_cursor_and_history(tmp_path: Path) -> None:
    catalog, ref = reserve(tmp_path, "success")
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        controller = RunController(
            archive,
            RecordedFoundersComposition(load_retained_inputs(ref)),
            RecordedTickDriver(),
            max_ticks=None,
            start_paused=True,
        )
        controller.poll()
        for index in range(4):
            controller.submit(
                CommandEnvelope(str(index), "step", controller.status().state_version)
            )
            for _ in range(4):
                controller.poll()
        checkpoint = controller.published()
        assert decode_world(checkpoint.snapshot).tick == 4
    child = catalog.fork(ref.attempt_id, checkpoint.revision)
    with (
        AttemptLease(child),
        catalog.open_attempt(child.attempt_id, read_only=False) as archive,
    ):
        controller = RunController(
            archive,
            RecordedFoundersComposition(load_retained_inputs(child)),
            RecordedTickDriver(),
            max_ticks=None,
            start_paused=True,
        )
        assert controller.poll().tick == 4
        assert controller.published().snapshot == checkpoint.snapshot
        assert controller.published().driver_cursor == checkpoint.driver_cursor
        controller.submit(
            CommandEnvelope("resume", "resume", controller.status().state_version)
        )
        assert drive(controller).state is RuntimeState.COMPLETED
        assert controller.published().snapshot.digest == ROWS[0][2]


def test_subprocess_exit_reopen_and_fork_keeps_complete_boundary(
    tmp_path: Path,
) -> None:
    catalog, ref = reserve(tmp_path, "success")
    source = """
import sys
from pathlib import Path
from living_world.archives import RunCatalog, AttemptLease, load_retained_inputs, CommandEnvelope
from living_world.runtime import RunController
from living_world.runtime.recorded import RecordedFoundersComposition, RecordedTickDriver
catalog = RunCatalog(Path(sys.argv[1]))
with catalog.open_attempt(sys.argv[2]) as reader:
    ref = reader.ref
with AttemptLease(ref), catalog.open_attempt(ref.attempt_id, read_only=False) as archive:
    controller = RunController(archive, RecordedFoundersComposition(load_retained_inputs(ref)), RecordedTickDriver(), max_ticks=None, start_paused=True)
    controller.poll()
    controller.submit(CommandEnvelope('step', 'step', controller.status().state_version))
    for _ in range(4): controller.poll()
    assert controller.status().tick == 1
"""
    subprocess.run(
        [sys.executable, "-c", source, str(tmp_path), ref.attempt_id],
        check=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    with catalog.open_attempt(ref.attempt_id) as archive:
        saved = archive.checkpoint()
        assert archive.command("step").status == "applied"
    child = catalog.fork(ref.attempt_id, saved.revision)
    with (
        AttemptLease(child),
        catalog.open_attempt(child.attempt_id, read_only=False) as archive,
    ):
        controller = RunController(
            archive,
            RecordedFoundersComposition(load_retained_inputs(child)),
            RecordedTickDriver(),
            max_ticks=None,
            start_paused=False,
        )
        assert drive(controller).state is RuntimeState.COMPLETED
        assert controller.published().snapshot.digest == ROWS[0][2]


def test_recorded_zero_limit_finalize_modes(tmp_path: Path) -> None:
    catalog, ref = reserve(tmp_path, "success")
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        controller = RunController(
            archive,
            RecordedFoundersComposition(
                load_retained_inputs(ref), finalize_proposals=False
            ),
            RecordedTickDriver(),
            max_ticks=0,
            start_paused=False,
        )
        assert controller.poll().state is RuntimeState.COMPLETED
        assert controller.status().tick == 0
        assert controller.published().driver_cursor["next_index"] == 0
    catalog, ref = reserve(tmp_path / "strict", "success")
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        controller = RunController(
            archive,
            RecordedFoundersComposition(load_retained_inputs(ref)),
            RecordedTickDriver(),
            max_ticks=0,
            start_paused=False,
        )
        assert controller.poll().state is RuntimeState.FAILED
        assert archive.latest_revision is None


def test_tampered_retained_bytes_and_cursor_rejected(tmp_path: Path) -> None:
    _catalog, ref = reserve(tmp_path, "success")
    inputs = load_retained_inputs(ref)
    inputs.tape_path.write_bytes(inputs.tape_path.read_bytes() + b"\n")
    from living_world.archives import ArchiveFormatError

    with pytest.raises(ArchiveFormatError):
        RecordedFoundersComposition(inputs)


def test_discarded_recorded_candidate_is_collectable_while_composition_lives(
    tmp_path: Path,
) -> None:
    import gc
    import weakref

    _catalog, attempt = reserve(tmp_path, "success")
    composition = RecordedFoundersComposition(load_retained_inputs(attempt))
    current = composition.initialize()
    discarded = composition.restore(encode_world(current.state))
    discarded_ref = weakref.ref(discarded)
    del discarded
    gc.collect()
    assert discarded_ref() is None
    # Collection of another candidate must not remove the live engine's preparation.
    current.step()
    assert current.state.tick == 1
    composition.finalize(current, stopped=True)
    assert encode_world(current.state).schema_version == 12


def test_generic_recorded_without_tape_and_unknown_terminal(tmp_path: Path) -> None:
    from living_world.runtime import recorded

    assert hasattr(recorded, "RecordedScenarioComposition")
    (tmp_path / "world.yaml").write_text("definitions:\n  - key: person\n")
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text("""schema_version: 1
key: generic
seed: 7
definitions: world.yaml
run:
  max_ticks: 2
  terminal_conditions: [tick_limit]
entities:
  - label: actor
    definition: person
    name: Ada
relationships: []
""")
    catalog = RunCatalog(tmp_path / "runs")
    ref = catalog.reserve(AttemptConfig("recorded", "generic", 7, "test", {}))
    inputs = retain_inputs(ref, scenario_path, tape_path=None)
    composition = recorded.RecordedScenarioComposition(inputs, max_ticks=2)
    engine = composition.initialize()
    assert composition.terminal_condition(engine) is None
    engine.step()
    engine.step()
    assert composition.terminal_condition(engine) == "tick_limit"
    composition.finalize(engine, stopped=False)
    assert encode_world(
        composition.restore(encode_world(engine.state)).state
    ) == encode_world(engine.state)
    scenario_path.write_text(
        scenario_path.read_text().replace("[tick_limit]", "[unknown]")
    )
    ref2 = catalog.reserve(AttemptConfig("recorded", "generic", 7, "test", {}))
    with pytest.raises(ValueError):
        recorded.RecordedScenarioComposition(
            retain_inputs(ref2, scenario_path, tape_path=None)
        ).initialize()
