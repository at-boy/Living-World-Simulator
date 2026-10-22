"""Live preparation never calls the provider from the simulation step."""

from pathlib import Path

from living_world.archives import (
    AttemptArchive,
    AttemptConfig,
    AttemptLease,
    Checkpoint,
    RunCatalog,
)
from living_world.runtime.broker import BrokerResult, DecisionBroker, ProviderConfig
from living_world.runtime.contracts import (
    ScenarioComposition,
    TickDriver,
    TickPreparation,
)
from living_world.runtime.feedback import DecisionInput
from living_world.runtime.founders import FoundersLiveComposition
from living_world.runtime.ollama_driver import (
    OllamaTickDriver,
    effective_config_fingerprint,
)
from living_world.state.world_state import WorldState


def test_effective_config_excludes_operational_settings() -> None:
    a = AttemptConfig("ollama", "founders", 1, "rev", {"provider": {"model": "local"}})
    b = AttemptConfig(
        "ollama",
        "founders",
        1,
        "rev",
        {
            "provider": {"model": "local", "seed": 1},
            "limits": {"max_requests": 2, "max_ticks": 4},
        },
    )
    assert effective_config_fingerprint(a) == effective_config_fingerprint(b)
    c = AttemptConfig(
        "ollama", "founders", 1, "rev", {"provider": {"model": "changed"}}
    )
    assert effective_config_fingerprint(a) != effective_config_fingerprint(c)


class ImmediateBroker(DecisionBroker):
    def __init__(self, *, failure: str | None = None) -> None:
        self.calls: list[DecisionInput] = []
        self.failure = failure
        self.current: tuple[str, DecisionInput] | None = None

    def start(
        self, job_id: str, config: ProviderConfig, decision_input: DecisionInput
    ) -> None:
        self.calls.append(decision_input)
        self.current = (job_id, decision_input)

    def poll(self, job_id: str) -> BrokerResult:
        from living_world.cognition.npc_cognition_client import NPCDecision
        from living_world.runtime.broker import BrokerResult

        assert self.current is not None
        if self.failure:
            return BrokerResult(job_id, None, self.failure, None, 0.0)
        return BrokerResult(job_id, NPCDecision("I will watch.", None), None, None, 0.0)

    def close(self) -> None:
        self.current = None


def live_archive(
    tmp_path: Path,
    *,
    maximum: int | None = 40,
    provider: dict[str, object] | None = None,
) -> tuple[RunCatalog, AttemptLease, AttemptArchive, FoundersLiveComposition]:
    from living_world.archives import AttemptLease, RunCatalog, retain_inputs
    from living_world.founders.assets import materialize_founders_assets
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        scenario = YAMLScenarioLoader().load(assets.scenario)
        config = AttemptConfig(
            "ollama",
            scenario.key,
            scenario.seed,
            "test",
            {
                "provider": provider or {"model": "local"},
                "limits": {} if maximum is None else {"max_requests": maximum},
            },
        )
        ref = catalog.reserve(config)
        inputs = retain_inputs(ref, assets.scenario, tape_path=None)
    lease = AttemptLease(ref)
    lease.acquire()
    archive = catalog.open_attempt(ref.attempt_id, read_only=False)
    return catalog, lease, archive, FoundersLiveComposition(inputs)


def initialized(
    archive: AttemptArchive, live: FoundersLiveComposition, broker: DecisionBroker
) -> tuple[OllamaTickDriver, Checkpoint]:
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.broker import client_for, encoded_body, provider_config
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.ollama_driver import OllamaTickDriver

    config = provider_config(archive.config)
    client = client_for(config)
    feedback = FoundersFeedback(
        lambda context, options: len(
            encoded_body(client.build_payload(context, options))
        )
    )
    driver = OllamaTickDriver(config, feedback, broker)
    candidate = live.initialize()
    commit = driver.initialize(candidate, archive)
    base = archive.commit(
        encode_world(candidate.state),
        expected_revision=None,
        driver_cursor=commit.driver_cursor,
        feedback_cursor=commit.feedback_cursor,
        entries=(),
    )
    return driver, base


