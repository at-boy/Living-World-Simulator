"""Exact linked restart and offline replay through the owner-thread service."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_runtime_service import reserved, wait_for

from living_world.archives import AttemptLease, CommandEnvelope
from living_world.runtime import RuntimeService, RuntimeStartupError, RuntimeState


def bytes_tree(directory: Path):
    return {
        p.relative_to(directory): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("hard", [False, True])
def test_real_process_checkpoint_then_exact_child_step(
    tmp_path: Path, hard: bool
) -> None:
    catalog, _config, ref, _inputs = reserved(tmp_path)
    source = """
import sys, time
from pathlib import Path
from living_world.archives import RunCatalog, load_retained_inputs, CommandEnvelope
from living_world.runtime import RuntimeService, RuntimeState
catalog=RunCatalog(Path(sys.argv[1]))
with catalog.open_attempt(sys.argv[2]) as archive:
    config, ref=archive.config, archive.ref
service=RuntimeService(catalog)
c=service.start(config,load_retained_inputs(ref),paused=True)
service.submit(CommandEnvelope('one','step',c.status().state_version)).result(2)
while not (c.status().tick==1 and c.status().state is RuntimeState.PAUSED): time.sleep(.005)
print('checkpoint',flush=True)
if sys.argv[3]=='hard':
    while True: time.sleep(.1)
service.shutdown()
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            source,
            str(catalog.root),
            ref.attempt_id,
            "hard" if hard else "normal",
        ],
        stdout=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    try:
        assert process.stdout.readline().strip() == "checkpoint"
        if hard:
            process.kill()
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(5)
    with AttemptLease(ref):
        pass
    with catalog.open_attempt(ref.attempt_id) as archive:
        saved = archive.checkpoint()
    before = bytes_tree(ref.directory)
    child = RuntimeService(catalog)
    controller = child.resume(ref.attempt_id, saved.revision, paused=True)
    try:
        first = controller.published()
        assert first.snapshot == saved.snapshot
        assert first.driver_cursor == saved.driver_cursor
        assert first.feedback_cursor == saved.feedback_cursor
        assert controller.status().state is RuntimeState.PAUSED
        child.submit(
            CommandEnvelope("next", "step", controller.status().state_version)
        ).result(2)
        wait_for(
            controller,
            lambda state: state.tick == 2 and state.state is RuntimeState.PAUSED,
        )
    finally:
        child.shutdown()
    assert bytes_tree(ref.directory) == before


@pytest.mark.parametrize("action", ["completed", "stopped"])
def test_operational_outcome_does_not_seal_nonterminal_world(
    tmp_path: Path, action: str
) -> None:
    catalog, config, ref, inputs = reserved(tmp_path, limits={"max_ticks": 1})
    service = RuntimeService(catalog)
    c = service.start(config, inputs, paused=action == "stopped")
    if action == "stopped":
        service.submit(
            CommandEnvelope("stop", "stop", c.status().state_version)
        ).result(2)
    wait_for(c, lambda state: state.state.terminal)
    saved = c.published()
    service.shutdown()
    child = RuntimeService(catalog)
    c = child.resume(ref.attempt_id, paused=True)
    try:
        assert c.status().state is RuntimeState.PAUSED
        assert c.published().snapshot == saved.snapshot
        child.submit(CommandEnvelope("one", "step", c.status().state_version)).result(2)
        wait_for(c, lambda state: state.tick == saved.driver_cursor["next_tick"] + 1)
    finally:
        child.shutdown()


