"""Public inert shell and real Chrome saved evidence browsing."""

import importlib

import pytest
from test_inspection_api import ASGIClient
from test_runtime_operator_api import operator

from living_world.api.auth import AdminSession
from living_world.archives.catalog import RunCatalog


@pytest.mark.parametrize("mode", ["live", "offline"])
def test_public_shell_keeps_evidence_protected(tmp_path, mode):
    service = None
    if mode == "live":
        client, service, _, _, auth = operator(tmp_path)
    else:
        auth = AdminSession.issue()
        module = importlib.import_module("living_world.api.trace_analysis")
        client = ASGIClient(module.create_analysis_app(RunCatalog(tmp_path), auth=auth))
    try:
        for path, media in (
            ("/analysis", "text/html"),
            ("/analysis/assets/analysis.css", "text/css"),
            ("/analysis/assets/analysis.js", "text/javascript"),
        ):
            result = client.request("GET", path)
            assert result.status_code == 200
            assert result.headers["content-type"].startswith(media)
            assert result.headers["cache-control"] == "no-store"
            assert auth.token.encode() not in result.body
            assert auth.csrf_nonce.encode() not in result.body
        for path in ("/analysis/assets/unknown", "/analysis/assets/runtime.js"):
            assert client.request("GET", path).status_code == 404
        assert client.request("GET", "/analysis/status").status_code == 401
        assert (
            client.request(
                "GET",
                "/analysis/status",
                headers={
                    "Authorization": f"Bearer {auth.token}",
                    "Origin": "http://evil.invalid",
                },
            ).status_code
            == 403
        )
        assert client.request("POST", "/analysis/status").status_code == 405
    finally:
        if service is not None:
            service.shutdown()


@pytest.fixture(params=["offline", "live"])
def trace_browser(tmp_path, request):
    """Owned loopback application and Chrome, without starting a simulation."""
    import os
    import socket
    import threading
    import time
    from pathlib import Path

    import uvicorn
    from test_inference_trace_storage import request as saved_request
    from test_inference_trace_storage import request_trace
    from test_trace_analysis_reader import create, fail

    from living_world.archives import InferenceBlob

    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent")
    root = tmp_path / "runs"
    archive = create(root)
    raw = b"<script>window.pwned=true</script>\xff\x00" + b"x" * 65536
    for index in range(52):
        name = f"req-{index}"
        archive.append(
            saved_request(request_trace(max_response_bytes=100000), request_id=name),
            inference_blobs=(InferenceBlob(b"{}"),),
        )
        fail(
            archive,
            raw if index == 0 else b"",
            name,
            body_state="incomplete" if index == 0 else "complete",
        )
    other = create(root, checkpoint=False)
    observed, errors = [], []
    service = None
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        auth = AdminSession.issue(origin=base)
        catalog = RunCatalog(root)
        if request.param == "offline":
            from living_world.api.trace_analysis import create_analysis_app

            app = create_analysis_app(catalog, auth=auth)
        else:
            from living_world.api.operator import create_operator_app
            from living_world.runtime import RuntimeService

            service = RuntimeService(catalog)
            app = create_operator_app(service, None, auth=auth)

        @app.middleware("http")
        async def observe(req, call_next):
            observed.append(
                (req.method, str(req.url), req.headers.get("authorization"))
            )
            return await call_next(req)

        server = uvicorn.Server(
            uvicorn.Config(app, log_level="error", access_log=False)
        )
        thread = threading.Thread(
            target=lambda: server.run(sockets=[sock]), daemon=True
        )
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    executable_path=executable, headless=True
                )
                try:
                    page = browser.new_page(accept_downloads=True)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "/analysis")
                    yield page, auth, archive, other, raw, root, observed, request.param
                    assert errors == []
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(8)
            if service is not None:
                service.shutdown()
            assert not thread.is_alive()


def connect(page, auth):
    from playwright.sync_api import expect

    page.get_by_label("Administrator token").fill(auth.token)
    page.get_by_role("button", name="Connect", exact=True).click()
    expect(page.locator("#notice")).to_have_text("Connected.")