def ready(preparation: TickPreparation) -> str:
    for _ in range(20):
        status = preparation.poll()
        if status != "waiting":
            return status
    raise AssertionError("Preparation did not settle")


def test_two_actor_speech_only_commits_and_reuses_validated_after_pause(
    tmp_path: Path,
) -> None:
    from living_world.repositories.world_snapshot import encode_world

    _catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        first = driver.prepare(live.restore(base.snapshot), base, archive)
        assert first.poll() == "waiting"
        assert first.poll() == "waiting"  # validates Ada, starts Bryn
        first.request_pause()
        assert first.poll() == "paused"
        first.close()
        assert len(broker.calls) == 2
        candidate = live.restore(base.snapshot)
        second = driver.prepare(candidate, base, archive)
        assert ready(second) == "ready"
        assert len(broker.calls) == 2
        second.install()
        candidate.step()
        commit = second.finish_tick()
        assert [e.payload["actor_label"] for e in commit.journal_entries] == [
            "ada",
            "bryn",
        ]
        assert all(e.payload["outcome"] == "no_action" for e in commit.journal_entries)
        assert len(broker.calls) == 2
        saved = archive.commit(
            encode_world(candidate.state),
            expected_revision=base.revision,
            driver_cursor=commit.driver_cursor,
            feedback_cursor=commit.feedback_cursor,
            entries=commit.journal_entries,
        )
        second.close()
        assert saved.driver_cursor["next_tick"] == 1
        assert sum(e.kind == "candidate_aborted" for e in archive.entries()) == 1
    finally:
        archive.close()
        lease.release()


def test_failure_retry_once_and_cold_restart_requires_explicit_retry(
    tmp_path: Path,
) -> None:
    _catalog, lease, archive, live = live_archive(tmp_path, maximum=2)
    try:
        broker = ImmediateBroker(failure="timeout")
        driver, base = initialized(archive, live, broker)
        first = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(first) == "provider_error"
        first.close()
        assert len(broker.calls) == 1
        from living_world.runtime.ollama_driver import OllamaTickDriver

        cold = OllamaTickDriver(driver.config, driver.feedback, broker)
        recovered = cold.prepare(live.restore(base.snapshot), base, archive)
        assert recovered.poll() == "provider_error"
        assert len(broker.calls) == 1
        recovered.close()
        retry = cold.prepare(live.restore(base.snapshot), base, archive)
        assert ready(retry) == "provider_error"
        assert len(broker.calls) == 2
        retry.close()
        budget = cold.prepare(live.restore(base.snapshot), base, archive)
        assert ready(budget) == "provider_error"
        assert budget.error_code == "request_budget_exhausted"
        assert len(broker.calls) == 2
        budget.close()
    finally:
        archive.close()
        lease.release()


class ActionBroker(ImmediateBroker):
    def poll(self, job_id: str) -> BrokerResult:
        from living_world.cognition.npc_cognition_client import (
            ActionRequest,
            NPCDecision,
        )
        from living_world.runtime.broker import BrokerResult

        assert self.current is not None
        item = self.current[1]
        if not item.options:
            return super().poll(job_id)
        option = item.options[0]
        decision = NPCDecision(
            None,
            ActionRequest(
                option.key,
                option.target_labels[0] if option.target_labels else None,
                "We need supplies.",
                {},
            ),
        )
        return BrokerResult(job_id, decision, None, None, 0.0)


def advance(
    driver: TickDriver,
    live: ScenarioComposition,
    archive: AttemptArchive,
    base: Checkpoint,
) -> Checkpoint:
    from living_world.repositories.world_snapshot import encode_world

    candidate = live.restore(base.snapshot)
    preparation = driver.prepare(candidate, base, archive)
    assert ready(preparation) == "ready"
    preparation.install()
    candidate.step()
    commit = preparation.finish_tick()
    checkpoint = archive.commit(
        encode_world(candidate.state),
        expected_revision=base.revision,
        driver_cursor=commit.driver_cursor,
        feedback_cursor=commit.feedback_cursor,
        entries=commit.journal_entries,
    )
    preparation.close()
    return checkpoint