def test_live_earlier_checkpoint_resume_is_pure_and_exact(
    tmp_path: Path, monkeypatch
) -> None:
    from test_runtime_ollama_driver import (
        ImmediateBroker,
        advance,
        initialized,
        live_archive,
    )

    from living_world.runtime import launch

    catalog, lease, source, live = live_archive(
        tmp_path, provider={"model": "local", "model_digest": "a" * 64}
    )
    try:
        driver, first = initialized(source, live, ImmediateBroker())
        advance(driver, live, source, first)
        attempt_id, ref = source.ref.attempt_id, source.ref
    finally:
        source.close()
        lease.release()
    before = bytes_tree(ref.directory)
    monkeypatch.setattr(launch, "preflight_provider", lambda config, **kwargs: config)
    service = RuntimeService(catalog)
    try:
        c = service.resume(attempt_id, first.revision, paused=True)
        assert c.published().snapshot == first.snapshot
        assert c.published().driver_cursor == first.driver_cursor
        assert c.published().feedback_cursor == first.feedback_cursor
    finally:
        service.shutdown()
    assert bytes_tree(ref.directory) == before


def test_replay_and_replay_resume_share_original_horizon(
    tmp_path: Path, monkeypatch
) -> None:
    from test_runtime_ollama_driver import (
        ActionBroker,
        advance,
        initialized,
        live_archive,
    )

    from living_world.runtime import launch

    catalog, lease, source, live = live_archive(tmp_path)
    try:
        driver, first = initialized(source, live, ActionBroker())
        second = advance(driver, live, source, first)
        third = advance(driver, live, source, second)
        ref = source.ref
    finally:
        source.close()
        lease.release()

    def forbidden(*args, **kwargs):
        raise AssertionError("HTTP forbidden")

    monkeypatch.setattr(launch, "preflight_provider", forbidden)
    before = bytes_tree(ref.directory)
    service = RuntimeService(catalog)
    c = service.replay(ref.attempt_id, third.revision, paused=True)
    replay_id = c.status().attempt.attempt_id
    try:
        assert c.published().snapshot == first.snapshot
        service.submit(CommandEnvelope("one", "step", c.status().state_version)).result(
            2
        )
        wait_for(
            c, lambda state: state.tick == 1 and state.state is RuntimeState.PAUSED
        )
        local = c.published()
        assert local.snapshot == second.snapshot
    finally:
        service.shutdown()
    service = RuntimeService(catalog)
    c = service.resume(replay_id, local.revision, paused=False)
    try:
        wait_for(c, lambda state: state.state.terminal)
        assert c.status().state is RuntimeState.COMPLETED
        assert c.published().snapshot == third.snapshot
        assert c.published().driver_cursor == third.driver_cursor
        assert c.published().feedback_cursor == third.feedback_cursor
    finally:
        service.shutdown()
    assert bytes_tree(ref.directory) == before


@pytest.mark.parametrize("mode", ["unknown", "cursor", "feedback"])
def test_recorded_terminal_zero_limit_still_validates_child_cp0(
    tmp_path: Path, mode: str
) -> None:
    catalog, config, ref, inputs = reserved(tmp_path, limits={"max_ticks": 0})
    service = RuntimeService(catalog)
    c = service.start(config, inputs, paused=False)
    saved = c.published()
    service.shutdown()
    cursor = dict(saved.driver_cursor)
    feedback = {}
    if mode == "unknown":
        cursor["mode"] = "unknown"
    elif mode == "cursor":
        cursor["next_tick"] = 99
    else:
        feedback = {"unexpected": "field"}
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        archive.commit(
            saved.snapshot,
            expected_revision=saved.revision,
            driver_cursor=cursor,
            feedback_cursor=feedback,
            entries=(),
        )
    before = bytes_tree(ref.directory)
    child = RuntimeService(catalog)
    with pytest.raises(RuntimeStartupError) as failure:
        child.resume(ref.attempt_id, paused=True)
    child.shutdown()
    assert failure.value.code == "incompatible_save"
    assert failure.value.ref != ref
    with catalog.open_attempt(failure.value.ref.attempt_id) as archive:
        assert archive.latest_revision == 0
        assert archive.lifecycle()[-1]["state"] == "failed"
        assert archive.checkpoint().driver_cursor == cursor
    assert bytes_tree(ref.directory) == before