def select_first(page, archive):
    from playwright.sync_api import expect

    page.get_by_role("button", name=archive.ref.attempt_id, exact=True).click()
    expect(page.locator("#calls tr")).to_have_count(50)
    page.get_by_role("button", name="req-0", exact=True).click()


def test_chrome_saved_bytes_paging_refresh_and_mobile(trace_browser):
    import hashlib

    from playwright.sync_api import expect
    from test_trace_analysis_reader import snapshot, start

    page, auth, archive, _, raw, root, observed, mode = trace_browser
    before = snapshot(root)
    connect(page, auth)
    expect(page.get_by_label("Administrator token")).to_have_value("")
    expect(page.locator("#mode")).to_contain_text(mode + " · read-only")
    select_first(page, archive)
    expect(page.locator("#details")).to_contain_text("incomplete captured prefix")
    expect(page.locator("#details")).to_contain_text("ollama")
    expect(page.locator("#details")).to_contain_text("unavailable")
    boundary = page.locator("#boundary").inner_text()
    page.get_by_role("button", name="Preview response", exact=True).click()
    expect(page.locator("#preview-meta")).to_contain_text("replacement_used: true")
    expect(page.locator("#preview-meta")).to_contain_text("truncated: true")
    expect(page.locator("#preview")).to_contain_text(
        "<script>window.pwned=true</script>"
    )
    assert page.evaluate("window.pwned") is None
    page.evaluate("""() => {
      const revoke = URL.revokeObjectURL.bind(URL); window.revoked = [];
      URL.revokeObjectURL = url => {window.revoked.push(url); revoke(url);};
    }""")
    with page.expect_download() as captured:
        page.get_by_role("button", name="Download response", exact=True).click()
    download = captured.value
    assert (
        download.suggested_filename
        == f"inference-{hashlib.sha256(raw).hexdigest()}.bin"
    )
    assert download.path().read_bytes() == raw
    expect(page.locator("#notice")).to_have_text("Download dispatched.")
    page.wait_for_timeout(50)
    assert page.evaluate("window.revoked.length") == 1
    page.get_by_role("button", name="req-1", exact=True).click()
    with page.expect_download() as captured:
        page.get_by_role("button", name="Download response", exact=True).click()
    assert captured.value.path().read_bytes() == b""
    with page.expect_download() as captured:
        page.get_by_role("button", name="Download request", exact=True).click()
    request_download = captured.value
    assert request_download.path().read_bytes() == b"{}"
    assert request_download.suggested_filename == (
        f"inference-{hashlib.sha256(b'{}').hexdigest()}.bin"
    )
    assert snapshot(root) == before
    start(archive, "later")
    after_append = snapshot(root)
    page.get_by_role("button", name="More calls", exact=True).click()
    expect(page.locator("#calls tr")).to_have_count(52)
    assert page.locator("#boundary").inner_text() == boundary
    page.get_by_role("button", name="Refresh calls", exact=True).click()
    expect(page.locator("#detail-panel")).to_be_hidden()
    expect(page.locator("#calls tr")).to_have_count(50)
    page.get_by_role("button", name="More calls", exact=True).click()
    expect(page.locator("#calls tr")).to_have_count(53)
    page.get_by_role("button", name="later", exact=True).click()
    expect(page.locator("#details")).to_contain_text("pending")
    expect(
        page.get_by_role("button", name="Download response", exact=True)
    ).to_be_disabled()
    for width in (360, 1280):
        page.set_viewport_size({"width": width, "height": 800})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert (
        page.evaluate("JSON.stringify([localStorage,sessionStorage,document.cookie])")
        == '[{},{},""]'
    )
    assert all(auth.token not in url and method == "GET" for method, url, _ in observed)
    assert auth.token not in page.content()
    page.get_by_role("button", name="Disconnect", exact=True).click()
    expect(page.locator("#session")).to_be_hidden()
    expect(page.locator("#details")).to_have_text("")
    assert snapshot(root) == after_append


def wait_held(page, held):
    import time

    deadline = time.monotonic() + 4
    while not held and time.monotonic() < deadline:
        page.wait_for_timeout(20)
    assert held


def release_held(held, **kwargs):
    from contextlib import suppress

    from playwright.sync_api import Error

    for route, response in held:
        with suppress(Error):
            route.fulfill(**kwargs) if kwargs else route.fulfill(response=response)
    held.clear()


