"""Authenticated local operator boundaries exercised through ASGI and real runtime."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def test_session_secrets_and_origins() -> None:
    from living_world.api.auth import AdminSession

    session = AdminSession.issue(origin="HTTP://LOCALHOST:80")
    assert session.origin == "http://localhost"
    assert session.token != session.csrf_nonce
    assert session.token not in repr(session) and session.csrf_nonce not in repr(
        session
    )
    assert AdminSession.issue(origin="https://[::1]:443").origin == "https://[::1]"
    for origin in (
        "http://example.org",
        "http://localhost/",
        "http://localhost:",
        "http://[::1]extra",
        "http://[::1]extra:8000",
        "http://localhost?",
        "http://localhost#",
        "http://u@localhost",
        "http://localhost:0",
        "http://localhost\n",
    ):
        with pytest.raises(ValueError):
            AdminSession.issue(origin=origin)


@pytest.mark.parametrize("mutation", [False, True])
def test_session_header_security(mutation: bool) -> None:
    from living_world.api.auth import AdminSession

    session = AdminSession.issue()

    def request(headers):
        return Request(
            {
                "type": "http",
                "headers": [
                    (k.encode(), v.encode("latin1")) for k, v in headers.items()
                ],
            }
        )

    valid = {
        "authorization": f"Bearer {session.token}",
        "origin": session.origin,
        "x-csrf-token": session.csrf_nonce,
    }
    session.authorize(request(valid), mutation=mutation)
    for key, value, code in (
        ("authorization", "Bearer é", 401),
        ("authorization", "", 401),
        ("origin", "http://localhost", 403),
        ("origin", "é", 403),
    ):
        with pytest.raises(HTTPException) as failure:
            session.authorize(request({**valid, key: value}), mutation=mutation)
        assert failure.value.status_code == code
        assert failure.value.detail == ("unauthorized" if code == 401 else "forbidden")
    session.authorize(request({"authorization": valid["authorization"]}))
    for headers in (
        {"authorization": valid["authorization"]},
        {**valid, "x-csrf-token": "é"},
    ):
        with pytest.raises(HTTPException) as failure:
            session.authorize(request(headers), mutation=True)
        assert failure.value.status_code == 403


def operator(tmp_path):
    from test_inspection_api import ASGIClient
    from test_runtime_service import reserved

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.runtime import RuntimeService

    catalog, config, ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    controller = service.start(config, inputs, paused=True)
    session = AdminSession.issue()
    app = create_operator_app(service, controller, auth=session)
    return ASGIClient(app), service, controller, ref, session


def headers(session):
    return {
        "Authorization": f"Bearer {session.token}",
        "Origin": session.origin,
        "X-CSRF-Token": session.csrf_nonce,
    }


def test_operator_auth_status_and_command_admission(tmp_path: Path) -> None:
    import json

    from test_runtime_service import wait_for

    from living_world.runtime import RuntimeState

    client, service, controller, ref, session = operator(tmp_path)
    try:
        for path in (
            "/runtime/status",
            "/archives",
            f"/archives/{ref.attempt_id}",
            "/live/checkpoints/0/world",
        ):
            response = client.get(path)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
            assert "x-csrf-token" not in response.headers
        response = client.request("GET", "/runtime/status", headers=headers(session))
        live = response.json()["live"]
        assert live["tick"] == 0 and live["inspection_prefix"] == "/live/checkpoints/0"
        assert live["mode"] == "recorded" and live["scenario"] == "generic"
        assert response.headers["x-csrf-token"] == session.csrf_nonce
        assert not any("access-control" in key for key in response.headers)
        command = {
            "command_id": "step-one",
            "action": "step",
            "expected_state_version": live["state_version"],
        }

        def post(value, route="/runtime/commands", auth=None):
            return client.request(
                "POST",
                route,
                headers=auth or headers(session),
                body=json.dumps(value).encode(),
            )

        assert (
            post(
                command,
                "/runtime/commands?mutation=false",
                {"Authorization": headers(session)["Authorization"]},
            ).status_code
            == 403
        )
        assert post({**command, "extra": True}).json() == {"detail": "invalid_command"}
        assert post({**command, "expected_state_version": True}).status_code == 422
        receipt = post(command)
        assert receipt.status_code == 202 and receipt.json()["status"] == "queued"
        wait_for(controller, lambda s: s.tick == 1 and s.state is RuntimeState.PAUSED)
        assert post(command).json()["status"] == "applied"
        assert post({**command, "action": "stop"}).json() == {
            "detail": "command_conflict"
        }
        assert post({**command, "command_id": "stale"}).status_code == 409
        assert (
            client.request(
                "GET", "/runtime/commands/step-one", headers=headers(session)
            ).json()["status"]
            == "applied"
        )
        assert (
            client.request(
                "GET", "/runtime/commands/unknown", headers=headers(session)
            ).status_code
            == 404
        )
        assert (
            client.request(
                "PUT",
                "/runtime/commands",
                headers=headers(session),
                body=json.dumps(command).encode(),
            ).status_code
            == 405
        )
        all_bytes = b"".join(
            p.read_bytes() for p in ref.directory.rglob("*") if p.is_file()
        )
        assert (
            session.token.encode() not in all_bytes
            and session.csrf_nonce.encode() not in all_bytes
        )
    finally:
        service.shutdown()


def test_archives_pinned_world_and_no_live(tmp_path: Path) -> None:
    from test_inspection_api import ASGIClient

    from living_world.api.operator import create_operator_app
    from living_world.runtime import RuntimeService

    client, service, controller, ref, session = operator(tmp_path)
    service.shutdown()
    archive_service = RuntimeService(service.catalog)
    client = ASGIClient(create_operator_app(archive_service, None, auth=session))

    def get(path):
        return client.request("GET", path, headers=headers(session))

    before = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in ref.directory.rglob("*")
        if p.is_file()
    }
    assert get("/runtime/status").json() == {"live": None}
    listing = get("/archives").json()["attempts"]
    assert listing[0]["attempt_id"] == ref.attempt_id and "directory" not in str(
        listing
    )
    detail = get(f"/archives/{ref.attempt_id}").json()
    assert detail["configuration_source"] == "archive" and detail["outcome"] is None
    assert detail["attempt"]["lifecycle"] == "stopped"
    assert detail["journal_total"] == len(detail["recent_journal"])
    assert get(f"/archives/{ref.attempt_id}/checkpoints").json() == {
        "checkpoints": [{"revision": 0, "tick": 0}, {"revision": 1, "tick": 0}]
    }
    prefix = f"/archives/{ref.attempt_id}/checkpoints/0"
    assert get(prefix + "/world/tick").json() == {"tick": 0}
    assert get(prefix + "/world").status_code == 200
    assert get(prefix + "/world/entities").status_code == 200
    for bad in ("-1", "1.0", "x"):
        assert (
            get(f"/archives/{ref.attempt_id}/checkpoints/{bad}/world").status_code
            == 404
        )
    assert get("/archives/bad").status_code == 404
    assert get("/live/checkpoints/0/world").status_code == 404
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}
    with pytest.raises(ValueError):
        create_operator_app(archive_service, controller, auth=session)


def test_no_world_setups_failed_initialization_and_corruption(
    tmp_path: Path, monkeypatch
) -> None:
    from test_inspection_api import ASGIClient

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.archives import AttemptConfig, AttemptLease, RunCatalog
    from living_world.archives import catalog as module
    from living_world.archives.catalog import ArchiveReservationError
    from living_world.runtime import RuntimeService

    catalog = RunCatalog(tmp_path / "runs")
    config = AttemptConfig(
        "ollama", "generic", 7, "test", {"provider": {"model": "tiny"}}
    )
    pending = catalog.reserve_setup(config)
    failed = catalog.reserve_setup(config)
    with AttemptLease(failed):
        catalog.fail_setup(failed, "model_missing")

    def broken(*args, **kwargs):
        raise OSError("PRIVATE")

    with monkeypatch.context() as patch:
        patch.setattr(module.AttemptArchive, "create", broken)
        with pytest.raises(ArchiveReservationError) as failure:
            catalog.reserve(AttemptConfig("recorded", "generic", 7, "test", {}))
    uninitialized = failure.value.ref
    corrupt = catalog.reserve(AttemptConfig("recorded", "generic", 7, "test", {}))
    (corrupt.directory / "archive.sqlite3").write_bytes(b"PRIVATE")
    session = AdminSession.issue()
    client = ASGIClient(
        create_operator_app(RuntimeService(catalog), None, auth=session)
    )
    for ref, label in (
        (pending, "requested"),
        (failed, "requested"),
        (uninitialized, "reservation"),
    ):
        response = client.request(
            "GET", f"/archives/{ref.attempt_id}", headers=headers(session)
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["configuration_source"] == label
        assert detail["journal_total"] == 0 and detail["recent_journal"] == []
        assert client.request(
            "GET", f"/archives/{ref.attempt_id}/checkpoints", headers=headers(session)
        ).json() == {"checkpoints": []}
    assert (
        len(
            client.request("GET", "/archives", headers=headers(session)).json()[
                "attempts"
            ]
        )
        == 4
    )
    assert client.request(
        "GET", f"/archives/{corrupt.attempt_id}", headers=headers(session)
    ).json() == {"detail": "archive_invalid"}


def test_auth_precedes_data_access_and_metadata_failure_cached(
    tmp_path: Path, monkeypatch
) -> None:
    from living_world.api import revision_source

    client, service, _controller, ref, session = operator(tmp_path)
    calls = []

    def broken(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("PRIVATE")

    monkeypatch.setattr(service.catalog, "attempts", broken)
    monkeypatch.setattr(revision_source.RevisionSource, "open", broken)
    try:
        for path in (
            "/archives",
            f"/archives/{ref.attempt_id}",
            "/live/checkpoints/0/world",
        ):
            assert client.get(path).status_code == 401
        assert (
            client.request("POST", "/runtime/commands", body=b"not json").status_code
            == 401
        )
        assert calls == []
        for _ in range(2):
            live = client.request(
                "GET", "/runtime/status", headers=headers(session)
            ).json()["live"]
            assert (
                live["tick"] == 0 and live["configuration_error"] == "archive_invalid"
            )
        assert len(calls) == 1
    finally:
        service.shutdown()


def test_bounded_journal_and_pinned_cache_eviction(tmp_path: Path) -> None:
    from test_inspection_api import ASGIClient
    from test_runtime_revision_source import archive_world, inventory

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.archives import AttemptLease, JournalEntry
    from living_world.runtime import RuntimeService

    catalog, ref, _ = archive_world(tmp_path, revisions=10)
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        archive.record(
            tuple(
                JournalEntry(
                    "candidate_aborted", {"base_revision": 9, "reason": "test"}
                )
                for _ in range(55)
            )
        )
    before = inventory(catalog.root)
    session = AdminSession.issue()
    client = ASGIClient(
        create_operator_app(RuntimeService(catalog), None, auth=session)
    )

    def get(path):
        return client.request("GET", path, headers=headers(session))

    detail = get(f"/archives/{ref.attempt_id}").json()
    assert detail["journal_total"] == 55 and len(detail["recent_journal"]) == 50
    for revision in (*range(10), 0):
        prefix = f"/archives/{ref.attempt_id}/checkpoints/{revision}"
        assert get(prefix + "/world/tick").json() == {"tick": revision}
        assert get(prefix + "/world/entities").status_code == 200
    assert get(f"/archives/{ref.attempt_id}/checkpoints/99/world").status_code == 404
    prefix = f"/archives/{ref.attempt_id}/checkpoints/0"
    for suffix in (
        "replay",
        "run",
        "entities",
        "definitions",
        "resources",
        "relationships",
        "placements",
        "external-references",
        "external-dispatches",
        "goals",
        "settlement-stages",
        "needs",
        "consequences",
        "work-orders",
        "events",
        "npcs",
        "observations",
        "memories",
        "knowledge",
        "beliefs",
        "experiences",
    ):
        assert get(prefix + "/world/" + suffix).status_code == 200
    assert before == inventory(catalog.root)


def test_delayed_provider_status_pause_retry_stop_and_owner(
    tmp_path: Path, monkeypatch
) -> None:
    import json
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from test_inspection_api import ASGIClient
    from test_runtime_ollama_driver import ImmediateBroker
    from test_runtime_preflight import tags_server
    from test_runtime_service import live_reserved, wait_for

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.runtime import RuntimeService, RuntimeState, launch

    release = threading.Event()
    owners = []

    class Delayed(ImmediateBroker):
        def poll(self, job_id):
            owners.append(threading.get_ident())
            return super().poll(job_id) if release.is_set() else None

    broker = Delayed(failure="timeout")
    monkeypatch.setattr(launch, "DecisionBroker", lambda: broker)
    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as base:
        catalog, config, ref, inputs = live_reserved(tmp_path, base)
        service = RuntimeService(catalog)
        controller = service.start(config, inputs, paused=True)
        session = AdminSession.issue()
        client = ASGIClient(create_operator_app(service, controller, auth=session))

        def send(identity, action, version=None):
            command = {
                "command_id": identity,
                "action": action,
                "expected_state_version": (
                    controller.status().state_version if version is None else version
                ),
            }
            return client.request(
                "POST",
                "/runtime/commands",
                headers=headers(session),
                body=json.dumps(command).encode(),
            )

        try:
            version = controller.status().state_version
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(
                    pool.map(lambda _: send("same", "step", version), range(2))
                )
            assert all(result.status_code == 202 for result in results)
            wait_for(controller, lambda s: s.state is RuntimeState.AWAITING_MODEL)
            start = time.monotonic()
            live = client.request(
                "GET", "/runtime/status", headers=headers(session)
            ).json()["live"]
            assert time.monotonic() - start < 0.5
            assert (
                live["tick"] == live["revision"] == 0 and live["activity"] is not None
            )
            assert live["model"] == {"name": "tiny:latest", "digest": "a" * 64}
            release.set()
            wait_for(
                controller, lambda s: s.state is RuntimeState.PROVIDER_ERROR_PAUSED
            )
            assert (
                send("resume", "resume").json()["reason"] == "provider_retry_required"
            )
            broker.failure = None
            assert send("retry", "retry").status_code == 202
            wait_for(controller, lambda s: s.tick == 1)
            assert (
                set(owners) == {controller._owner}
                and controller._owner != threading.get_ident()
            )
            assert send("stop", "stop").status_code == 202
            wait_for(controller, lambda s: s.state is RuntimeState.STOPPED)
            assert send("late", "step").status_code == 409
            with catalog.open_attempt(ref.attempt_id) as archive:
                assert archive.command("same").status == "applied"
                assert archive.command("stop").status == "applied"
        finally:
            release.set()
            service.shutdown()


def test_real_uvicorn_loopback_auth_control_and_lifespan(
    tmp_path: Path, caplog
) -> None:
    import json
    import socket
    import threading
    import time
    import urllib.error
    import urllib.request

    import uvicorn

    from living_world.api.operator import create_operator_app

    _client, service, controller, _ref, session = operator(tmp_path)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        from living_world.api.auth import AdminSession

        session = AdminSession.issue(origin=base)
        app = create_operator_app(service, controller, auth=session)
        server = uvicorn.Server(
            uvicorn.Config(app, log_level="error", access_log=False)
        )
        thread = threading.Thread(
            target=lambda: server.run(sockets=[sock]), daemon=True
        )
        thread.start()
        try:
            deadline = time.monotonic() + 3
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with pytest.raises(urllib.error.HTTPError) as failure:
                urllib.request.urlopen(base + "/runtime/status", timeout=2)
            assert failure.value.code == 401
            request = urllib.request.Request(
                base + "/runtime/status", headers=headers(session)
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                live = json.load(response)["live"]
                assert response.headers["X-CSRF-Token"] == session.csrf_nonce
            request = urllib.request.Request(
                base + "/runtime/commands",
                headers=headers(session),
                data=json.dumps(
                    {
                        "command_id": "network-step",
                        "action": "step",
                        "expected_state_version": live["state_version"],
                    }
                ).encode(),
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                assert response.status == 202
            assert service._thread.is_alive()
        finally:
            server.should_exit = True
            thread.join(6)
        assert not thread.is_alive() and not service._thread.is_alive()
        assert service.controller is controller
    assert session.token not in caplog.text and session.csrf_nonce not in caplog.text


def test_pause_ack_waits_for_durable_receipt(tmp_path: Path, monkeypatch) -> None:
    import json
    import threading

    from test_inspection_api import ASGIClient
    from test_runtime_ollama_driver import ImmediateBroker
    from test_runtime_preflight import tags_server
    from test_runtime_service import live_reserved, wait_for

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.runtime import RuntimeService, RuntimeState, launch

    release = threading.Event()

    class Delayed(ImmediateBroker):
        def poll(self, job_id):
            return super().poll(job_id) if release.is_set() else None

    monkeypatch.setattr(launch, "DecisionBroker", Delayed)
    with tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]}) as base:
        catalog, config, ref, inputs = live_reserved(tmp_path, base)
        service = RuntimeService(catalog)
        controller = service.start(config, inputs, paused=False)
        session = AdminSession.issue()
        client = ASGIClient(create_operator_app(service, controller, auth=session))
        try:
            wait_for(controller, lambda s: s.state is RuntimeState.AWAITING_MODEL)
            response = client.request(
                "POST",
                "/runtime/commands",
                headers=headers(session),
                body=json.dumps(
                    {
                        "command_id": "pause",
                        "action": "pause",
                        "expected_state_version": controller.status().state_version,
                    }
                ).encode(),
            )
            assert response.status_code == 202 and response.json()["status"] == "queued"
            wait_for(controller, lambda s: s.state is RuntimeState.PAUSE_REQUESTED)
            receipt = client.request(
                "GET", "/runtime/commands/pause", headers=headers(session)
            ).json()
            assert receipt["status"] == "queued"
            release.set()
            wait_for(controller, lambda s: s.state is RuntimeState.PAUSED)
            receipt = client.request(
                "GET", "/runtime/commands/pause", headers=headers(session)
            ).json()
            assert receipt["status"] == "applied" and controller.status().tick == 0
            with catalog.open_attempt(ref.attempt_id) as archive:
                assert archive.command("pause").revision == receipt["revision"]
        finally:
            release.set()
            service.shutdown()


@pytest.mark.parametrize(
    "lifecycle,outcome",
    [
        ("completed", "tick_limit"),
        ("failed", "service_failed"),
        ("stopped", None),
        ("interrupted", None),
    ],
)
def test_archive_lifecycle_and_outcome_are_independent(
    tmp_path: Path, lifecycle: str, outcome: str | None
) -> None:
    from test_inspection_api import ASGIClient
    from test_runtime_revision_source import archive_world

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.archives import AttemptLease, JournalEntry
    from living_world.runtime import RuntimeService

    catalog, ref, _ = archive_world(tmp_path)
    if lifecycle != "interrupted":
        with (
            AttemptLease(ref),
            catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
        ):
            archive.record(
                (
                    JournalEntry(
                        "attempt_finished",
                        {
                            "lifecycle": lifecycle,
                            "outcome": outcome,
                            "last_revision": 1,
                        },
                    ),
                ),
                lifecycle=lifecycle,
                reason=outcome,
            )
    session = AdminSession.issue()
    client = ASGIClient(
        create_operator_app(RuntimeService(catalog), None, auth=session)
    )
    response = client.request(
        "GET", f"/archives/{ref.attempt_id}", headers=headers(session)
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["attempt"]["lifecycle"] == lifecycle and detail["outcome"] == outcome


def test_commands_fixed_failures_and_auth_query_cannot_bypass(
    tmp_path: Path, monkeypatch
) -> None:
    import json
    from concurrent.futures import Future

    from living_world.runtime import RuntimeStartupError

    client, service, controller, ref, session = operator(tmp_path)
    try:
        command = json.dumps(
            {
                "command_id": "test",
                "action": "step",
                "expected_state_version": controller.status().state_version,
            }
        ).encode()
        for body in (
            b"not json",
            b"{}",
            b'{"command_id":"x","command_id":"y","action":"step","expected_state_version":1}',
        ):
            response = client.request(
                "POST", "/runtime/commands", headers=headers(session), body=body
            )
            assert response.status_code == 422 and response.json() == {
                "detail": "invalid_command"
            }
            assert response.headers["cache-control"] == "no-store"
        assert (
            client.request("GET", "/archives?token=" + session.token).status_code == 401
        )
        for code, expected in (
            ("service_closed", "runtime_unavailable"),
            ("service_not_ready", "runtime_unavailable"),
            ("archive_failed", "archive_invalid"),
        ):

            def submit(_command, code=code):
                future = Future()
                future.set_exception(RuntimeStartupError(ref, code))
                return future

            monkeypatch.setattr(service, "submit", submit)
            response = client.request(
                "POST", "/runtime/commands", headers=headers(session), body=command
            )
            assert response.status_code == 409 and response.json() == {
                "detail": expected
            }
    finally:
        service.shutdown()


def test_blocked_inspection_dto_keeps_loopback_status_responsive(
    tmp_path: Path, monkeypatch
) -> None:
    import json
    import socket
    import threading
    import time
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    import uvicorn

    from living_world.api.auth import AdminSession
    from living_world.api.inspection import EngineWorldInspector
    from living_world.api.operator import create_operator_app

    _client, service, controller, _ref, _session = operator(tmp_path)
    entered, release = threading.Event(), threading.Event()
    dto_threads = []
    original = EngineWorldInspector.world_summary

    def blocked(inspector):
        dto_threads.append(threading.get_ident())
        entered.set()
        assert release.wait(4)
        return original(inspector)

    monkeypatch.setattr(EngineWorldInspector, "world_summary", blocked)
    with socket.socket() as sock, ThreadPoolExecutor(max_workers=1) as pool:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        session = AdminSession.issue(origin=base)
        server = uvicorn.Server(
            uvicorn.Config(
                create_operator_app(service, controller, auth=session),
                log_level="error",
                access_log=False,
            )
        )
        thread = threading.Thread(
            target=lambda: server.run(sockets=[sock]), daemon=True
        )
        thread.start()

        def get(path, timeout=3):
            request = urllib.request.Request(base + path, headers=headers(session))
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)

        world = None
        try:
            deadline = time.monotonic() + 3
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            world = pool.submit(get, "/live/checkpoints/0/world")
            assert entered.wait(2)
            live = get("/runtime/status", timeout=0.75)["live"]
            assert live["tick"] == live["revision"] == 0
            assert not release.is_set()
            assert dto_threads and dto_threads[0] != thread.ident
            release.set()
            assert isinstance(world.result(timeout=2), dict)
        finally:
            release.set()
            server.should_exit = True
            thread.join(6)
            if world is not None:
                world.result(timeout=2)
            service.shutdown()
        assert not thread.is_alive() and not service._thread.is_alive()