def test_semantic_terminal_live_resume_skips_discovery_and_generation(
    tmp_path: Path, monkeypatch
) -> None:
    from test_runtime_ollama_driver import ImmediateBroker, initialized, live_archive

    from living_world.goals.model import GoalStatus
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime import launch

    catalog, lease, source, live = live_archive(
        tmp_path, provider={"model": "local", "model_digest": "a" * 64}
    )
    try:
        _driver, base = initialized(source, live, ImmediateBroker())
        candidate = live.restore(base.snapshot)
        candidate.goals.transition_goal("goal_founding", GoalStatus.FAILED)
        terminal = source.commit(
            encode_world(candidate.state),
            expected_revision=base.revision,
            driver_cursor=base.driver_cursor,
            feedback_cursor=base.feedback_cursor,
            entries=(),
        )
        ref = source.ref
    finally:
        source.close()
        lease.release()

    def forbidden(*args, **kwargs):
        raise AssertionError("Provider access on semantic terminal")

    monkeypatch.setattr(launch, "preflight_provider", forbidden)
    before = bytes_tree(ref.directory)
    service = RuntimeService(catalog)
    c = service.resume(ref.attempt_id, terminal.revision, paused=False)
    try:
        assert c.status().state is RuntimeState.COMPLETED
        assert c.status().tick == 0
        assert c.published().snapshot == terminal.snapshot
        with catalog.open_attempt(c.status().attempt.attempt_id) as archive:
            assert not any(
                entry.kind == "request_started" for entry in archive.entries()
            )
    finally:
        service.shutdown()
    assert bytes_tree(ref.directory) == before