@pytest.mark.parametrize("code", [401, 403])
def test_chrome_old_rejection_cannot_clear_reconnect(trace_browser, code):
    from playwright.sync_api import expect

    page, auth, archive, *_ = trace_browser
    held = []

    def hold(route):
        held.append((route, route.fetch()))

    page.route("**/analysis/attempts?*", hold)
    try:
        connect(page, auth)
        wait_held(page, held)
        page.get_by_role("button", name="Disconnect", exact=True).click()
        page.unroute("**/analysis/attempts?*", hold)
        connect(page, auth)
        release_held(held, status=code, json={"detail": "unauthorized"})
        page.wait_for_timeout(100)
        expect(page.locator("#notice")).to_have_text("Connected.")
        expect(
            page.get_by_role("button", name=archive.ref.attempt_id, exact=True)
        ).to_be_enabled()
    finally:
        release_held(held)


@pytest.mark.parametrize(
    "operation",
    ["select_call", "select_attempt", "refresh", "reconnect", "replace_body"],
)
@pytest.mark.parametrize("download", [False, True])
def test_chrome_late_bodies_do_not_repaint_or_download(
    trace_browser, operation, download
):
    from playwright.sync_api import expect

    page, auth, archive, other, *_ = trace_browser
    held, downloads = [], []
    page.on("download", lambda result: downloads.append(result))
    connect(page, auth)
    select_first(page, archive)

    def hold(route):
        if not held:
            held.append((route, route.fetch()))
        else:
            route.continue_()

    page.route("**/analysis/attempts/*/bodies/**", hold)
    try:
        page.get_by_role(
            "button",
            name="Download response" if download else "Preview response",
            exact=True,
        ).click()
        wait_held(page, held)
        if operation == "replace_body":
            page.get_by_role("button", name="Preview request", exact=True).click()
            expect(page.locator("#preview")).to_have_text("{}")
        elif operation == "select_call":
            page.get_by_role("button", name="req-1", exact=True).click()
        elif operation == "select_attempt":
            page.get_by_role("button", name=other.ref.attempt_id, exact=True).click()
        elif operation == "refresh":
            page.get_by_role("button", name="Refresh calls", exact=True).click()
        else:
            page.get_by_role("button", name="Disconnect", exact=True).click()
            connect(page, auth)
        release_held(held)
        page.wait_for_timeout(150)
        expect(page.locator("#preview")).to_have_text(
            "{}" if operation == "replace_body" else ""
        )
        assert downloads == []
        if operation == "reconnect":
            expect(page.locator("#notice")).to_have_text("Connected.")
    finally:
        release_held(held)


@pytest.mark.parametrize(
    "failure",
    [
        "array",
        "number",
        "digest",
        "body_state",
        "duration",
        "cursor",
        "boundary",
        "body_pair",
        "request_digest_null",
        "request_length_null",
        "request_both_null",
        "request_length_zero",
        "timestamps",
    ],
)
def test_chrome_rejects_malformed_call_dtos(trace_browser, failure):
    from playwright.sync_api import expect

    page, auth, archive, *_ = trace_browser
    connect(page, auth)

    def malformed(route):
        response = route.fetch()
        value = response.json()
        if failure == "array":
            value["calls"] = {}
        elif failure == "number":
            value["calls"][0]["source_tick"] = 9007199254740992
        elif failure == "digest":
            value["calls"][0]["response_trace"]["body_digest"] = "../secret"
        elif failure == "body_state":
            value["calls"][0]["response_trace"]["body_state"] = "fabricated"
        elif failure == "duration":
            value["calls"][0]["response_trace"]["durations"]["worker_seconds"] = -1
        elif failure == "request_digest_null":
            value["calls"][0]["request_trace"]["body_digest"] = None
        elif failure == "request_length_null":
            value["calls"][0]["request_trace"]["body_length"] = None
        elif failure == "request_both_null":
            value["calls"][0]["request_trace"]["body_digest"] = None
            value["calls"][0]["request_trace"]["body_length"] = None
        elif failure == "request_length_zero":
            value["calls"][0]["request_trace"]["body_length"] = 0
        elif failure == "body_pair":
            value["calls"][0]["response_trace"]["body_length"] = None
        elif failure == "timestamps":
            del value["calls"][0]["response_trace"]["timestamps"]["settled_at"]
        elif failure == "cursor":
            value["next_after_sequence"] = -1
        else:
            value["boundary"]["digest"] = "A" * 64
        route.fulfill(status=200, json=value)

    page.route("**/analysis/attempts/*/traces?*", malformed)
    page.get_by_role("button", name=archive.ref.attempt_id, exact=True).click()
    expect(page.locator("#notice")).to_have_text("Saved evidence is invalid.")
    expect(page.locator("#calls tr")).to_have_count(0)
    expect(page.locator("#detail-panel")).to_be_hidden()
    for side in ("request", "response"):
        for operation in ("preview", "download"):
            expect(page.locator(f"#{operation}-{side}")).to_be_disabled()


