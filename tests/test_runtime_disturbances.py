"""Fixed completed-boundary policies remain engine owned and replayable."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from living_world.archives import ArchiveFormatError, AttemptConfig, JournalEntry
from living_world.archives.model import BoundaryDisturbance, parse_boundary_disturbance
from living_world.runtime.broker import DecisionBroker
from living_world.runtime.disturbances import apply_boundary_disturbance


def config(kind="resource_loss", *, format=1):
    return AttemptConfig(
        "ollama",
        "canonical_founders_v1",
        7,
        "test",
        {
            "disturbance": kind,
            "boundary_disturbance": BoundaryDisturbance(
                kind=kind, format=format
            ).as_document(),
            "provider": {"model": "local"},
        },
    )


def test_schedule_is_closed_immutable_and_fingerprinted():
    import hashlib

    from living_world.archives.model import canonical

    policy = BoundaryDisturbance(kind="resource_loss")
    assert parse_boundary_disturbance(policy.as_document()) == policy
    assert (
        policy.fingerprint
        == hashlib.sha256(canonical(policy.as_document()).encode()).hexdigest()
    )
    with pytest.raises(FrozenInstanceError):
        policy.at_tick = 3
    for value in (
        {},
        {**policy.as_document(), "format": True},
        {**policy.as_document(), "at_tick": 3},
        {**policy.as_document(), "kind": "none"},
        {**policy.as_document(), "amount": 2},
    ):
        with pytest.raises(ArchiveFormatError):
            parse_boundary_disturbance(value)


def test_policy_requires_live_matching_label_and_legacy_is_inert():
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    base = AttemptConfig(
        "ollama", "canonical_founders_v1", 7, "test", {"provider": {"model": "local"}}
    )
    legacy = replace(base, settings={**base.settings, "disturbance": "resource_loss"})
    assert effective_config_fingerprint(base) == effective_config_fingerprint(legacy)
    assert effective_config_fingerprint(base) != effective_config_fingerprint(config())
    for mode, label in (
        ("recorded", "resource_loss"),
        ("journal_replay", "resource_loss"),
        ("ollama", "none"),
    ):
        with pytest.raises(ArchiveFormatError):
            replace(
                config(),
                mode=mode,
                settings={**config().settings, "disturbance": label},
            )


def test_resource_loss_is_all_stock_and_only_at_boundary(tmp_path: Path):
    from test_runtime_ollama_driver import live_archive

    from living_world.repositories.world_snapshot import encode_world

    _, lease, archive, live = live_archive(tmp_path)
    try:
        engine = live.initialize()
        policy = replace(archive.config, settings=config().settings)
        initial = encode_world(engine.state)
        assert apply_boundary_disturbance(engine, policy, base_revision=0) == ()
        assert encode_world(engine.state) == initial
        engine.step()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        before = engine.state.entities[camp].attributes["resources"]["timber"]
        rows = apply_boundary_disturbance(engine, policy, base_revision=1)
        assert len(rows) == 1
        row = rows[0]
        assert row.kind == "boundary_disturbance"
        assert row.payload["quantity_before"] == before > 0
        assert row.payload["quantity_after"] == 0
        assert engine.state.entities[camp].attributes["resources"]["timber"] == 0
        assert (
            engine.state.events[row.payload["event_references"][0]].kind
            == "runtime_resource_loss"
        )
        engine.step()
        assert apply_boundary_disturbance(engine, policy, base_revision=2) == ()
    finally:
        archive.close()
        lease.release()


def archived(tmp_path, kind, *, format=1):
    from living_world.archives import AttemptLease, RunCatalog, retain_inputs
    from living_world.founders.assets import materialize_founders_assets
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        scenario = YAMLScenarioLoader().load(assets.scenario)
        settings = {} if kind is None else dict(config(kind, format=format).settings)
        settings["provider"] = {"model": "local"}
        cfg = AttemptConfig("ollama", scenario.key, scenario.seed, "test", settings)
        ref = catalog.reserve(cfg)
        inputs = retain_inputs(ref, assets.scenario, tape_path=None)
    lease = AttemptLease(ref)
    lease.acquire()
    archive = catalog.open_attempt(ref.attempt_id, read_only=False)
    return catalog, lease, archive, FoundersLiveComposition(inputs)


@pytest.mark.parametrize(
    "kind,format", [("resource_loss", 1), ("work_blockage", 1), ("work_blockage", 2)]
)
def test_live_boundary_pause_restart_fork_and_exact_offline_replay(
    tmp_path, kind, format, monkeypatch
):
    from test_runtime_ollama_driver import ActionBroker, advance, initialized, ready

    from living_world.archives import AttemptLease, load_retained_inputs, retain_inputs
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.broker import client_for, encoded_body
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.runtime.journal_replay import (
        JournalReplayComposition,
        JournalReplayDriver,
    )
    from living_world.runtime.ollama_driver import (
        OllamaTickDriver,
        effective_config_fingerprint,
    )

    catalog, lease, source, live = archived(tmp_path, kind, format=format)
    try:
        broker = ShelterBroker() if format == 2 else ActionBroker()
        driver, initial = initialized(source, live, broker)
        first = advance(driver, live, source, initial)
        first = source.commit(
            first.snapshot,
            expected_revision=first.revision,
            driver_cursor=first.driver_cursor,
            feedback_cursor=first.feedback_cursor,
            entries=(),
        )
        source_bytes = first.snapshot
        candidate = live.restore(first.snapshot)
        staged = driver.prepare(candidate, first, source)
        assert ready(staged) == "ready"
        count = len(broker.calls)
        staged.request_pause()
        staged.close()
        assert source.checkpoint() == first
        assert not any(e.kind == "boundary_disturbance" for e in source.entries())
        # Cold driver reuses valid responses at the unchanged predecessor.
        cold = OllamaTickDriver(driver.config, driver.feedback, broker)
        second = advance(cold, live, source, first)
        assert len(broker.calls) == count
        assert first.snapshot == source_bytes
        rows = [e for e in source.entries() if e.kind == "boundary_disturbance"]
        assert len(rows) == 1
        assert rows[0].payload["outcome"] == (
            "applied" if kind == "resource_loss" or format == 2 else "no_eligible_work"
        )
        assert rows[0].payload["base_revision"] == first.revision
        third = advance(cold, live, source, second)
        assert sum(e.kind == "boundary_disturbance" for e in source.entries()) == 1
        assert (
            len([e for e in source.entries() if e.kind == "request_started"])
            == len(broker.calls)
            == 6
        )
        # The source's recorded policy, including exact world events, drives replay.
        replay_cfg = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            "replay",
            {"source_config_fingerprint": effective_config_fingerprint(source.config)},
        )
        ref = catalog.reserve(replay_cfg)
        inputs = retain_inputs(
            ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
        )
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as target,
        ):
            replay = JournalReplayComposition(source, FoundersLiveComposition(inputs))
            client = client_for(driver.config)
            feedback = FoundersFeedback(
                lambda context, options: len(
                    encoded_body(client.build_payload(context, options))
                )
            )
            replayer = JournalReplayDriver(source, feedback)
            # Any attempted transport, including through the old broker, is forbidden.
            monkeypatch.setattr(
                broker,
                "start",
                lambda *args: pytest.fail("provider called during replay"),
            )
            monkeypatch.setattr(
                "urllib.request.urlopen",
                lambda *args, **kwargs: pytest.fail("network during replay"),
            )
            engine = replay.initialize()
            commit = replayer.initialize(engine, target)
            local = target.commit(
                encode_world(engine.state),
                expected_revision=None,
                driver_cursor=commit.driver_cursor,
                feedback_cursor=commit.feedback_cursor,
                entries=(),
            )
            for expected in (first, second, third):
                local = advance(replayer, replay, target, local)
                assert local.snapshot == expected.snapshot
                assert local.driver_cursor == expected.driver_cursor
                assert local.feedback_cursor == expected.feedback_cursor
            assert not any(e.kind == "request_started" for e in target.entries())
            imported = [e for e in target.entries() if e.kind == "boundary_disturbance"]
            assert len(imported) == 1
            assert imported[0].payload["base_revision"] == 1
            assert all(
                imported[0].payload[k] == rows[0].payload[k]
                for k in rows[0].payload
                if k != "base_revision"
            )
        # Absolute world tick prevents repetition in children after the boundary.
        for point, expect in ((first, 1), (second, 0)):
            child_ref = catalog.fork(source.ref.attempt_id, point.revision)
            with (
                AttemptLease(child_ref),
                catalog.open_attempt(child_ref.attempt_id, read_only=False) as child,
            ):
                assert child.config == source.config
                assert child.checkpoint().snapshot == point.snapshot
                child_broker = ActionBroker()
                child_driver = OllamaTickDriver(
                    driver.config, driver.feedback, child_broker
                )
                advance(child_driver, live, child, child.checkpoint())
                assert (
                    sum(e.kind == "boundary_disturbance" for e in child.entries())
                    == expect
                )
    finally:
        source.close()
        lease.release()


@pytest.mark.parametrize("kind", ["resource_loss", "work_blockage"])
def test_no_effect_and_terminal_are_audited_without_manager_events(tmp_path, kind):
    from living_world.goals.model import GoalStatus
    from living_world.repositories.world_snapshot import encode_world

    _, lease, archive, live = archived(tmp_path, kind)
    try:
        engine = live.initialize()
        engine.step()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        if kind == "resource_loss":
            engine.entities.set_attribute(
                entity_id=camp,
                key="resources",
                value={"food": 0, "water": 0, "timber": 0},
            )
        before = encode_world(engine.state)
        (row,) = apply_boundary_disturbance(engine, archive.config, base_revision=1)
        assert row.payload["outcome"] == (
            "empty_stock" if kind == "resource_loss" else "no_eligible_work"
        )
        assert row.payload["event_references"] == ()
        assert encode_world(engine.state) == before
        # A terminal goal is ordinary engine authority; disturbance does not override it.
        engine.state.goal_states["goal_founding"] = replace(
            engine.state.goal_states["goal_founding"], status=GoalStatus.FAILED
        )
        before = encode_world(engine.state)
        (row,) = apply_boundary_disturbance(engine, archive.config, base_revision=1)
        assert row.payload["outcome"] == "terminal"
        assert encode_world(engine.state) == before
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize(
    "resources",
    [
        None,
        {"food": 1, "water": 2},
        {"food": 1, "water": 2, "timber": True},
        {"food": -1, "water": 2, "timber": 3},
        {"food": 1, "water": 2, "timber": 3, "ore": 1},
    ],
)
def test_malformed_resources_reject_before_mutation(tmp_path, resources):
    from living_world.repositories.world_snapshot import encode_world

    _, lease, archive, live = archived(tmp_path, "resource_loss")
    try:
        engine = live.initialize()
        engine.step()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        engine.entities.set_attribute(entity_id=camp, key="resources", value=resources)
        before = encode_world(engine.state)
        with pytest.raises(ArchiveFormatError):
            apply_boundary_disturbance(engine, archive.config, base_revision=1)
        assert encode_world(engine.state) == before
    finally:
        archive.close()
        lease.release()


def test_work_blockage_releases_reservation_and_uses_manager_order(tmp_path):
    from test_runtime_founders_feedback import create_work

    from living_world.work.model import WorkStatus

    _, lease, archive, live = archived(tmp_path, "work_blockage")
    try:
        engine = live.initialize()
        engine.step()
        engine.step()
        first = create_work(engine, "First water effort")
        second = create_work(engine, "Second water effort", quantity=2)
        engine.work.mark_ready(first.id)
        engine.work.mark_ready(second.id)
        engine.work.set_priority(second.id, 3)
        engine.work.assign_and_reserve(second.id, ())
        (reservation,) = engine.work.active_reservations()
        (row,) = apply_boundary_disturbance(engine, archive.config, base_revision=1)
        assert row.payload["target_id"] == second.id
        assert engine.state.work_states[first.id].status is WorkStatus.READY
        assert engine.state.work_states[second.id].status is WorkStatus.BLOCKED
        assert engine.state.work_reservations[reservation.id].released_tick == 2
        assert [
            engine.state.events[x].kind for x in row.payload["event_references"]
        ] == ["work_reservation_released", "work_order_blocked"]
    finally:
        archive.close()
        lease.release()


class ShelterBroker(DecisionBroker):
    """Fake inference proposes an ordinary canonical modest shelter offer."""

    def __init__(self):
        self.current = None
        self.calls = []

    def start(self, job_id, config, decision_input):
        self.calls.append(decision_input)
        self.current = (job_id, decision_input)

    def poll(self, job_id):
        from living_world.cognition import ActionRequest
        from living_world.cognition.npc_cognition_client import NPCDecision
        from living_world.runtime.broker import BrokerResult

        item = self.current[1]
        choice = next(
            (
                o
                for o in item.options
                if o.key == "build_shelter"
                and "Build a modest shelter" in o.target_labels
            ),
            None,
        )
        decision = (
            NPCDecision(
                None,
                ActionRequest(
                    choice.key, "Build a modest shelter", "We need shelter.", {}
                ),
            )
            if choice
            else NPCDecision("I will wait.", None)
        )
        return BrokerResult(job_id, decision, None, None, 0.0)

    def close(self):
        self.current = None


@pytest.mark.parametrize("kind", ["resource_loss", "work_blockage"])
def test_service_factory_commits_boundary_and_cold_resume_without_repeating(
    tmp_path, kind, monkeypatch
):
    from test_runtime_cli import live_args
    from test_runtime_ollama_driver import ActionBroker
    from test_runtime_preflight import tags_server
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope, RunCatalog
    from living_world.cli import build_parser
    from living_world.runtime import RuntimeState
    from living_world.runtime import launch as launch_module
    from living_world.runtime.entrypoints import prepare_archived_launch

    monkeypatch.setattr(
        launch_module,
        "DecisionBroker",
        ShelterBroker if kind == "work_blockage" else ActionBroker,
    )
    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as url:
        catalog = RunCatalog(tmp_path / "runs")
        args = build_parser().parse_args(live_args(catalog.root, url))
        announced = []
        prepared = prepare_archived_launch(
            args, catalog=catalog, on_reserved=announced.append, disturbance=kind
        )
        assert not catalog.attempts()
        controller = prepared.launch(paused=True)
        try:
            for tick in (1, 2):
                prepared.service.submit(
                    CommandEnvelope(
                        f"step-{tick}", "step", controller.status().state_version
                    )
                ).result(2)
                wait_for(
                    controller,
                    lambda s, tick=tick: s.tick == tick
                    and s.state is RuntimeState.PAUSED,
                )
            published = controller.published()
            with catalog.open_attempt(announced[0].attempt_id) as source:
                saved = source.checkpoint()
                assert saved.snapshot == published.snapshot
                rows = [e for e in source.entries() if e.kind == "boundary_disturbance"]
                assert len(rows) == 1
                assert rows[0].payload["outcome"] == "applied"
                if kind == "work_blockage":
                    from living_world.repositories.world_snapshot import decode_world
                    from living_world.work.model import WorkStatus

                    world = decode_world(saved.snapshot)
                    selected = rows[0].payload["target_id"]
                    state = world.work_states[selected]
                    assert (
                        state.status is WorkStatus.BLOCKED
                        and state.progress == 0
                        and state.inputs_charged_tick is None
                    )
                    assert all(
                        world.events[ref].tick == 1
                        for ref in rows[0].payload["event_references"]
                    )
                    assert not any(
                        e.kind in ("work_inputs_charged", "work_order_progressed")
                        and e.subject_id == selected
                        for e in world.events.values()
                    )
                    camp = world.scenario_entity_bindings["camp"]
                    assert world.entities[camp].attributes["resources"]["timber"] == 10
                assert (
                    source.config.settings["boundary_disturbance"]
                    == BoundaryDisturbance(
                        kind=kind, format=2 if kind == "work_blockage" else 1
                    ).as_document()
                )
        finally:
            prepared.service.shutdown()
        args = build_parser().parse_args(
            ["run", "--resume-attempt", announced[0].attempt_id]
        )
        for invalid in (
            "none",
            "work_blockage" if kind == "resource_loss" else "resource_loss",
        ):
            with pytest.raises(Exception) as failure:
                prepare_archived_launch(
                    args,
                    catalog=catalog,
                    on_reserved=lambda ref: None,
                    disturbance=invalid,
                )
            assert failure.value.reason == "invalid_configuration"
        resumed = prepare_archived_launch(
            args, catalog=catalog, on_reserved=lambda ref: None, disturbance=kind
        )
        child = resumed.launch(paused=True)
        try:
            assert child.status().tick == 2
            resumed.service.submit(
                CommandEnvelope("third", "step", child.status().state_version)
            ).result(2)
            wait_for(child, lambda s: s.tick == 3 and s.state is RuntimeState.PAUSED)
            with catalog.open_attempt(announced[0].attempt_id) as source:
                assert (
                    sum(e.kind == "boundary_disturbance" for e in source.entries()) == 1
                )
                if kind == "work_blockage":
                    from living_world.archives.model import canonical
                    from living_world.repositories.world_snapshot import decode_world

                    with catalog.open_attempt(
                        child.status().attempt.attempt_id
                    ) as resumed_archive:
                        world = decode_world(resumed_archive.checkpoint().snapshot)
                        assert not any(
                            e.kind == "boundary_disturbance"
                            for e in resumed_archive.entries()
                        )
                        requests = [
                            e
                            for e in resumed_archive.entries()
                            if e.kind == "request_started"
                            and e.payload["source_tick"] == 2
                        ]
                    assert world.work_states[selected].status is WorkStatus.COMPLETED
                    assert requests and any(
                        "This work cannot currently proceed."
                        in canonical(e.payload["request"])
                        for e in requests
                    )
                    for entry in requests:
                        text = canonical(entry.payload["request"])
                        for hidden in (
                            "boundary_disturbance",
                            "schedule_fingerprint",
                            "event_",
                            "entity_",
                            "execution_tick",
                        ):
                            assert hidden not in text

        finally:
            resumed.service.shutdown()


@pytest.mark.parametrize("value", [True, 1, "bad", [], {}])
def test_factory_rejects_unknown_choices_before_side_effects(tmp_path, value):
    from living_world.archives import RunCatalog
    from living_world.cli import build_parser
    from living_world.runtime.entrypoints import (
        RuntimeCLIError,
        prepare_archived_launch,
    )

    catalog = RunCatalog(tmp_path / "runs")
    args = build_parser().parse_args(["run", "--founders", "success"])
    with pytest.raises(RuntimeCLIError):
        prepare_archived_launch(
            args, catalog=catalog, on_reserved=lambda ref: None, disturbance=value
        )
    assert not catalog.attempts()


@pytest.mark.parametrize("value", ["none", "resource_loss", "work_blockage"])
def test_factory_rejects_recorded_and_replay_explicit_choices(tmp_path, value):
    from uuid import uuid4

    from living_world.archives import RunCatalog
    from living_world.cli import build_parser
    from living_world.runtime.entrypoints import (
        RuntimeCLIError,
        prepare_archived_launch,
    )

    catalog = RunCatalog(tmp_path / "runs")
    for flags in (["--founders", "success"], ["--replay-attempt", uuid4().hex]):
        args = build_parser().parse_args(["run", *flags])
        with pytest.raises(RuntimeCLIError):
            prepare_archived_launch(
                args, catalog=catalog, on_reserved=lambda ref: None, disturbance=value
            )
        assert not catalog.attempts()


@pytest.mark.parametrize("failure_site", ["manager", "event"])
@pytest.mark.parametrize("policy_kind", ["resource_loss", "work_blockage"])
def test_failed_boundary_never_advances_service_archive_or_publication(
    tmp_path, monkeypatch, failure_site, policy_kind
):
    from test_runtime_cli import live_args
    from test_runtime_ollama_driver import ActionBroker
    from test_runtime_preflight import tags_server
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope, RunCatalog
    from living_world.cli import build_parser
    from living_world.managers.entity_manager import EntityManager
    from living_world.managers.event_manager import EventManager
    from living_world.runtime import RuntimeState
    from living_world.runtime import launch as launch_module
    from living_world.runtime.entrypoints import prepare_archived_launch

    monkeypatch.setattr(
        launch_module,
        "DecisionBroker",
        ShelterBroker if policy_kind == "work_blockage" else ActionBroker,
    )
    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as url:
        catalog = RunCatalog(tmp_path / "runs")
        args = build_parser().parse_args(live_args(catalog.root, url))
        prepared = prepare_archived_launch(
            args,
            catalog=catalog,
            on_reserved=lambda ref: None,
            disturbance=policy_kind,
        )
        controller = prepared.launch(paused=True)
        try:
            prepared.service.submit(
                CommandEnvelope("first", "step", controller.status().state_version)
            ).result(2)
            wait_for(
                controller, lambda s: s.tick == 1 and s.state is RuntimeState.PAUSED
            )
            before = controller.published()
            if failure_site == "event":
                original = EventManager.record

                def failed(self, *, kind, **kwargs):
                    if kind == (
                        "work_order_blocked"
                        if policy_kind == "work_blockage"
                        else "runtime_resource_loss"
                    ):
                        raise RuntimeError("Injected after entity manager mutation")
                    return original(self, kind=kind, **kwargs)

                monkeypatch.setattr(EventManager, "record", failed)
            elif policy_kind == "work_blockage":
                from living_world.work.manager import WorkManager

                def failed(*args):
                    raise RuntimeError("Injected work manager failure")

                monkeypatch.setattr(WorkManager, "block", failed)
            else:
                original = EntityManager.set_attribute

                def failed(self, *, entity_id, key, value):
                    if key == "resources" and value.get("timber") == 0:
                        raise RuntimeError("Injected entity manager failure")
                    return original(self, entity_id=entity_id, key=key, value=value)

                monkeypatch.setattr(EntityManager, "set_attribute", failed)
            prepared.service.submit(
                CommandEnvelope("second", "step", controller.status().state_version)
            ).result(2)
            wait_for(controller, lambda s: s.state.terminal)
            assert controller.published() == before
            with catalog.open_attempt(
                controller.status().attempt.attempt_id
            ) as archive:
                assert archive.checkpoint() == before
                assert not any(
                    e.kind == "boundary_disturbance" for e in archive.entries()
                )
        finally:
            prepared.service.shutdown()


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "wrong_base", "quantity", "event", "schedule"]
)
@pytest.mark.parametrize(
    "policy_kind,format", [("resource_loss", 1), ("work_blockage", 2)]
)
def test_replay_rejects_sealed_semantic_boundary_faults_without_next_commit(
    tmp_path, fault, monkeypatch, policy_kind, format
):
    from test_runtime_ollama_driver import ActionBroker, advance, initialized

    from living_world.archives import AttemptLease, load_retained_inputs, retain_inputs
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime import ollama_driver
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.runtime.journal_replay import (
        JournalReplayComposition,
        JournalReplayDriver,
    )
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    catalog, lease, source, live = archived(tmp_path, policy_kind, format=format)
    original = ollama_driver.apply_boundary_disturbance

    def faulty(candidate, cfg, *, base_revision, prepared=None):
        rows = original(candidate, cfg, base_revision=base_revision, prepared=prepared)
        if fault == "extra" and candidate.state.tick == 1:
            return (
                JournalEntry(
                    "boundary_disturbance",
                    {
                        "base_revision": base_revision,
                        "boundary_tick": 2,
                        "kind": "work_blockage",
                        "schedule_fingerprint": BoundaryDisturbance(
                            kind="work_blockage"
                        ).fingerprint,
                        "outcome": "no_eligible_work",
                        "target_id": None,
                        "resource": None,
                        "quantity_before": None,
                        "quantity_after": None,
                        "event_references": (),
                    },
                ),
            )
        if not rows:
            return rows
        if fault == "missing":
            return ()
        p = dict(rows[0].payload)
        if fault == "wrong_base":
            p["base_revision"] = base_revision + 1
        elif fault == "quantity":
            if policy_kind == "resource_loss":
                p["quantity_before"] += 1
            else:
                p["target_id"] = "work_wrong"
        elif fault == "event":
            p["event_references"] = ("event_nonexistent",)
        elif fault == "schedule" and format == 2:
            p["schedule_fingerprint"] = BoundaryDisturbance(
                kind="work_blockage", format=1
            ).fingerprint
        elif fault == "schedule":
            p.update(
                kind="work_blockage",
                schedule_fingerprint=BoundaryDisturbance(
                    kind="work_blockage"
                ).fingerprint,
                resource=None,
                quantity_before=None,
                quantity_after=None,
            )
        return (JournalEntry("boundary_disturbance", p),)

    monkeypatch.setattr(ollama_driver, "apply_boundary_disturbance", faulty)
    try:
        driver, base = initialized(
            source, live, ShelterBroker() if format == 2 else ActionBroker()
        )
        first = advance(driver, live, source, base)
        advance(driver, live, source, first)
        replay_cfg = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            "replay",
            {"source_config_fingerprint": effective_config_fingerprint(source.config)},
        )
        ref = catalog.reserve(replay_cfg)
        inputs = retain_inputs(
            ref, load_retained_inputs(source.ref).scenario_path, tape_path=None
        )
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as target,
        ):
            replay = JournalReplayComposition(source, FoundersLiveComposition(inputs))
            # Use the exact same byte budget function as live.
            replayer = JournalReplayDriver(source, driver.feedback)
            engine = replay.initialize()
            commit = replayer.initialize(engine, target)
            local = target.commit(
                encode_world(engine.state),
                expected_revision=None,
                driver_cursor=commit.driver_cursor,
                feedback_cursor=commit.feedback_cursor,
                entries=(),
            )
            if fault != "extra":
                local = advance(replayer, replay, target, local)
            with pytest.raises(ArchiveFormatError, match="boundary disturbance"):
                advance(replayer, replay, target, local)
            assert target.checkpoint() == local
            assert not any(e.kind == "boundary_disturbance" for e in target.entries())
    finally:
        source.close()
        lease.release()


@pytest.mark.parametrize("active", [False, True])
def test_gateway_created_work_blocks_and_ready_stale_offer_rejects(tmp_path, active):
    from living_world.cognition import ActionRequest
    from living_world.repositories.world_snapshot import encode_world
    from living_world.work import (
        ResourceWorkTarget,
        WorkActionHandler,
        WorkAssignmentOffer,
        WorkCategory,
        WorkCreationOffer,
        WorkStatus,
    )

    _, lease, archive, live = archived(tmp_path, "work_blockage")
    try:
        engine = live.initialize()
        engine.step()  # Goals become active through ordinary systems.
        if not active:
            engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        actor = engine.state.scenario_entity_bindings["ada"]
        offer = WorkCreationOffer(
            "Gather water",
            WorkCategory.GATHER_WATER,
            ResourceWorkTarget("water", 2),
            camp,
            "objective_founders_water",
            camp,
            labor_required=1,
            required_progress=5,
        )
        handler = WorkActionHandler(
            engine.state, engine.definitions, engine.work, actor, (offer,)
        )
        assert handler.apply(
            actor_id=actor,
            request=ActionRequest("gather_water", "Gather water", "We need water.", {}),
        ).accepted
        (work,) = engine.work.all()
        engine.work.mark_ready(work.id)
        stale = WorkActionHandler(
            engine.state,
            engine.definitions,
            engine.work,
            actor,
            assignment_offers=(WorkAssignmentOffer("Volunteer for water", work.id),),
        )
        request = ActionRequest(
            "volunteer_for_work", "Volunteer for water", "I can help.", {}
        )
        if active:
            engine.step()
            assert engine.state.work_states[work.id].status is WorkStatus.ACTIVE
        else:
            assert stale.validate(actor_id=actor, request=request).accepted
        (row,) = apply_boundary_disturbance(engine, archive.config, base_revision=1)
        assert row.payload["target_id"] == work.id
        assert engine.state.work_states[work.id].status is WorkStatus.BLOCKED
        assert [
            engine.state.events[x].kind for x in row.payload["event_references"]
        ] == (
            ["work_reservation_released", "work_order_blocked"]
            if active
            else ["work_order_blocked"]
        )
        before = encode_world(engine.state)
        result = stale.validate(
            actor_id=actor,
            request=ActionRequest(
                "volunteer_for_work", "Volunteer for water", "I can help.", {}
            ),
        )
        assert not result.accepted
        assert encode_world(engine.state) == before
    finally:
        archive.close()
        lease.release()


def test_stale_shelter_creation_offer_rejects_after_resource_loss(tmp_path):
    from living_world.api.inspection import EngineWorldInspector
    from living_world.cognition import ActionRequest
    from living_world.founders.model import canonical_policy
    from living_world.founders.runtime import FoundersLiveOfferProvider
    from living_world.repositories.world_snapshot import encode_world

    _, lease, archive, live = archived(tmp_path, "resource_loss")
    try:
        engine = live.initialize()
        engine.step()
        engine.step()
        actor = engine.state.scenario_entity_bindings["ada"]
        offered = FoundersLiveOfferProvider(engine, canonical_policy()).offers(
            actor_id=actor, inspector=EngineWorldInspector(engine)
        )
        request = ActionRequest(
            "build_shelter", "Build a modest shelter", "We need shelter.", {}
        )
        handler = next(
            h
            for h in offered.handlers
            if any(o.key == "build_shelter" for o in h.action_options)
        )
        assert handler.validate(actor_id=actor, request=request).accepted
        apply_boundary_disturbance(engine, archive.config, base_revision=1)
        before = encode_world(engine.state)
        assert not handler.validate(actor_id=actor, request=request).accepted
        assert encode_world(engine.state) == before
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize(
    "source_kind,target_kind",
    [
        (None, "resource_loss"),
        ("resource_loss", None),
        ("resource_loss", "work_blockage"),
    ],
)
def test_catalog_cannot_enable_clear_or_change_active_policy(
    tmp_path, source_kind, target_kind
):
    from test_runtime_ollama_driver import ImmediateBroker, initialized

    catalog, lease, source, live = archived(tmp_path, source_kind)
    try:
        _, base = initialized(source, live, ImmediateBroker())
        before = {
            p: p.read_bytes() for p in source.ref.directory.rglob("*") if p.is_file()
        }
        count = len(catalog.attempts())
        settings = {
            k: v
            for k, v in source.config.settings.items()
            if k not in ("disturbance", "boundary_disturbance")
        }
        if target_kind is not None:
            settings.update(
                disturbance=target_kind,
                boundary_disturbance=BoundaryDisturbance(
                    kind=target_kind
                ).as_document(),
            )
        with pytest.raises(ArchiveFormatError, match="policy"):
            catalog.fork(
                source.ref.attempt_id,
                base.revision,
                config=replace(source.config, settings=settings),
            )
        assert len(catalog.attempts()) == count
        assert before == {
            p: p.read_bytes() for p in source.ref.directory.rglob("*") if p.is_file()
        }
    finally:
        source.close()
        lease.release()


def test_legacy_fingerprint_retains_exact_reference_hash():
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    base = AttemptConfig(
        "ollama", "canonical_founders_v1", 7, "test", {"provider": {"model": "local"}}
    )
    assert (
        effective_config_fingerprint(base)
        == "9c3a9e2bf4db4312cf0f71816ff6bb27b33a98a86a66613d794145c5b2ac210a"
    )
    for label in ("none", "resource_loss", "work_blockage"):
        assert effective_config_fingerprint(
            replace(base, settings={**base.settings, "disturbance": label})
        ) == effective_config_fingerprint(base)
    assert effective_config_fingerprint(
        config("resource_loss")
    ) != effective_config_fingerprint(config("work_blockage"))


def test_next_feedback_removes_unavailable_resource_offers_and_hides_audit(tmp_path):
    from test_runtime_ollama_driver import ImmediateBroker, advance, initialized

    from living_world.cognition.local_llm_cognition_format import (
        serialize_decision_request,
    )
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.feedback import FoundersFeedback

    _, lease, source, live = archived(tmp_path, "resource_loss")
    try:
        driver, base = initialized(source, live, ImmediateBroker())
        first = advance(driver, live, source, base)
        before_engine = live.restore(first.snapshot)
        before_items = driver.feedback.prepare(before_engine, first)
        assert any(
            o.key == "build_shelter" for item in before_items for o in item.options
        )
        second = advance(driver, live, source, first)
        candidate = live.restore(second.snapshot)
        items = driver.feedback.prepare(candidate, second)
        assert all(
            o.key not in ("build_shelter", "build_storage")
            for item in items
            for o in item.options
        )
        serialized = "\n".join(
            serialize_decision_request(i.context, i.options) for i in items
        )
        for hidden in (
            "boundary_disturbance",
            "schedule_fingerprint",
            "base_revision",
            "quantity_before",
            "runtime_resource_loss",
            "entity_",
            "event_",
            "work_000",
            "checkpoint",
            "WorldState",
        ):
            assert hidden not in serialized
        # Repeated preparation and cold feedback restart retain owner record identities.
        snapshot = encode_world(candidate.state)
        repeated = driver.feedback.prepare(candidate, second)
        assert [serialize_decision_request(i.context, i.options) for i in repeated] == [
            serialize_decision_request(i.context, i.options) for i in items
        ]
        assert encode_world(candidate.state) == snapshot
        cold_engine = live.restore(second.snapshot)
        cold = FoundersFeedback(driver.feedback._request_size)
        cold_items = cold.prepare(cold_engine, second)
        assert [
            serialize_decision_request(i.context, i.options) for i in cold_items
        ] == [serialize_decision_request(i.context, i.options) for i in items]
        assert encode_world(cold_engine.state) == snapshot
    finally:
        source.close()
        lease.release()


@pytest.mark.parametrize(
    "mutation",
    [
        {"base_revision": True},
        {"boundary_tick": True},
        {"boundary_tick": 3},
        {"kind": "none"},
        {"schedule_fingerprint": "a" * 64},
        {"outcome": "no_eligible_work"},
        {"target_id": None},
        {"resource": "water"},
        {"quantity_before": 0},
        {"quantity_after": 1},
        {"event_references": []},
        {"event_references": ["event_1", "event_1"]},
        {"unexpected": 1},
    ],
)
def test_boundary_journal_rejects_closed_grammar_violations(mutation):
    payload = {
        "base_revision": 1,
        "boundary_tick": 2,
        "kind": "resource_loss",
        "schedule_fingerprint": BoundaryDisturbance(kind="resource_loss").fingerprint,
        "outcome": "applied",
        "target_id": "camp",
        "resource": "timber",
        "quantity_before": 10,
        "quantity_after": 0,
        "event_references": ["event_1"],
    }
    with pytest.raises(ArchiveFormatError):
        JournalEntry("boundary_disturbance", {**payload, **mutation})


def test_replay_rejects_boundary_audit_appended_outside_advancing_commit(tmp_path):
    from test_runtime_ollama_driver import ImmediateBroker, advance, initialized

    from living_world.runtime.journal_replay import JournalReplayComposition

    _, lease, source, live = archived(tmp_path, "resource_loss")
    try:
        driver, base = initialized(source, live, ImmediateBroker())
        first = advance(driver, live, source, base)
        advance(driver, live, source, first)
        original = next(e for e in source.entries() if e.kind == "boundary_disturbance")
        source.append(original)
        with pytest.raises(ArchiveFormatError, match="boundary disturbance"):
            JournalReplayComposition(source, live)
    finally:
        source.close()
        lease.release()


def test_fresh_none_and_default_retain_identical_config_and_initial_world(
    tmp_path, monkeypatch
):
    from test_runtime_cli import live_args
    from test_runtime_ollama_driver import ImmediateBroker
    from test_runtime_preflight import tags_server

    from living_world.archives import RunCatalog
    from living_world.cli import build_parser
    from living_world.runtime import launch as launch_module
    from living_world.runtime.entrypoints import prepare_archived_launch

    monkeypatch.setattr(launch_module, "DecisionBroker", ImmediateBroker)
    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as url:
        captured = []
        for index, policy in enumerate((None, "none")):
            catalog = RunCatalog(tmp_path / str(index))
            args = build_parser().parse_args(live_args(catalog.root, url))
            prepared = prepare_archived_launch(
                args, catalog=catalog, on_reserved=lambda ref: None, disturbance=policy
            )
            controller = prepared.launch(paused=True)
            try:
                with catalog.open_attempt(
                    controller.status().attempt.attempt_id
                ) as archive:
                    assert "disturbance" not in archive.config.settings
                    assert "boundary_disturbance" not in archive.config.settings
                    captured.append((archive.config, archive.checkpoint()))
            finally:
                prepared.service.shutdown()
        assert captured[0] == captured[1]


def test_catalog_live_to_replay_omits_target_policy_but_retains_source_snapshot(
    tmp_path,
):
    from test_runtime_ollama_driver import ImmediateBroker, advance, initialized

    from living_world.archives import AttemptLease
    from living_world.runtime.ollama_driver import effective_config_fingerprint

    catalog, lease, source, live = archived(tmp_path, "resource_loss")
    try:
        driver, base = initialized(source, live, ImmediateBroker())
        last = advance(driver, live, source, advance(driver, live, source, base))
        cfg = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            "replay",
            {"source_config_fingerprint": effective_config_fingerprint(source.config)},
        )
        before = {
            p: p.read_bytes() for p in source.ref.directory.rglob("*") if p.is_file()
        }
        child_ref = catalog.fork(source.ref.attempt_id, last.revision, config=cfg)
        with (
            AttemptLease(child_ref),
            catalog.open_attempt(child_ref.attempt_id) as child,
        ):
            assert "boundary_disturbance" not in child.config.settings
            assert child.checkpoint().snapshot == last.snapshot
        assert before == {
            p: p.read_bytes() for p in source.ref.directory.rglob("*") if p.is_file()
        }
    finally:
        source.close()
        lease.release()


@pytest.mark.parametrize("bad", [None, "", 3, True])
def test_interruption_request_and_result_closed_types(bad):
    from living_world.work.interruption import (
        WorkInterruptionRequest,
        WorkInterruptionResult,
    )

    with pytest.raises((TypeError, ValueError)):
        WorkInterruptionRequest(settlement_id=bad, execution_tick=1)
    request = WorkInterruptionRequest(settlement_id="camp", execution_tick=1)
    for tick in (True, -1, 1.0):
        with pytest.raises((TypeError, ValueError)):
            WorkInterruptionRequest(settlement_id="camp", execution_tick=tick)
    with pytest.raises((TypeError, ValueError)):
        WorkInterruptionResult(
            request=request, outcome="applied", work_id=bad, event_references=()
        )
    for refs in (("e", "e"), ["e"], ("",)):
        with pytest.raises((TypeError, ValueError)):
            WorkInterruptionResult(
                request=request,
                outcome="applied",
                work_id="work",
                event_references=refs,
            )


@pytest.mark.parametrize("reserved", [False, True])
def test_atomic_phase_interrupts_first_executable_without_labor_lock_or_charge(
    tmp_path, reserved
):
    from living_world.work import (
        ResourceRequirement,
        ResourceWorkTarget,
        ToolRequirement,
        WorkCategory,
        WorkStatus,
    )
    from living_world.work.interruption import WorkInterruptionRequest

    _, lease, archive, live = archived(tmp_path, "work_blockage", format=2)
    try:
        engine = live.initialize()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        actor = engine.state.scenario_entity_bindings["ada"]
        quantities = dict(engine.state.entities[camp].attributes["resources"])
        quantities["water"] = 1
        engine.entities.set_attribute(entity_id=camp, key="resources", value=quantities)
        orders = [
            engine.work.create(
                category=WorkCategory.GATHER_WATER,
                target=ResourceWorkTarget("water", 2),
                public_label=label,
                settlement_id=camp,
                objective_id="objective_founders_water",
                location_id=camp,
                labor_required=1,
                resources=(ResourceRequirement("timber", 1),),
                tools=(ToolRequirement("water", 1),),
                required_progress=1,
            )
            for label in ("First water effort", "Second water effort")
        ]
        engine.work.set_priority(orders[0].id, 5)
        if reserved:
            engine.work.mark_ready(orders[0].id)
            engine.work.assign_and_reserve(orders[0].id, (actor,))
        before = engine.state.entities[camp].attributes["resources"]["timber"]
        request = WorkInterruptionRequest(settlement_id=camp, execution_tick=1)
        engine.configure_work_interruption(request)
        engine.step()
        result = engine.work_interruption_result
        assert (
            result.request == request
            and result.work_id == orders[0].id
            and result.outcome == "applied"
        )
        first = engine.state.work_states[orders[0].id]
        assert (
            first.status is WorkStatus.BLOCKED
            and first.progress == 0
            and first.inputs_charged_tick is None
        )
        assert engine.state.work_states[orders[1].id].status is WorkStatus.COMPLETED
        assert engine.work.reservations_for(orders[1].id)[0].labor_entity_ids == (
            actor,
        )
        assert (
            engine.state.entities[camp].attributes["resources"]["timber"] == before - 1
        )
        assert [engine.state.events[ref].kind for ref in result.event_references] == (
            ["work_reservation_released", "work_order_blocked"]
            if reserved
            else ["work_order_blocked"]
        )
        assert all(
            engine.state.events[ref].tick == 1 for ref in result.event_references
        )
        engine.configure_work_interruption(None)
        assert engine.work_interruption_result is None
        engine.step()
        assert engine.state.work_states[orders[0].id].status is WorkStatus.COMPLETED
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize("unavailable", [False, True])
def test_format_two_zero_or_unavailable_work_no_eligible_result(tmp_path, unavailable):
    from living_world.runtime.disturbances import prepare_boundary_disturbance
    from living_world.work import ResourceWorkTarget, WorkCategory, WorkStatus

    _, lease, archive, live = archived(tmp_path, "work_blockage", format=2)
    try:
        engine = live.initialize()
        engine.step()
        if unavailable:
            camp = engine.state.scenario_entity_bindings["camp"]
            work = engine.work.create(
                category=WorkCategory.GATHER_WATER,
                target=ResourceWorkTarget("water", 2),
                public_label="Large water effort",
                settlement_id=camp,
                objective_id="objective_founders_water",
                location_id=camp,
                labor_required=3,
            )
        token = prepare_boundary_disturbance(engine, archive.config)
        engine.step()
        (row,) = apply_boundary_disturbance(
            engine, archive.config, base_revision=1, prepared=token
        )
        assert row.payload["outcome"] == "no_eligible_work"
        if unavailable:
            assert engine.state.work_states[work.id].status is WorkStatus.BLOCKED
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize("fault", ["manager", "event"])
def test_failed_work_phase_clears_transients_but_retains_failed_tick_guard(
    tmp_path, monkeypatch, fault
):
    from living_world.managers.event_manager import EventManager
    from living_world.simulation.simulation_engine import FailedTickError
    from living_world.work import ResourceWorkTarget, WorkCategory
    from living_world.work.interruption import WorkInterruptionRequest
    from living_world.work.manager import WorkManager

    _, lease, archive, live = archived(tmp_path, "work_blockage", format=2)
    try:
        engine = live.initialize()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        engine.work.create(
            category=WorkCategory.GATHER_WATER,
            target=ResourceWorkTarget("water", 2),
            public_label="Water effort",
            settlement_id=camp,
            objective_id="objective_founders_water",
            location_id=camp,
        )
        request = WorkInterruptionRequest(settlement_id=camp, execution_tick=1)
        engine.configure_work_interruption(request)
        before_work = dict(engine.state.work_states)
        if fault == "manager":
            monkeypatch.setattr(
                WorkManager,
                "block",
                lambda *args: (_ for _ in ()).throw(
                    RuntimeError("injected block failure")
                ),
            )
        else:
            original = EventManager.record

            def failed(self, *, kind, **kwargs):
                if kind == "work_order_blocked":
                    raise RuntimeError("injected blocked event failure")
                return original(self, kind=kind, **kwargs)

            monkeypatch.setattr(EventManager, "record", failed)
        with pytest.raises(RuntimeError):
            engine.step()
        assert engine.work_interruption_result is None
        assert engine.state.work_states == before_work
        engine.configure_work_interruption(None)
        assert engine.work_interruption_result is None
        with pytest.raises(FailedTickError):
            engine.step()
        with pytest.raises(FailedTickError):
            engine.configure_work_interruption(request)
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize(
    "fault",
    ["missing_token", "wrong_policy", "missing_result", "wrong_request", "bad_event"],
)
def test_format_two_rejects_inconsistent_preparation_result_or_events(tmp_path, fault):
    from living_world.runtime.disturbances import prepare_boundary_disturbance
    from living_world.work import ResourceWorkTarget, WorkCategory
    from living_world.work.interruption import WorkInterruptionRequest

    _, lease, archive, live = archived(tmp_path, "work_blockage", format=2)
    try:
        engine = live.initialize()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        engine.work.create(
            category=WorkCategory.GATHER_WATER,
            target=ResourceWorkTarget("water", 2),
            public_label="Water effort",
            settlement_id=camp,
            objective_id="objective_founders_water",
            location_id=camp,
        )
        token = prepare_boundary_disturbance(engine, archive.config)
        engine.step()
        result = engine.work_interruption_result
        if fault == "missing_token":
            token = None
        elif fault == "wrong_policy":
            token = replace(token, policy=BoundaryDisturbance(kind="work_blockage"))
        elif fault == "missing_result":
            engine.configure_work_interruption(None)
        elif fault == "wrong_request":
            token = replace(
                token,
                request=WorkInterruptionRequest(settlement_id=camp, execution_tick=0),
            )
        else:
            # Fault injection alters only the transient result; actual world remains intact.
            engine._work_execution_system._interruption_result = replace(
                result, event_references=("event_missing",)
            )
        with pytest.raises(ArchiveFormatError):
            apply_boundary_disturbance(
                engine, archive.config, base_revision=1, prepared=token
            )
    finally:
        archive.close()
        lease.release()


@pytest.mark.parametrize("terminal_before", [True, False])
def test_format_two_terminal_base_skips_but_applied_result_keeps_later_terminal_authority(
    tmp_path, terminal_before
):
    from living_world.goals.model import GoalStatus
    from living_world.runtime.disturbances import prepare_boundary_disturbance
    from living_world.work import ResourceWorkTarget, WorkCategory

    _, lease, archive, live = archived(tmp_path, "work_blockage", format=2)
    try:
        engine = live.initialize()
        engine.step()
        camp = engine.state.scenario_entity_bindings["camp"]
        if not terminal_before:
            engine.work.create(
                category=WorkCategory.GATHER_WATER,
                target=ResourceWorkTarget("water", 2),
                public_label="Water effort",
                settlement_id=camp,
                objective_id="objective_founders_water",
                location_id=camp,
            )
        if terminal_before:
            engine.state.goal_states["goal_founding"] = replace(
                engine.state.goal_states["goal_founding"], status=GoalStatus.FAILED
            )
        token = prepare_boundary_disturbance(engine, archive.config)
        engine.step()
        if not terminal_before:
            engine.state.goal_states["goal_founding"] = replace(
                engine.state.goal_states["goal_founding"], status=GoalStatus.FAILED
            )
        (row,) = apply_boundary_disturbance(
            engine, archive.config, base_revision=1, prepared=token
        )
        assert row.payload["outcome"] == ("terminal" if terminal_before else "applied")
        assert engine.state.goal_states["goal_founding"].status is GoalStatus.FAILED
    finally:
        archive.close()
        lease.release()
