"""Authenticated inert analysis application over real saved trace evidence."""

import importlib

import pytest
from test_inspection_api import ASGIClient

from living_world.api.auth import AdminSession
from living_world.archives.catalog import RunCatalog


def test_offline_status_and_missing_catalog_are_inert(tmp_path):
    module = importlib.import_module("living_world.api.trace_analysis")
    root = tmp_path / "absent"
    auth = AdminSession.issue()
    client = ASGIClient(module.create_analysis_app(RunCatalog(root), auth=auth))
    headers = {"Authorization": f"Bearer {auth.token}"}
    assert client.request("GET", "/analysis/status", headers=headers).json() == {
        "mode": "offline",
        "access": "read_only",
        "capabilities": ["calls", "body_download", "body_preview"],
        "world_validation": "not_performed",
    }
    result = client.request("GET", "/analysis/attempts", headers=headers)
    assert result.json()["attempts"] == []
    assert not root.exists()


def setup(tmp_path):
    module = importlib.import_module("living_world.api.trace_analysis")
    auth = AdminSession.issue()
    client = ASGIClient(module.create_analysis_app(RunCatalog(tmp_path), auth=auth))
    return module, client, {"Authorization": f"Bearer {auth.token}"}, auth


def test_auth_precedes_all_discovery_and_readers(tmp_path, monkeypatch):
    module, client, headers, _auth = setup(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("filesystem reached before auth")

    for name in (
        "list_trace_attempts",
        "resolve_trace_attempt",
        "read_trace_page",
        "read_trace_body",
    ):
        monkeypatch.setattr(module, name, forbidden)
    for path in (
        "/analysis/attempts",
        "/analysis/attempts/unknown/traces",
        "/analysis/attempts/unknown/bodies/abc",
        "/analysis/attempts/unknown/bodies/abc/preview",
    ):
        for credential, code in (
            ({}, 401),
            ({"Authorization": "Bearer wrong"}, 401),
            ({**headers, "Origin": "http://evil.invalid"}, 403),
        ):
            response = client.request("GET", path, headers=credential)
            assert response.status_code == code
            assert response.headers["cache-control"] == "no-store"
            assert "access-control-allow-origin" not in response.headers


def test_exact_failed_body_prefix_download_and_preview(tmp_path):
    from test_trace_analysis_reader import create, fail, snapshot, start

    from living_world.archives import InferenceBlob

    archive = create(tmp_path, checkpoint=False)
    from test_inference_trace_storage import request, request_trace

    archive.append(
        request(request_trace(max_response_bytes=100)),
        inference_blobs=(InferenceBlob(b"{}"),),
    )
    fail(archive, b"<script>\xff\x00{invalid")
    _module, client, headers, _ = setup(tmp_path)
    prefix = f"/analysis/attempts/{archive.ref.attempt_id}"
    before = snapshot(tmp_path)
    result = client.request("GET", prefix + "/traces", headers=headers)
    assert result.status_code == 200
    page = result.json()
    call = page["calls"][0]
    assert (
        call["response_kind"] == "response_failed" and call["elapsed_seconds"] is None
    )
    assert call["response_trace"]["http_status"] == 503
    assert page["integrity"] == "trace_metadata_checked"
    boundary = page["boundary"]
    query = (
        f'?through_sequence={boundary["sequence"]}&journal_digest={boundary["digest"]}'
    )
    bodypath = prefix + "/bodies/" + InferenceBlob(b"<script>\xff\x00{invalid").sha256
    attachment = client.request("GET", bodypath + query, headers=headers)
    assert (
        attachment.status_code == 200 and attachment.body == b"<script>\xff\x00{invalid"
    )
    assert attachment.headers["content-type"] == "application/octet-stream"
    assert attachment.headers["x-content-type-options"] == "nosniff"
    assert attachment.headers["content-disposition"].startswith(
        'attachment; filename="inference-'
    )
    preview = client.request(
        "GET", bodypath + "/preview" + query, headers=headers
    ).json()
    assert preview["text"] == "<script>\ufffd\x00{invalid"
    assert preview["replacement_used"] is True and preview["truncated"] is False
    assert preview["preview_kind"] == "utf8_text"
    start(archive, "later")
    old = client.request("GET", prefix + "/traces" + query, headers=headers).json()
    assert old == page
    after_append = snapshot(tmp_path)
    for path in (
        bodypath,
        prefix + "/traces?through_sequence=0",
        prefix + "/traces?journal_digest=" + "a" * 64,
    ):
        response = client.request("GET", path, headers=headers)
        assert response.status_code == 400 and response.json() == {
            "detail": "invalid_query"
        }
        assert response.headers["cache-control"] == "no-store"
    assert snapshot(tmp_path) == after_append
    assert before != after_append


def test_query_error_sanitization_and_budget(tmp_path, monkeypatch):
    from living_world.archives.trace_analysis import TraceAnalysisLimitError

    module, client, headers, _ = setup(tmp_path)
    for query in (
        "?limit=0",
        "?limit=101",
        "?after_lineage_id=bad",
        "?after_lineage_id=bad&after_attempt_id=bad",
    ):
        response = client.request("GET", "/analysis/attempts" + query, headers=headers)
        assert response.status_code == 400

    def limited(*args, **kwargs):
        raise TraceAnalysisLimitError()

    monkeypatch.setattr(module, "resolve_trace_attempt", limited)
    response = client.request(
        "GET", "/analysis/attempts/unknown/traces", headers=headers
    )
    assert response.status_code == 413 and response.json() == {
        "detail": "analysis_limit_exceeded"
    }

    def broken(*args, **kwargs):
        raise RuntimeError("secret-token-path-rawbody")

    monkeypatch.setattr(module, "resolve_trace_attempt", broken)
    response = client.request(
        "GET", "/analysis/attempts/unknown/traces", headers=headers
    )
    assert response.status_code == 409 and response.json() == {
        "detail": "trace_unavailable"
    }


def test_preview_cap_empty_partial_bodies_and_sealed_prefix(tmp_path):
    from test_inference_trace_storage import request, request_trace
    from test_trace_analysis_reader import create, fail, mutate, snapshot

    from living_world.archives import InferenceBlob

    archive = create(tmp_path)
    _, client, headers, _ = setup(tmp_path)
    prefix = f"/analysis/attempts/{archive.ref.attempt_id}"
    empty = client.request("GET", prefix + "/traces", headers=headers).json()[
        "boundary"
    ]
    query0 = f'?through_sequence=0&journal_digest={empty["digest"]}'
    assert (
        client.request("GET", prefix + "/traces" + query0, headers=headers).json()[
            "calls"
        ]
        == []
    )
    bodies = (b"", b"{broken", b"a" * 65535 + "€".encode())
    for index, raw in enumerate(bodies):
        name = f"req-{index}"
        archive.append(
            request(request_trace(max_response_bytes=100000), request_id=name),
            inference_blobs=(InferenceBlob(b"{}"),),
        )
        fail(archive, raw, name, body_state="incomplete" if index == 1 else "complete")
    page = client.request("GET", prefix + "/traces?limit=1", headers=headers).json()
    boundary = page["boundary"]
    query = (
        f'?through_sequence={boundary["sequence"]}&journal_digest={boundary["digest"]}'
    )
    assert page["next_after_sequence"] == 1
    tail = client.request(
        "GET", prefix + "/traces" + query + "&after_sequence=1", headers=headers
    ).json()
    assert [call["request_id"] for call in tail["calls"]] == ["req-1", "req-2"]
    before = snapshot(tmp_path)
    for index, raw in enumerate(bodies):
        path = prefix + "/bodies/" + InferenceBlob(raw).sha256
        assert client.request("GET", path + query, headers=headers).body == raw
        preview = client.request(
            "GET", path + "/preview" + query, headers=headers
        ).json()
        assert preview["preview_byte_length"] == min(len(raw), 65536)
        assert preview["truncated"] is (index == 2)
        assert preview["replacement_used"] is (index == 2)
        assert preview["text"] == (
            "a" * 65535 + "\ufffd" if index == 2 else raw.decode()
        )
        assert client.request("GET", path + query0, headers=headers).status_code == 409
    assert snapshot(tmp_path) == before
    mutate(
        archive,
        "UPDATE inference_blobs SET body=? WHERE sha256=?",
        (b"x" * len(bodies[1]), InferenceBlob(bodies[1]).sha256),
    )
    path = prefix + "/bodies/" + InferenceBlob(bodies[1]).sha256
    for suffix in ("", "/preview"):
        response = client.request("GET", path + suffix + query, headers=headers)
        assert response.status_code == 409 and response.json() == {
            "detail": "trace_unavailable"
        }
    # An unrelated corrupt body does not broaden selected-body verification.
    path = prefix + "/bodies/" + InferenceBlob(bodies[0]).sha256
    assert client.request("GET", path + query, headers=headers).status_code == 200


def test_offline_lifespan_and_requests_never_construct_runtime(tmp_path, monkeypatch):
    import asyncio

    from living_world.archives.catalog import RunCatalog
    from living_world.archives.lease import AttemptLease
    from living_world.archives.store import AttemptArchive
    from living_world.runtime import RunController, RuntimeService

    def prohibited(*args, **kwargs):
        raise AssertionError("offline app initialized a runtime owner")

    for cls, method in (
        (RuntimeService, "__init__"),
        (RunController, "__init__"),
        (RunCatalog, "reserve"),
        (AttemptLease, "acquire"),
        (RunCatalog, "attempts"),
        (RunCatalog, "open_attempt"),
        (AttemptArchive, "__init__"),
    ):
        monkeypatch.setattr(cls, method, prohibited)
    _, client, headers, _ = setup(tmp_path / "absent")

    async def lifecycle():
        async with client.app.router.lifespan_context(client.app):
            result = await client._request("GET", "/analysis/attempts", headers=headers)
            assert result.status_code == 200

    asyncio.run(lifecycle())
    for path in ("/docs", "/redoc", "/openapi.json", "/analysis/nope"):
        response = client.request("GET", path, headers=headers)
        assert (
            response.status_code == 404
            and response.headers["cache-control"] == "no-store"
        )
    assert not (tmp_path / "absent").exists()


def test_live_operator_mount_preserves_existing_assets(tmp_path):
    from living_world.api.operator import create_operator_app
    from living_world.runtime import RuntimeService

    auth = AdminSession.issue()
    service = RuntimeService(RunCatalog(tmp_path))
    try:
        client = ASGIClient(create_operator_app(service, None, auth=auth))
        headers = {"Authorization": f"Bearer {auth.token}"}
        assert (
            client.request("GET", "/analysis/status", headers=headers).json()["mode"]
            == "live"
        )
        assert client.get("/runtime").status_code == 200
        assert client.get("/runtime/assets/runtime.js").status_code == 200
    finally:
        service.shutdown()


def test_owned_actual_uvicorn_loopback(tmp_path):
    import socket
    import threading
    import time
    import urllib.error
    import urllib.request

    import uvicorn

    _, client, headers, _ = setup(tmp_path / "absent")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    server = uvicorn.Server(
        uvicorn.Config(client.app, log_level="critical", access_log=False)
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [listener]}, daemon=True
    )
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        base = f"http://127.0.0.1:{listener.getsockname()[1]}"
        with urllib.request.urlopen(
            urllib.request.Request(base + "/analysis/status", headers=headers),
            timeout=2,
        ) as response:
            assert (
                response.status == 200
                and response.headers["Cache-Control"] == "no-store"
            )
        try:
            urllib.request.urlopen(base + "/analysis/attempts", timeout=2)
        except urllib.error.HTTPError as response:
            assert (
                response.code == 401 and response.headers["Cache-Control"] == "no-store"
            )
        else:
            raise AssertionError("unauthenticated real HTTP call accepted")
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive()