@pytest.mark.parametrize(
    "code,expected",
    [
        (404, "unavailable or not found"),
        (409, "changed or is invalid"),
        (413, "exceeds the read limit"),
    ],
)
def test_chrome_distinct_errors_and_private_clear(trace_browser, code, expected):
    from playwright.sync_api import expect

    page, auth, archive, *_ = trace_browser
    connect(page, auth)
    select_first(page, archive)
    page.route(
        "**/analysis/attempts/*/bodies/**",
        lambda route: route.fulfill(status=code, body="secret exception"),
    )
    page.get_by_role("button", name="Preview response", exact=True).click()
    expect(page.locator("#notice")).to_contain_text(expected)
    assert "secret exception" not in page.content()
    page.route(
        "**/analysis/attempts?*",
        lambda route: route.fulfill(status=401, body="secret exception"),
    )
    page.get_by_role("button", name="Refresh attempts", exact=True).click()
    expect(page.locator("#session")).to_be_hidden()
    expect(page.locator("#attempts")).to_have_text("")
    expect(page.locator("#details")).to_have_text("")
    expect(page.locator("#notice")).to_contain_text("Connection rejected")


def test_chrome_timeout_and_pagehide_clear(trace_browser):
    from playwright.sync_api import expect

    page, auth, archive, *_ = trace_browser
    connect(page, auth)
    select_first(page, archive)
    page.clock.install()
    held = []

    def hold(route):
        held.append((route, route.fetch()))

    page.route("**/analysis/attempts/*/bodies/**", hold)
    try:
        page.get_by_role("button", name="Preview response", exact=True).click()
        wait_held(page, held)
        page.clock.run_for(10001)
        expect(page.locator("#notice")).to_have_text("Request timed out. Try again.")
        release_held(held)
        expect(page.locator("#preview")).to_have_text("")
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
        expect(page.locator("#session")).to_be_hidden()
        expect(page.locator("#details")).to_have_text("")
    finally:
        release_held(held)