def test_real_gateway_and_discarded_candidate_gc(tmp_path: Path) -> None:
    import gc
    import weakref

    from living_world.repositories.world_snapshot import decode_world

    _catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ActionBroker()
        driver, base = initialized(archive, live, broker)
        first_base = advance(driver, live, archive, base)
        next_base = advance(driver, live, archive, first_base)
        outcomes = [e for e in archive.entries() if e.kind == "action_resolved"]
        assert len(outcomes) == 4
        assert any(e.payload["outcome"] == "accepted" for e in outcomes)
        assert any(e.payload["event_references"] for e in outcomes)
        assert decode_world(next_base.snapshot).work_definitions
        candidate = live.restore(next_base.snapshot)
        ref = weakref.ref(candidate)
        preparation = driver.prepare(candidate, next_base, archive)
        preparation.close()
        del preparation, candidate
        gc.collect()
        assert ref() is None
    finally:
        archive.close()
        lease.release()


def test_sealed_fork_reuses_prefix_and_continues_multiple_ticks(tmp_path: Path) -> None:
    from living_world.archives import AttemptLease
    from living_world.runtime.ollama_driver import OllamaTickDriver

    catalog, lease, archive, live = live_archive(tmp_path)
    child_archive = None
    child_lease = None
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        preparation = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(preparation) == "ready"
        preparation.close()
        child_ref = catalog.fork(archive.ref.attempt_id, 0)
        child_lease = AttemptLease(child_ref)
        child_lease.acquire()
        child_archive = catalog.open_attempt(child_ref.attempt_id, read_only=False)
        child_driver = OllamaTickDriver(driver.config, driver.feedback, broker)
        first = advance(child_driver, live, child_archive, child_archive.checkpoint())
        assert len(broker.calls) == 2
        assert sum(e.kind == "response_reused" for e in child_archive.entries()) == 2
        second = advance(child_driver, live, child_archive, first)
        assert second.driver_cursor["next_tick"] == 2
        assert len(broker.calls) == 4
    finally:
        if child_archive is not None:
            child_archive.close()
        if child_lease is not None:
            child_lease.release()
        archive.close()
        lease.release()


def test_pending_restart_is_uncertain_without_resend_then_retry_reuses_earlier_actor(
    tmp_path: Path,
) -> None:
    from living_world.runtime.ollama_driver import OllamaTickDriver

    _catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        pending = driver.prepare(live.restore(base.snapshot), base, archive)
        assert pending.poll() == "waiting"
        assert pending.poll() == "waiting"  # first validated; second pending at crash
        # Simulate process loss: no preparation.close(), preserving the pending row.
        broker.close()
        cold = OllamaTickDriver(driver.config, driver.feedback, broker)
        recovered = cold.prepare(live.restore(base.snapshot), base, archive)
        assert ready(recovered) == "provider_error"
        assert recovered.error_code == "uncertain"
        assert len(broker.calls) == 2
        recovered.close()
        advance(cold, live, archive, base)
        assert len(broker.calls) == 3
        assert (
            sum(
                e.kind == "response_failed" and e.payload["code"] == "uncertain"
                for e in archive.entries()
            )
            == 1
        )
    finally:
        archive.close()
        lease.release()


def test_complete_body_required_identity_fails_before_any_call(tmp_path: Path) -> None:
    import pytest

    from living_world.archives import (
        AttemptConfig,
        AttemptLease,
        RunCatalog,
        retain_inputs,
    )
    from living_world.founders.assets import materialize_founders_assets
    from living_world.runtime.founders import FoundersLiveComposition
    from living_world.scenarios.scenario import YAMLScenarioLoader

    catalog = RunCatalog(tmp_path)
    with materialize_founders_assets() as assets:
        scenario = YAMLScenarioLoader().load(assets.scenario)
        config = AttemptConfig(
            "ollama",
            scenario.key,
            scenario.seed,
            "test",
            {"provider": {"model": "\\" * 18000}},
        )
        ref = catalog.reserve(config)
        inputs = retain_inputs(ref, assets.scenario, tape_path=None)
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        live = FoundersLiveComposition(inputs)
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        with pytest.raises(ValueError, match="context_budget_exceeded"):
            driver.prepare(live.restore(base.snapshot), base, archive)
        assert broker.calls == []
        assert not archive.entries()