def test_legacy_pending_missing_database_wal_and_unknown_identity(tmp_path):
    from test_inference_trace_storage import request
    from test_trace_analysis_reader import create, mutate, snapshot

    archive = create(tmp_path, checkpoint=False)
    archive.append(request(None))
    mutate(archive, "UPDATE archive_meta SET payload=json_set(payload,'$.format',1)")
    _, client, headers, _ = setup(tmp_path)
    prefix = f"/analysis/attempts/{archive.ref.attempt_id}"
    result = client.request("GET", prefix + "/traces", headers=headers).json()
    assert result["archive_format"] == 1
    call = result["calls"][0]
    assert all(
        call[name] is None
        for name in (
            "request_trace",
            "response_trace",
            "response_kind",
            "elapsed_seconds",
            "content_digest",
        )
    )
    for identity in ("unknown", "f" * 32):
        response = client.request(
            "GET", f"/analysis/attempts/{identity}/traces", headers=headers
        )
        assert response.status_code == 404 and response.json() == {
            "detail": "not_found"
        }
    (archive.ref.directory / "archive.sqlite3-wal").write_bytes(b"unsupported")
    before = snapshot(tmp_path)
    assert client.request("GET", prefix + "/traces", headers=headers).status_code == 409
    assert snapshot(tmp_path) == before
    archive.database_path.unlink()
    before = snapshot(tmp_path)
    assert client.request("GET", prefix + "/traces", headers=headers).status_code == 409
    assert snapshot(tmp_path) == before