def test_chrome_actual_backend_opaque_model_zero_null_reused_and_legacy(trace_browser):
    from uuid import uuid4

    from playwright.sync_api import expect
    from test_inference_trace_storage import (
        DURATIONS,
        TIMESTAMPS,
        request,
        request_trace,
        response_trace,
    )

    from living_world.archives import InferenceBlob, JournalEntry

    page, auth, _, archive, *_ = trace_browser
    model_identity = "sha256:" + "b" * 64 + "/saved/model.gguf"
    trace = request_trace(
        provider_kind="llama_cpp",
        model="<img src=x onerror=alert(1)>",
        model_digest=model_identity,
        url="http://localhost:8080/v1/chat/completions",
    )
    archive.append(request(trace), inference_blobs=(InferenceBlob(b"{}"),))
    archive.append(
        JournalEntry(
            "response_validated",
            {
                "request_id": "req",
                "decision": {"spoken_text": "Hi", "action_request": None},
                "content_digest": "d" * 64,
                "elapsed_seconds": 0,
                "response_trace": response_trace(
                    None,
                    durations={**dict.fromkeys(DURATIONS), "http_seconds": 0},
                    timestamps={
                        **dict.fromkeys(TIMESTAMPS),
                        "settled_at": "2026-10-27T12:00:00+00:00",
                    },
                ),
            },
        )
    )
    source = {
        "attempt_id": uuid4().hex,
        "request_id": "source-request",
        "boundary": {"sequence": 0, "digest": "c" * 64},
    }
    archive.append(
        JournalEntry(
            "response_reused",
            {
                **request(trace, request_id="reused").payload,
                "decision": {"spoken_text": "Hi", "action_request": None},
                "source": source,
                "response_trace": response_trace(None),
                "elapsed_seconds": 0,
                "content_digest": "e" * 64,
            },
        )
    )
    archive.append(request(None, request_id="legacy"))
    connect(page, auth)
    page.get_by_role("button", name=archive.ref.attempt_id, exact=True).click()
    page.get_by_role("button", name="req", exact=True).click()
    expect(page.locator("#details")).to_contain_text(model_identity)
    expect(page.locator("#details")).to_contain_text("provider_kind: llama_cpp")
    expect(page.locator("#details")).to_contain_text("elapsed_seconds: 0")
    expect(page.locator("#details")).to_contain_text("http_seconds: 0")
    expect(page.locator("#details")).to_contain_text("worker_seconds: unavailable")
    expect(page.locator("#details")).to_contain_text(
        "settled_at: 2026-10-27T12:00:00+00:00"
    )
    assert page.locator("#details img").count() == 0
    page.get_by_role("button", name="reused", exact=True).click()
    expect(page.locator("#details")).to_contain_text(
        "Original reused evidence/timing; not a new latency measurement."
    )
    expect(page.locator("#details")).to_contain_text("source-request")
    page.get_by_role("button", name="legacy", exact=True).click()
    expect(page.locator("#details")).to_contain_text("legacy/unavailable")
    expect(
        page.get_by_role("button", name="Download request", exact=True)
    ).to_be_disabled()


def test_chrome_catalog_paired_cursor_missing_invalid_and_zero_boundary(trace_browser):
    from urllib.parse import parse_qs, urlsplit
    from uuid import uuid4

    from playwright.sync_api import expect

    page, auth, _, archive, _, root, observed, _ = trace_browser
    for index in range(51):
        folder = root / uuid4().hex / uuid4().hex
        folder.mkdir(parents=True)
        if index == 0:
            (folder / "attempt.json").write_text("invalid")
    connect(page, auth)
    expect(page.locator("#attempts tr")).to_have_count(50)
    page.get_by_role("button", name="More attempts", exact=True).click()
    expect(page.locator("#attempts tr")).to_have_count(53)
    expect(page.locator("#attempts")).to_contain_text("missing")
    expect(page.locator("#attempts")).to_contain_text("invalid")
    assert page.locator("#attempts button:disabled").count() == 51
    query = parse_qs(
        urlsplit(next(url for _, url, _ in observed if "after_lineage_id" in url)).query
    )
    assert set(query) == {"limit", "after_lineage_id", "after_attempt_id"}
    assert len(query["after_lineage_id"][0]) == len(query["after_attempt_id"][0]) == 32
    page.get_by_role("button", name=archive.ref.attempt_id, exact=True).click()
    expect(page.locator("#boundary")).to_contain_text("Boundary sequence: 0")

    count = {"value": 0}

    def zero_cursor(route):
        response = route.fetch()
        value = response.json()
        if count["value"] == 0:
            value["next_after_sequence"] = 0
        count["value"] += 1
        route.fulfill(status=200, json=value)

    page.route("**/analysis/attempts/*/traces?*", zero_cursor)
    page.get_by_role("button", name="Refresh calls", exact=True).click()
    expect(page.get_by_role("button", name="More calls", exact=True)).to_be_enabled()
    page.get_by_role("button", name="More calls", exact=True).click()
    expect(page.get_by_role("button", name="More calls", exact=True)).to_be_disabled()
    requests = [url for _, url, _ in observed if "after_sequence=" in url]
    query = parse_qs(urlsplit(requests[-1]).query)
    assert query["after_sequence"] == ["0"] and query["through_sequence"] == ["0"]
    page.get_by_role("button", name="Refresh attempts", exact=True).click()
    expect(page.locator("#attempts tr")).to_have_count(50)
    expect(page.locator("#call-panel")).to_be_hidden()