def test_domain_phase_invalidates_actor_and_gateway_rejects(tmp_path: Path) -> None:
    _catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ActionBroker()
        driver, base = initialized(archive, live, broker)
        first = advance(driver, live, archive, base)
        candidate = live.restore(first.snapshot)
        preparation = driver.prepare(candidate, first, archive)
        assert ready(preparation) == "ready"

        class Destroy:
            def step(self, state: WorldState) -> None:
                actor = candidate.state.scenario_entity_bindings["ada"]
                candidate.entities.mark_destroyed(actor, candidate.state.tick)

        candidate.register_system(Destroy(), key="destroy_ada")
        preparation.install()
        candidate.step()
        result = preparation.finish_tick()
        assert result.journal_entries[0].payload["actor_label"] == "ada"
        assert result.journal_entries[0].payload["outcome"] == "rejected"
        preparation.close()
    finally:
        archive.close()
        lease.release()


def test_parent_postfork_response_is_excluded_and_recursive_reuse_is_safe(
    tmp_path: Path,
) -> None:
    from living_world.archives import AttemptLease
    from living_world.runtime.ollama_driver import OllamaTickDriver

    catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        first = driver.prepare(live.restore(base.snapshot), base, archive)
        first.poll()  # source pending Ada at seal
        child_ref = catalog.fork(archive.ref.attempt_id, 0)
        assert ready(first) == "ready"  # response appended after seal
        first.close()
        with (
            AttemptLease(child_ref),
            catalog.open_attempt(child_ref.attempt_id, read_only=False) as child,
        ):
            cold = OllamaTickDriver(driver.config, driver.feedback, broker)
            error = cold.prepare(live.restore(base.snapshot), child.checkpoint(), child)
            assert ready(error) == "provider_error"
            assert error.error_code == "uncertain"
            assert len(broker.calls) == 2
            error.close()
            ready_child = cold.prepare(
                live.restore(base.snapshot), child.checkpoint(), child
            )
            assert ready(ready_child) == "ready"
            ready_child.close()
            assert len(broker.calls) == 4
            grandchild_ref = catalog.fork(child_ref.attempt_id, 0)
        with (
            AttemptLease(grandchild_ref),
            catalog.open_attempt(
                grandchild_ref.attempt_id, read_only=False
            ) as grandchild,
        ):
            grand_driver = OllamaTickDriver(driver.config, driver.feedback, broker)
            advance(grand_driver, live, grandchild, grandchild.checkpoint())
            assert len(broker.calls) == 4
            assert sum(e.kind == "response_reused" for e in grandchild.entries()) == 2
    finally:
        archive.close()
        lease.release()


def test_unsafe_prose_never_reaches_journal(tmp_path: Path) -> None:
    from living_world.cognition.npc_cognition_client import NPCDecision
    from living_world.runtime.broker import BrokerResult

    class UnsafeBroker(ImmediateBroker):
        def poll(self, job_id: str) -> BrokerResult:
            return BrokerResult(
                job_id, NPCDecision("next_index is hidden", None), None, None, 0.0
            )

    _catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = UnsafeBroker()
        driver, base = initialized(archive, live, broker)
        preparation = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(preparation) == "provider_error"
        assert preparation.error_code == "unsafe_response"
        preparation.close()
        assert "next_index is hidden" not in str(archive.entries())
        assert not any(e.kind == "response_validated" for e in archive.entries())
    finally:
        archive.close()
        lease.release()