def test_exact_validated_reuse_timing_and_source_projection(tmp_path):
    from uuid import uuid4

    from test_inference_trace_storage import request, request_trace, response_trace
    from test_trace_analysis_reader import create, start

    from living_world.archives import JournalEntry

    archive = create(tmp_path)
    start(archive)
    decision = {"spoken_text": "Ready.", "action_request": None}
    archive.append(
        JournalEntry(
            "response_validated",
            {
                "request_id": "req",
                "decision": decision,
                "content_digest": "d" * 64,
                "elapsed_seconds": 2,
                "response_trace": response_trace(None),
            },
        )
    )
    source = {
        "attempt_id": uuid4().hex,
        "request_id": "original",
        "boundary": {"sequence": 17, "digest": "c" * 64},
    }
    archive.append(
        JournalEntry(
            "response_reused",
            {
                **request(request_trace(), request_id="reused").payload,
                "decision": decision,
                "source": source,
                "response_trace": response_trace(None),
                "elapsed_seconds": 0.75,
                "content_digest": "e" * 64,
            },
        )
    )
    _, client, headers, _ = setup(tmp_path)
    response = client.request(
        "GET", f"/analysis/attempts/{archive.ref.attempt_id}/traces", headers=headers
    )
    assert response.status_code == 200
    first, second = response.json()["calls"]
    assert first["elapsed_seconds"] == 2 and type(first["elapsed_seconds"]) is int
    assert (
        second["elapsed_seconds"] == 0.75 and type(second["elapsed_seconds"]) is float
    )
    assert second["source"] == source and second["request_trace"] == request_trace()
    assert first["content_digest"] == "d" * 64 and second["content_digest"] == "e" * 64