@pytest.mark.parametrize("code", [401, 403])
def test_chrome_old_login_rejection_cannot_clear_new_login(trace_browser, code):
    from playwright.sync_api import expect

    page, auth, *_ = trace_browser
    held = []

    def hold(route):
        if not held:
            held.append((route, route.fetch()))
        else:
            route.continue_()

    page.route("**/analysis/status", hold)
    try:
        page.get_by_label("Administrator token").fill(auth.token)
        page.get_by_role("button", name="Connect", exact=True).click()
        wait_held(page, held)
        connect(page, auth)
        release_held(held, status=code, json={"detail": "unauthorized"})
        page.wait_for_timeout(100)
        expect(page.locator("#notice")).to_have_text("Connected.")
        expect(page.locator("#session")).to_be_visible()
    finally:
        release_held(held)


@pytest.mark.parametrize("operation", ["attempt", "refresh"])
def test_chrome_late_call_listing_cannot_replace_new_selection(
    trace_browser, operation
):
    from playwright.sync_api import expect

    page, auth, archive, other, *_ = trace_browser
    held = []

    def hold(route):
        held.append((route, route.fetch()))

    connect(page, auth)
    page.route("**/analysis/attempts/*/traces?*", hold)
    try:
        page.get_by_role("button", name=archive.ref.attempt_id, exact=True).click()
        wait_held(page, held)
        page.unroute("**/analysis/attempts/*/traces?*", hold)
        if operation == "attempt":
            page.get_by_role("button", name=other.ref.attempt_id, exact=True).click()
            expect(page.locator("#boundary")).to_contain_text("Boundary sequence: 0")
        else:
            page.get_by_role("button", name="Refresh calls", exact=True).click()
            expect(page.locator("#calls tr")).to_have_count(50)
        value = held[0][1].json()
        value["calls"][0]["actor_label"] = "stale actor"
        release_held(held, status=200, json=value)
        page.wait_for_timeout(100)
        assert "stale actor" not in page.locator("#calls").inner_text()
        expect(page.locator("#notice")).to_have_text("Connected.")
    finally:
        release_held(held)


def test_public_shell_offline_inert_with_source_unchanged(tmp_path, monkeypatch):
    from test_trace_analysis_reader import create, snapshot

    from living_world.archives.store import AttemptArchive
    from living_world.runtime import RunController, RuntimeService
    from living_world.state.world_state import WorldState

    create(tmp_path)
    before = snapshot(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("static shell constructed runtime/world/archive")

    for cls in (RuntimeService, RunController, WorldState, AttemptArchive):
        monkeypatch.setattr(cls, "__init__", forbidden)
    module = importlib.import_module("living_world.api.trace_analysis")
    app = module.create_analysis_app(RunCatalog(tmp_path), auth=AdminSession.issue())
    client = ASGIClient(app)
    for path in (
        "/analysis",
        "/analysis/assets/analysis.js",
        "/analysis/assets/analysis.css",
    ):
        assert client.request("GET", path).status_code == 200
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("failure", ["identity", "cursor"])
def test_chrome_bad_identity_never_becomes_an_evidence_path(trace_browser, failure):
    from playwright.sync_api import expect

    page, auth, _, _, _, _, observed, _ = trace_browser

    def malformed(route):
        response = route.fetch()
        value = response.json()
        if failure == "identity":
            value["attempts"][0]["attempt_id"] = "../unsafe"
        else:
            value["next_after"] = {"lineage_id": "A" * 32, "attempt_id": "../unsafe"}
        route.fulfill(status=200, json=value)

    page.route("**/analysis/attempts?*", malformed)
    page.get_by_label("Administrator token").fill(auth.token)
    page.get_by_role("button", name="Connect", exact=True).click()
    expect(page.locator("#session")).to_be_visible()
    if failure == "identity":
        expect(
            page.get_by_role("button", name="../unsafe", exact=True)
        ).to_be_disabled()
    else:
        expect(page.locator("#notice")).to_have_text("Saved evidence is invalid.")
        expect(page.locator("#attempts tr")).to_have_count(0)
    assert not [url for _, url, _ in observed if "/traces" in url]