def test_seal_tamper_fails_before_http(tmp_path: Path) -> None:
    import sqlite3

    import pytest

    from living_world.archives import ArchiveFormatError, AttemptLease
    from living_world.runtime.ollama_driver import OllamaTickDriver

    catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        preparation = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(preparation) == "ready"
        preparation.close()
        ref = catalog.fork(archive.ref.attempt_id, 0)
        with sqlite3.connect(archive.database_path) as db:
            db.execute(
                "UPDATE journal SET payload=replace(payload, 'I will watch.', 'I will sleep.') WHERE kind='response_validated'"
            )
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as child,
        ):
            cold = OllamaTickDriver(driver.config, driver.feedback, broker)
            with pytest.raises(ArchiveFormatError, match="seal mismatch"):
                cold.prepare(live.restore(base.snapshot), child.checkpoint(), child)
        assert len(broker.calls) == 2
    finally:
        archive.close()
        lease.release()


def test_changed_config_fork_does_not_reuse_prior_responses(tmp_path: Path) -> None:
    from living_world.archives import AttemptLease
    from living_world.runtime.broker import client_for, encoded_body, provider_config
    from living_world.runtime.feedback import FoundersFeedback
    from living_world.runtime.ollama_driver import OllamaTickDriver

    catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        driver, base = initialized(archive, live, broker)
        preparation = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(preparation) == "ready"
        preparation.close()
        changed = AttemptConfig(
            "ollama",
            archive.config.scenario_key,
            archive.config.seed,
            "test",
            {"provider": {"model": "changed"}},
        )
        ref = catalog.fork(archive.ref.attempt_id, 0, config=changed)
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as child,
        ):
            config = provider_config(child.config)
            client = client_for(config)
            feedback = FoundersFeedback(
                lambda context, options: len(
                    encoded_body(client.build_payload(context, options))
                )
            )
            cold = OllamaTickDriver(config, feedback, broker)
            result = advance(cold, live, child, child.checkpoint())
            assert result.driver_cursor[
                "config_fingerprint"
            ] == effective_config_fingerprint(changed)
            assert sum(e.kind == "response_reused" for e in child.entries()) == 0
        assert len(broker.calls) == 4
    finally:
        archive.close()
        lease.release()


def test_real_driver_spawn_loopback_smoke(tmp_path: Path) -> None:
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.broker import DecisionBroker

    class Handler(BaseHTTPRequestHandler):
        requests = 0

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            Handler.requests += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b'{"response":"{\\"spoken_text\\":\\"I will watch.\\",\\"action_request\\":null}"}'
            )

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _catalog, lease, archive, live = live_archive(
            tmp_path,
            provider={
                "model": "local",
                "base_url": f"http://127.0.0.1:{server.server_port}",
                "timeout_seconds": 5,
            },
        )
        broker = DecisionBroker()
        try:
            driver, base = initialized(archive, live, broker)
            candidate = live.restore(base.snapshot)
            preparation = driver.prepare(candidate, base, archive)
            deadline = time.monotonic() + 12
            status = "waiting"
            while status == "waiting" and time.monotonic() < deadline:
                status = preparation.poll()
                time.sleep(0.01)
            assert status == "ready"
            assert Handler.requests == 2
            preparation.install()
            candidate.step()
            commit = preparation.finish_tick()
            archive.commit(
                encode_world(candidate.state),
                expected_revision=base.revision,
                driver_cursor=commit.driver_cursor,
                feedback_cursor=commit.feedback_cursor,
                entries=commit.journal_entries,
            )
            preparation.close()
            assert Handler.requests == 2
        finally:
            broker.close()
            archive.close()
            lease.release()
            server.shutdown()
            thread.join(timeout=2)


