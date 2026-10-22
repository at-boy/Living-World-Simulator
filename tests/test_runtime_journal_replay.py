"""Exact offline replay uses captured complete source worlds."""

from pathlib import Path

from living_world.runtime.journal_replay import (
    JournalReplayComposition,
    JournalReplayDriver,
)


def test_replay_types_are_available() -> None:
    assert JournalReplayComposition is not None
    assert JournalReplayDriver is not None


def test_complete_offline_replay_and_zero_tick_source(tmp_path: Path) -> None:
    from test_runtime_ollama_driver import (
        ActionBroker,
        advance,
        initialized,
        live_archive,
    )

    from living_world.archives import AttemptConfig, AttemptLease, retain_inputs
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.broker import client_for, encoded_body
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    catalog, lease, source, live = live_archive(tmp_path)
    target = None
    target_lease = None
    try:
        broker = ActionBroker()
        driver, base = initialized(source, live, broker)
        zero = JournalReplayComposition(source, live)
        assert zero.terminal_condition(zero.initialize()) == "journal_replay_complete"
        first = advance(driver, live, source, base)
        second = advance(driver, live, source, first)
        replay_config = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            "replay-rev",
            {"source_config_fingerprint": effective_config_fingerprint(source.config)},
        )
        ref = catalog.reserve(replay_config)
        from living_world.archives import load_retained_inputs

        inputs = retain_inputs(
            ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
        )
        target_lease = AttemptLease(ref)
        target_lease.acquire()
        target = catalog.open_attempt(ref.attempt_id, read_only=False)
        replay = JournalReplayComposition(source, FoundersLiveComposition(inputs))
        client = client_for(driver.config)
        feedback = FoundersFeedback(
            lambda context, options: len(
                encoded_body(client.build_payload(context, options))
            )
        )
        advance(driver, live, source, second)  # source advances between constructors
        replay_driver = JournalReplayDriver(
            source, feedback, source_point=replay.source_point
        )
        candidate = replay.initialize()
        commit = replay_driver.initialize(candidate, target)
        local = target.commit(
            encode_world(candidate.state),
            expected_revision=None,
            driver_cursor=commit.driver_cursor,
            feedback_cursor=commit.feedback_cursor,
            entries=(),
        )
        # Captured source excludes later appends/turns.
        local = advance(replay_driver, replay, target, local)
        assert local.snapshot == first.snapshot
        local = advance(replay_driver, replay, target, local)
        assert local.snapshot == second.snapshot
        assert (
            replay.terminal_condition(replay.restore(local.snapshot))
            == "journal_replay_complete"
        )
        assert not any(e.kind == "request_started" for e in target.entries())
        assert sum(e.kind == "response_reused" for e in target.entries()) == 4
    finally:
        if target is not None:
            target.close()
        if target_lease is not None:
            target_lease.release()
        source.close()
        lease.release()


def test_replay_child_starts_exact_nonzero_tick_and_updates_changed_config(
    tmp_path: Path,
) -> None:
    from test_runtime_ollama_driver import (
        ImmediateBroker,
        advance,
        initialized,
        live_archive,
    )

    from living_world.archives import (
        AttemptConfig,
        AttemptLease,
        load_retained_inputs,
        retain_inputs,
    )
    from living_world.repositories.world_snapshot import decode_world, encode_world
    from living_world.runtime.broker import client_for, encoded_body, provider_config
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.runtime.ollama_driver import (
        OllamaTickDriver,
        effective_config_fingerprint,
    )

    catalog, lease, parent, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(parent, live, broker)
        first = advance(driver, live, parent, base)
        changed = AttemptConfig(
            "ollama",
            parent.config.scenario_key,
            parent.config.seed,
            "test",
            {"provider": {"model": "changed"}},
        )
        child_ref = catalog.fork(parent.ref.attempt_id, 1, config=changed)
        with (
            AttemptLease(child_ref),
            catalog.open_attempt(child_ref.attempt_id, read_only=False) as source,
        ):
            config = provider_config(changed)
            client = client_for(config)
            feedback = FoundersFeedback(
                lambda context, options: len(
                    encoded_body(client.build_payload(context, options))
                )
            )
            child_driver = OllamaTickDriver(config, feedback, broker)
            last = advance(child_driver, live, source, source.checkpoint())
            replay_config = AttemptConfig(
                "journal_replay",
                changed.scenario_key,
                changed.seed,
                "replay",
                {"source_config_fingerprint": effective_config_fingerprint(changed)},
            )
            ref = catalog.reserve(replay_config)
            inputs = retain_inputs(
                ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
            )
            with (
                AttemptLease(ref),
                catalog.open_attempt(ref.attempt_id, read_only=False) as target,
            ):
                replay = JournalReplayComposition(
                    source, FoundersLiveComposition(inputs)
                )
                replay_driver = JournalReplayDriver(
                    source,
                    FoundersFeedback(
                        lambda context, options: len(
                            encoded_body(client.build_payload(context, options))
                        )
                    ),
                )
                candidate = replay.initialize()
                assert encode_world(candidate.state) == first.snapshot
                assert candidate.state.tick == 1
                commit = replay_driver.initialize(candidate, target)
                assert commit.driver_cursor[
                    "config_fingerprint"
                ] != effective_config_fingerprint(changed)
                local = target.commit(
                    encode_world(candidate.state),
                    expected_revision=None,
                    driver_cursor=commit.driver_cursor,
                    feedback_cursor=commit.feedback_cursor,
                    entries=(),
                )
                result = advance(replay_driver, replay, target, local)
                assert result.snapshot == last.snapshot
                assert result.driver_cursor == last.driver_cursor
                assert decode_world(result.snapshot).tick == 2
    finally:
        parent.close()
        lease.release()


def test_replay_rejects_mismatching_config_point_and_same_tick_cursor(
    tmp_path: Path,
) -> None:
    import pytest
    from test_runtime_ollama_driver import ImmediateBroker, initialized, live_archive

    from living_world.archives import (
        ArchiveFormatError,
        AttemptConfig,
        AttemptLease,
        ForkPoint,
        JournalBoundary,
        load_retained_inputs,
        retain_inputs,
    )
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.founders import FoundersLiveComposition

    _catalog, lease, source, live = live_archive(tmp_path)
    try:
        _driver, base = initialized(source, live, ImmediateBroker())
        point = source.fork_point()
        forged = ForkPoint(
            point.checkpoint, JournalBoundary(point.journal_boundary.sequence, "b" * 64)
        )
        with pytest.raises(ArchiveFormatError, match="source point mismatch"):
            JournalReplayComposition(source, live, source_point=forged)
        catalog = _catalog
        bad = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            "replay",
            {"source_config_fingerprint": "a" * 64},
        )
        ref = catalog.reserve(bad)
        inputs = retain_inputs(
            ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
        )
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as target,
        ):
            replay = JournalReplayComposition(source, FoundersLiveComposition(inputs))
            driver = JournalReplayDriver(
                source, FoundersFeedback(lambda _context, _options: 1)
            )
            with pytest.raises(
                ArchiveFormatError, match="configuration or inputs mismatch"
            ):
                driver.initialize(replay.initialize(), target)
        source.commit(
            base.snapshot,
            expected_revision=base.revision,
            driver_cursor={**base.driver_cursor, "next_slot": 1},
            feedback_cursor=base.feedback_cursor,
            entries=(),
        )
        with pytest.raises(ArchiveFormatError, match="same-tick"):
            JournalReplayComposition(source, live)
    finally:
        source.close()
        lease.release()