def test_action_work_cognition_and_resource_continuity_across_process(
    tmp_path: Path,
) -> None:
    from test_runtime_ollama_driver import (
        ActionBroker,
        advance,
        initialized,
        live_archive,
    )
    from test_runtime_preflight import tags_server

    from living_world.repositories.world_snapshot import decode_world

    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as url:
        catalog, lease, source, live = live_archive(
            tmp_path,
            provider={
                "model": "tiny:latest",
                "model_digest": "a" * 64,
                "base_url": url,
                "timeout_seconds": 2,
            },
        )
        try:
            driver, zero = initialized(source, live, ActionBroker())
            first = advance(driver, live, source, advance(driver, live, source, zero))
            state = decode_world(first.snapshot)
            assert state.work_definitions and state.memories
            # Independent uninterrupted reference includes all manager state,
            # cognition, resources, work charge/completion and semantic cursors.
            expected = advance(driver, live, source, first)
            ref = source.ref
        finally:
            source.close()
            lease.release()
        before = bytes_tree(ref.directory)
        script = """
import sys,time
from pathlib import Path
from test_runtime_ollama_driver import ActionBroker
from living_world.runtime import RuntimeService,RuntimeState,launch
from living_world.archives import RunCatalog,CommandEnvelope
launch.DecisionBroker=ActionBroker
catalog=RunCatalog(Path(sys.argv[1]))
service=RuntimeService(catalog)
c=service.resume(sys.argv[2],int(sys.argv[3]),paused=True)
print(c.status().attempt.attempt_id,flush=True)
assert c.status().tick==2
service.submit(CommandEnvelope('one','step',c.status().state_version)).result(2)
end=time.monotonic()+5
while not (c.status().state is RuntimeState.PAUSED and c.status().tick==3):
    assert time.monotonic()<end,c.status()
    time.sleep(.005)
print(c.published().revision,flush=True)
service.shutdown()
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(catalog.root),
                ref.attempt_id,
                str(first.revision),
            ],
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
            env={**os.environ, "PYTHONPATH": "src:tests"},
        )
        ident, revision = completed.stdout.splitlines()
        with catalog.open_attempt(ident) as child:
            initial = child.checkpoint(0)
            actual = child.checkpoint(int(revision))
            assert initial.snapshot == first.snapshot
            assert initial.driver_cursor == first.driver_cursor
            assert initial.feedback_cursor == first.feedback_cursor
            assert actual.snapshot == expected.snapshot
            assert actual.driver_cursor == expected.driver_cursor
            assert actual.feedback_cursor == expected.feedback_cursor
            assert (
                len(
                    [
                        entry
                        for entry in child.entries()
                        if entry.kind == "action_resolved"
                    ]
                )
                == 2
            )
        assert bytes_tree(ref.directory) == before


def test_changed_provider_fork_and_pinned_model_failure_retain_exact_child(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from test_runtime_preflight import tags_server
    from test_runtime_service import live_reserved

    body = {
        "models": [
            {"name": "tiny:latest", "digest": "a" * 64},
            {"name": "other:latest", "digest": "b" * 64},
        ]
    }
    with tags_server(body) as url:
        catalog, config, ref, inputs = live_reserved(tmp_path, url)
        service = RuntimeService(catalog)
        c = service.start(config, inputs, paused=True)
        saved = c.published()
        service.shutdown()
        with catalog.open_attempt(ref.attempt_id) as source:
            original = source.config
        before = bytes_tree(ref.directory)
        settings = dict(original.settings)
        provider = dict(settings["provider"])
        provider["model"] = "other"
        provider.pop("model_digest")
        settings["provider"] = provider
        changed = replace(original, settings=settings)
        fork = RuntimeService(catalog)
        c = fork.fork(ref.attempt_id, 0, config=changed, paused=True)
        try:
            assert c.published().snapshot == saved.snapshot
            assert c.published().driver_cursor == saved.driver_cursor
            with catalog.open_attempt(c.status().attempt.attempt_id) as child:
                assert child.config.settings["provider"]["model"] == "other:latest"
                assert child.config.settings["provider"]["model_digest"] == "b" * 64
        finally:
            fork.shutdown()
        body["models"][0]["digest"] = "c" * 64
        failed = RuntimeService(catalog)
        with pytest.raises(RuntimeStartupError) as failure:
            failed.resume(ref.attempt_id, paused=True)
        failed.shutdown()
        assert failure.value.code == "model_digest_mismatch"
        assert failure.value.ref is not None and failure.value.ref != ref
        assert (
            next(
                a for a in catalog.attempts() if a.ref == failure.value.ref
            ).failure_code
            == "model_digest_mismatch"
        )
        assert bytes_tree(ref.directory) == before


def test_zero_tick_replay_rejects_semantically_invalid_source_cursor(
    tmp_path: Path,
) -> None:
    from test_runtime_ollama_driver import ImmediateBroker, initialized, live_archive

    catalog, lease, source, live = live_archive(tmp_path)
    try:
        _driver, base = initialized(source, live, ImmediateBroker())
        source.commit(
            base.snapshot,
            expected_revision=0,
            driver_cursor={**base.driver_cursor, "next_slot": 99},
            feedback_cursor=base.feedback_cursor,
            entries=(),
        )
        ref = source.ref
    finally:
        source.close()
        lease.release()
    service = RuntimeService(catalog)
    try:
        with pytest.raises(RuntimeStartupError) as failure:
            service.replay(ref.attempt_id, paused=False)
        assert failure.value.code == "incompatible_save"
        assert failure.value.ref is not None
    finally:
        service.shutdown()


@pytest.mark.parametrize("mode", ["recorded", "journal_replay"])
@pytest.mark.parametrize("operation", ["resume", "fork"])
@pytest.mark.parametrize("phase", ["retention", "before_cp0", "after_cp0"])
def test_linked_clone_failure_retains_known_failed_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    operation: str,
    phase: str,
) -> None:
    from living_world.archives import AttemptArchive
    from living_world.archives import catalog as catalog_module

    if mode == "recorded":
        catalog, config, ref, inputs = reserved(tmp_path)
        original = RuntimeService(catalog)
        controller = original.start(config, inputs, paused=True)
    else:
        from test_runtime_ollama_driver import (
            ActionBroker,
            advance,
            initialized,
            live_archive,
        )

        catalog, lease, source, live = live_archive(tmp_path)
        try:
            driver, base = initialized(source, live, ActionBroker())
            advance(driver, live, source, base)
            live_ref = source.ref
        finally:
            source.close()
            lease.release()
        original = RuntimeService(catalog)
        controller = original.replay(live_ref.attempt_id, paused=True)
        ref = controller.status().attempt
    saved = controller.published()
    original.shutdown()
    with catalog.open_attempt(ref.attempt_id) as source:
        config = source.config
    before = bytes_tree(ref.directory)
    original_commit = AttemptArchive.commit

    def commit(archive: AttemptArchive, *args, **kwargs):
        assert archive.parent == (ref.attempt_id, saved.revision)
        if phase == "after_cp0":
            original_commit(archive, *args, **kwargs)
        raise OSError("private clone failure")

    def retention(*args, **kwargs):
        raise OSError("private retention failure")

    if phase == "retention":
        monkeypatch.setattr(catalog_module, "retain_inputs", retention)
    else:
        monkeypatch.setattr(AttemptArchive, "commit", commit)
    service = RuntimeService(catalog)
    try:
        with pytest.raises(RuntimeStartupError) as failure:
            if operation == "resume":
                service.resume(ref.attempt_id, saved.revision, paused=True)
            else:
                service.fork(ref.attempt_id, saved.revision, config=config, paused=True)
        assert failure.value.code == "archive_failed"
        child_ref = failure.value.ref
        assert child_ref is not None and child_ref != ref
        assert child_ref.lineage_id == ref.lineage_id
        with catalog.open_attempt(child_ref.attempt_id) as child:
            assert child.parent == (ref.attempt_id, saved.revision)
            assert child.latest_revision == (0 if phase == "after_cp0" else None)
            assert child.lifecycle()[-1]["state"] == "failed"
            assert child.lifecycle()[-1]["reason"] == "archive_failed"
            finished = child.entries()[-1]
            assert finished.kind == "attempt_finished"
            assert finished.payload["last_revision"] == child.latest_revision
            if phase == "after_cp0":
                assert child.checkpoint().snapshot == saved.snapshot
                assert child.checkpoint().driver_cursor == saved.driver_cursor
                assert child.checkpoint().feedback_cursor == saved.feedback_cursor
        with AttemptLease(child_ref):
            pass
    finally:
        service.shutdown()
    assert not service._thread.is_alive()
    assert bytes_tree(ref.directory) == before


@pytest.mark.parametrize("invalid_ref", ["source", "foreign", "wrong_parent"])
def test_allocated_fork_error_cannot_adopt_an_unrelated_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid_ref: str
) -> None:
    from living_world.archives.catalog import ArchiveReservationError

    catalog, config, ref, inputs = reserved(tmp_path)
    original = RuntimeService(catalog)
    original.start(config, inputs, paused=True)
    original.shutdown()
    if invalid_ref == "source":
        unrelated = ref
    elif invalid_ref == "foreign":
        foreign_dir = tmp_path / "foreign"
        foreign_dir.mkdir()
        _, _, unrelated, _ = reserved(foreign_dir)
    else:
        unrelated = catalog.reserve(config, parent=(ref.attempt_id, 1))
    source_before = bytes_tree(ref.directory)
    unrelated_before = bytes_tree(unrelated.directory)

    def fork(*args, **kwargs):
        raise ArchiveReservationError(unrelated)

    monkeypatch.setattr(catalog, "fork", fork)
    service = RuntimeService(catalog)
    try:
        with pytest.raises(RuntimeStartupError) as failure:
            service.resume(ref.attempt_id, 0, paused=True)
        assert failure.value.code == "archive_failed"
    finally:
        service.shutdown()
    assert bytes_tree(ref.directory) == source_before
    assert bytes_tree(unrelated.directory) == unrelated_before
    with AttemptLease(unrelated):
        pass