@pytest.mark.parametrize("field", ["scenario_key", "reserved_at"])
def test_escaped_surrogate_header_keeps_valid_rows_and_no_store(tmp_path, field):
    import json

    from test_trace_analysis_catalog import reservation
    from test_trace_analysis_reader import snapshot

    broken, valid = reservation(tmp_path), reservation(tmp_path)
    for directory, scenario in ((broken, "\ud800"), (valid, "København 日本語 🦉")):
        header = directory / "attempt.json"
        data = json.loads(header.read_text())
        data["config"]["scenario_key"] = "København 日本語 🦉"
        data["reserved_at"] = "2026-11-01🦉00:00:00+00:00"
        if field == "scenario_key":
            data["config"][field] = scenario
        elif directory == broken:
            data[field] = "2026-11-01\ud80000:00:00+00:00"
        header.write_text(json.dumps(data))
    before = snapshot(tmp_path)
    _, client, headers, _ = setup(tmp_path)
    response = client.request("GET", "/analysis/attempts", headers=headers)
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    rows = {row["attempt_id"]: row for row in response.json()["attempts"]}
    assert rows[broken.name]["metadata_state"] == "invalid"
    assert rows[broken.name]["scenario_key"] is None
    assert rows[valid.name]["scenario_key"] == "København 日本語 🦉"
    assert rows[valid.name]["reserved_at"] == "2026-11-01🦉00:00:00+00:00"
    assert snapshot(tmp_path) == before


def test_trace_encoding_failure_is_sanitized_in_both_mounts(tmp_path):
    from test_inference_trace_storage import request, request_trace
    from test_trace_analysis_reader import create, snapshot

    from living_world.api.operator import create_operator_app
    from living_world.archives import InferenceBlob, JournalEntry
    from living_world.runtime import RuntimeService

    archive = create(tmp_path)
    for name, label in (("valid", "Zoë 日本語 🦉"), ("bad", "\ud800")):
        payload = dict(request(request_trace(), request_id=name).payload)
        payload["actor_label"] = label
        archive.append(
            JournalEntry("request_started", payload),
            inference_blobs=(InferenceBlob(b"{}"),),
        )
        if name == "valid":
            sealed = archive.journal_boundary()
    before = snapshot(tmp_path)
    _, offline, headers, auth = setup(tmp_path)
    service = RuntimeService(RunCatalog(tmp_path))
    try:
        live = ASGIClient(create_operator_app(service, None, auth=auth))
        for client in (offline, live):
            prefix = f"/analysis/attempts/{archive.ref.attempt_id}"
            response = client.request("GET", prefix + "/traces", headers=headers)
            assert response.status_code == 409
            assert response.json() == {"detail": "trace_unavailable"}
            assert response.headers["cache-control"] == "no-store"
            # Narrow prefix retains valid non-ASCII text and exact opaque bytes.
            query = f"?through_sequence=1&journal_digest={sealed.digest}"
            valid = client.request("GET", prefix + "/traces" + query, headers=headers)
            assert valid.status_code == 200
            assert valid.json()["calls"][0]["actor_label"] == "Zoë 日本語 🦉"
            body = client.request(
                "GET",
                prefix + "/bodies/" + InferenceBlob(b"{}").sha256 + query,
                headers=headers,
            )
            assert body.status_code == 200 and body.body == b"{}"
        assert snapshot(tmp_path) == before
    finally:
        service.shutdown()