def _crash_at_boundary(root: str, attempt_id: str, phase: str) -> None:
    """Subprocess entry: actual archive/lease, fake inference, abrupt OS exit."""
    import os

    from living_world.archives import load_retained_inputs
    from living_world.runtime.broker import client_for, encoded_body, provider_config
    from living_world.runtime.feedback import FoundersFeedback

    catalog = RunCatalog(Path(root))
    ref = next(s.ref for s in catalog.attempts() if s.ref.attempt_id == attempt_id)
    with (
        AttemptLease(ref),
        catalog.open_attempt(attempt_id, read_only=False) as archive,
    ):
        live = FoundersLiveComposition(load_retained_inputs(ref))
        config = provider_config(archive.config)
        client = client_for(config)
        feedback = FoundersFeedback(
            lambda context, options, client=client: len(
                encoded_body(client.build_payload(context, options))
            )
        )
        driver = OllamaTickDriver(config, feedback, ActionBroker())
        base = archive.checkpoint()
        candidate = live.restore(base.snapshot)
        preparation = driver.prepare(candidate, base, archive)
        if phase == "before_response":
            preparation.poll()
        else:
            assert ready(preparation) == "ready"
            if phase == "after_commit":
                from living_world.repositories.world_snapshot import encode_world

                preparation.install()
                candidate.step()
                commit = preparation.finish_tick()
                archive.commit(
                    encode_world(candidate.state),
                    expected_revision=base.revision,
                    driver_cursor=commit.driver_cursor,
                    feedback_cursor=commit.feedback_cursor,
                    entries=commit.journal_entries,
                )
        os._exit(73)


def test_subprocess_crash_boundaries_preserve_exact_recovery(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    import pytest

    from living_world.archives import ArchiveFormatError
    from living_world.runtime.broker import client_for, encoded_body
    from living_world.runtime.feedback import FoundersFeedback

    for phase in ("before_response", "after_response", "after_commit"):
        root = tmp_path / phase
        catalog, lease, archive, live = live_archive(root)
        broker = ActionBroker()
        driver, initial = initialized(archive, live, broker)
        base = advance(driver, live, archive, initial)  # tick one has real work offers
        archive.close()
        lease.release()
        code = "from test_runtime_ollama_driver import _crash_at_boundary; _crash_at_boundary(*__import__('sys').argv[1:])"
        result = subprocess.run(
            [sys.executable, "-c", code, str(root), archive.ref.attempt_id, phase],
            env={**os.environ, "PYTHONPATH": "src:tests"},
            timeout=15,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 73, result.stderr.decode()
        with (
            AttemptLease(archive.ref),
            catalog.open_attempt(archive.ref.attempt_id, read_only=False) as recovered,
        ):
            fresh_broker = ActionBroker()
            client = client_for(driver.config)
            feedback = FoundersFeedback(
                lambda context, options, client=client: len(
                    encoded_body(client.build_payload(context, options))
                )
            )
            cold = OllamaTickDriver(driver.config, feedback, fresh_broker)
            durable = recovered.checkpoint()
            if phase == "after_commit":
                assert durable.revision == base.revision + 1
                before = durable.snapshot
                with pytest.raises(ArchiveFormatError, match="Stale"):
                    cold.prepare(live.restore(base.snapshot), base, recovered)
                assert recovered.checkpoint().snapshot == before
                assert len(fresh_broker.calls) == 0
                rows = [
                    r
                    for r in recovered.journal_records()
                    if r.entry.kind == "action_resolved"
                    and r.checkpoint_revision == durable.revision
                ]
                assert len(rows) == 2
                continue
            assert durable == base
            preparation = cold.prepare(live.restore(base.snapshot), base, recovered)
            status = ready(preparation)
            if phase == "before_response":
                assert (
                    status == "provider_error" and preparation.error_code == "uncertain"
                )
                assert fresh_broker.calls == []
                preparation.close()
                advance(cold, live, recovered, base)
                assert len(fresh_broker.calls) == 2
            else:
                assert status == "ready"
                assert fresh_broker.calls == []
                preparation.close()
                advance(cold, live, recovered, base)
                assert fresh_broker.calls == []


def test_complete_body_escaping_prunes_optional_memory_and_zero_actor_commit(
    tmp_path: Path,
) -> None:
    from living_world.core.memory import CognitiveSalience
    from living_world.repositories.world_snapshot import encode_world
    from living_world.runtime.broker import client_for, encoded_body

    _catalog, lease, archive, live = live_archive(tmp_path)
    try:
        broker = ImmediateBroker()
        # Build initial feedback once, then add optional safe but expensive memory.
        from living_world.runtime.broker import provider_config
        from living_world.runtime.feedback import FoundersFeedback

        config = provider_config(archive.config)
        client = client_for(config)
        feedback = FoundersFeedback(
            lambda context, options, client=client: len(
                encoded_body(client.build_payload(context, options))
            )
        )
        driver = OllamaTickDriver(config, feedback, broker)
        candidate = live.initialize()
        commit = driver.initialize(candidate, archive)
        ada = candidate.state.scenario_entity_bindings["ada"]
        expensive = "\\" * 7000
        candidate.memories.record(
            holder_id=ada,
            subject_id=ada,
            summary=expensive,
            salience=CognitiveSalience(0.9, False),
        )
        base = archive.commit(
            encode_world(candidate.state),
            expected_revision=None,
            driver_cursor=commit.driver_cursor,
            feedback_cursor=commit.feedback_cursor,
            entries=(),
        )
        preparation = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(preparation) == "ready"
        for item in broker.calls:
            assert (
                len(encoded_body(client.build_payload(item.context, item.options)))
                <= 16000
            )
            assert all(
                memory.text != expensive
                for memory in item.context.retrieved_information
            )
            assert item.context.core_cognition  # mandate retained
        preparation.close()
    finally:
        archive.close()
        lease.release()

    _catalog, lease, archive, live = live_archive(tmp_path / "empty")
    try:
        from living_world.runtime.broker import provider_config
        from living_world.runtime.feedback import FoundersFeedback

        config = provider_config(archive.config)
        feedback = FoundersFeedback(lambda _context, _options: 100)
        driver = OllamaTickDriver(config, feedback, ImmediateBroker())
        candidate = live.initialize()
        for label in ("ada", "bryn"):
            candidate.entities.mark_destroyed(
                candidate.state.scenario_entity_bindings[label], 0
            )
        commit = driver.initialize(candidate, archive)
        base = archive.commit(
            encode_world(candidate.state),
            expected_revision=None,
            driver_cursor=commit.driver_cursor,
            feedback_cursor=commit.feedback_cursor,
            entries=(),
        )
        advance(driver, live, archive, base)
        assert not any(e.kind == "candidate_aborted" for e in archive.entries())
        discarded = driver.prepare(
            live.restore(archive.checkpoint().snapshot), archive.checkpoint(), archive
        )
        discarded.close()
        assert sum(e.kind == "candidate_aborted" for e in archive.entries()) == 1
    finally:
        archive.close()
        lease.release()


def test_default_forty_request_budget_counts_durable_failures(tmp_path: Path) -> None:
    from living_world.archives import JournalEntry

    _catalog, lease, archive, live = live_archive(tmp_path, maximum=None)
    try:
        broker = ImmediateBroker(failure="timeout")
        driver, base = initialized(archive, live, broker)
        seed = driver.prepare(live.restore(base.snapshot), base, archive)
        request = seed._request(seed.items[0])
        entries = []
        for index in range(39):
            request_id = f"prior-{index}"
            entries.extend(
                (
                    JournalEntry(
                        "request_started", {**request, "request_id": request_id}
                    ),
                    JournalEntry(
                        "response_failed", {"request_id": request_id, "code": "timeout"}
                    ),
                )
            )
        archive.record(tuple(entries))
        assert ready(seed) == "provider_error"  # cold-start failure requires Retry
        seed.close()
        retry = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(retry) == "provider_error"
        retry.close()
        assert len(broker.calls) == 1
        assert sum(e.kind == "request_started" for e in archive.entries()) == 40
        exhausted = driver.prepare(live.restore(base.snapshot), base, archive)
        assert ready(exhausted) == "provider_error"
        assert exhausted.error_code == "request_budget_exhausted"
        exhausted.close()
        assert len(broker.calls) == 1
    finally:
        archive.close()
        lease.release()
