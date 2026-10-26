"""Packaged operator page and real browser/runtime behavior."""

import tomllib
from pathlib import Path

from test_runtime_operator_api import operator


def test_public_runtime_resources_and_packaging(tmp_path: Path) -> None:
    client, service, _, _, session = operator(tmp_path)
    try:
        for path, media in (
            ("/runtime", "text/html"),
            ("/runtime/assets/runtime.js", "text/javascript"),
            ("/runtime/assets/runtime.css", "text/css"),
        ):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith(media)
            assert response.headers["cache-control"] == "no-store"
            assert session.token.encode() not in response.body
            assert session.csrf_nonce.encode() not in response.body
        for name in ("runtime.html", "inspector.js", "unknown"):
            assert client.get("/runtime/assets/" + name).status_code == 404
        data = tomllib.loads(Path("pyproject.toml").read_text())["tool"]["setuptools"][
            "package-data"
        ]
        assert data["living_world.api"] == [
            "static/inspector.html",
            "static/inspector.css",
            "static/inspector.js",
            "static/runtime.html",
            "static/runtime.css",
            "static/runtime.js",
        ]
        assert len(data["living_world.founders"]) == 5
    finally:
        service.shutdown()


import os
import socket
import threading
import time
from collections.abc import Iterator

import pytest


@pytest.fixture
def runtime_browser(tmp_path: Path, request, monkeypatch) -> Iterator[tuple]:
    import uvicorn
    from test_runtime_service import reserved

    from living_world.api.auth import AdminSession
    from living_world.api.operator import create_operator_app
    from living_world.runtime import RuntimeService

    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent")
    from contextlib import ExitStack

    stack = ExitStack()
    release = threading.Event()
    broker = None
    mode = getattr(request, "param", "recorded")
    if mode == "ollama":
        from test_runtime_ollama_driver import ImmediateBroker
        from test_runtime_preflight import tags_server
        from test_runtime_service import live_reserved

        from living_world.runtime import launch

        class Delayed(ImmediateBroker):
            def poll(self, job_id):
                return super().poll(job_id) if release.is_set() else None

        broker = Delayed(failure="timeout")
        monkeypatch.setattr(launch, "DecisionBroker", lambda: broker)
        provider = stack.enter_context(
            tags_server({"models": [{"name": "tiny:latest", "digest": "a" * 64}]})
        )
        catalog, config, ref, inputs = live_reserved(tmp_path, provider)
    else:
        catalog, config, ref, inputs = reserved(tmp_path)
    service = RuntimeService(catalog)
    controller = service.start(config, inputs, paused=True)
    if mode == "archive":
        service.shutdown()
        service = RuntimeService(catalog)
        controller = None
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        session = AdminSession.issue(origin=base)
        app = create_operator_app(service, controller, auth=session)
        observed = []

        @app.middleware("http")
        async def observe(request, call_next):
            observed.append(
                (request.method, request.url.path, request.headers.get("authorization"))
            )
            return await call_next(request)

        server = uvicorn.Server(
            uvicorn.Config(app, log_level="error", access_log=False)
        )
        thread = threading.Thread(
            target=lambda: server.run(sockets=[sock]), daemon=True
        )
        thread.start()
        try:
            deadline = time.monotonic() + 4
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    executable_path=executable, headless=True
                )
                page = browser.new_page()
                page.goto(base + "/runtime")
                yield page, service, ref, session, observed, base, (release, broker)
                browser.close()
        finally:
            server.should_exit = True
            thread.join(8)
            release.set()
            service.shutdown()
            stack.close()
            assert not thread.is_alive()


def login(page, session):
    from playwright.sync_api import expect

    page.get_by_label("Administrator token").fill(session.token)
    page.get_by_role("button", name="Connect", exact=True).click()
    expect(page.locator("#notice")).to_have_text("Connected.")


def test_browser_login_single_step_fixed_history_and_logout(runtime_browser):
    from playwright.sync_api import expect

    page, service, ref, session, observed, base, _ = runtime_browser
    expect(page.locator("#session")).to_be_hidden()
    login(page, session)
    expect(page.locator("#live")).to_contain_text("Last committed tick: 0")
    frame = page.frame_locator('iframe[title="World Inspector"]')
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    page.get_by_role("button", name="Step", exact=True).dblclick()
    expect(page.locator("#live")).to_contain_text("Last committed tick: 1")
    page.wait_for_timeout(1200)
    assert service.controller.status().tick == 1
    commands = [p for method, p, _ in observed if method == "POST"]
    assert commands == ["/runtime/commands"]
    page.get_by_role("button", name=ref.attempt_id, exact=True).click()
    expect(page.locator("#controls")).to_be_hidden()
    expect(page.locator("#configuration")).to_contain_text("generic")
    page.get_by_label("Complete checkpoint").select_option("0")
    expect(frame.locator("#tick")).to_have_text("Reported tick: 0")
    from living_world.archives import CommandEnvelope

    service.submit(
        CommandEnvelope(
            "external-step", "step", service.controller.status().state_version
        )
    ).result(3)
    page.wait_for_timeout(1300)
    expect(frame.locator("#tick")).to_have_text("Reported tick: 0")
    assert len([p for m, p, _ in observed if m == "POST"]) == 1
    assert page.url == base + "/runtime"
    assert (
        page.evaluate("JSON.stringify([localStorage,sessionStorage,document.cookie])")
        == '[{},{},""]'
    )
    assert (
        session.token not in page.content() and session.csrf_nonce not in page.content()
    )
    page.get_by_role("button", name="Return to live", exact=True).click()
    expect(frame.locator("#tick")).to_have_text("Reported tick: 2")
    page.get_by_role("button", name="Disconnect", exact=True).click()
    expect(page.locator("#session")).to_be_hidden()
    expect(page.locator("iframe")).to_have_count(0)
    assert service.controller.status().state.value == "paused"
    assert page.get_by_label("Administrator token").input_value() == ""


def test_browser_uncertain_delivery_keeps_original_envelope(runtime_browser):
    from playwright.sync_api import expect

    page, service, _, session, observed, _, _ = runtime_browser
    login(page, session)
    envelopes = []

    def lose(route):
        envelopes.append(route.request.post_data_json)
        if len(envelopes) == 1:
            route.abort()
        else:
            route.continue_()

    page.route("**/runtime/commands", lose)
    page.get_by_role("button", name="Step", exact=True).click()
    expect(
        page.get_by_role("button", name="Retry delivery", exact=True)
    ).to_be_visible()
    page.wait_for_timeout(1200)
    assert len(envelopes) == 1
    assert service.controller.status().tick == 0
    page.get_by_role("button", name="Retry delivery", exact=True).click()
    expect(page.locator("#live")).to_contain_text("Last committed tick: 1")
    assert envelopes[0] == envelopes[1]
    assert len([p for m, p, _ in observed if m == "POST"]) == 1


def test_browser_bad_auth_stale_and_literal_archive_prose(runtime_browser):
    from playwright.sync_api import expect

    page, _, _, session, _, _, _ = runtime_browser
    page.get_by_label("Administrator token").fill("x" * 43)
    page.get_by_role("button", name="Connect", exact=True).click()
    expect(page.locator("#notice")).to_contain_text("Connection rejected")
    login(page, session)
    page.route(
        "**/runtime/status",
        lambda route: route.fulfill(
            status=200,
            json={"live": {"state": "invented"}},
            headers={"X-CSRF-Token": session.csrf_nonce},
        ),
    )
    expect(page.locator("#freshness")).to_contain_text("stale")
    expect(page.locator("#freshness")).to_contain_text("Last refresh:")
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_disabled()
    page.unroute("**/runtime/status")
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_enabled()
    page.route(
        "**/runtime/status",
        lambda route: route.fulfill(status=403, json={"detail": "forbidden"}),
    )
    expect(page.locator("#session")).to_be_hidden()
    expect(page.locator("#archives")).to_be_empty()
    expect(page.locator("iframe")).to_have_count(0)
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_browser_history_label_retains_metadata_and_inflight_source_is_ignored(
    runtime_browser,
):
    from playwright.sync_api import expect

    page, _, ref, session, _, _, _ = runtime_browser
    login(page, session)
    page.get_by_role("button", name=ref.attempt_id, exact=True).click()
    expect(page.locator("#details")).to_contain_text(ref.attempt_id)
    page.get_by_label("Complete checkpoint").select_option("0")
    expect(page.locator("#source")).to_contain_text("recorded")
    expect(page.locator("#source")).to_contain_text("parent")


@pytest.mark.parametrize("runtime_browser", ["ollama"], indirect=True)
def test_browser_delayed_provider_pause_retry_and_stop(runtime_browser):
    from playwright.sync_api import expect
    from test_runtime_service import wait_for

    from living_world.runtime import RuntimeState

    page, service, ref, session, observed, _, (release, broker) = runtime_browser
    login(page, session)
    page.get_by_role("button", name="Step", exact=True).click()
    expect(page.locator("#live")).to_contain_text("awaiting_model")
    expect(page.get_by_role("button", name="Pause", exact=True)).to_be_enabled()
    page.get_by_role("button", name="Pause", exact=True).click()
    expect(page.locator("#receipts")).to_contain_text("Pause requested")
    release.set()
    wait_for(
        service.controller, lambda s: s.state is RuntimeState.PROVIDER_ERROR_PAUSED
    )
    expect(page.get_by_role("button", name="Retry model", exact=True)).to_be_enabled()
    before = len([p for m, p, _ in observed if m == "POST"])
    page.wait_for_timeout(1100)
    assert len([p for m, p, _ in observed if m == "POST"]) == before
    broker.failure = None
    page.get_by_role("button", name="Retry model", exact=True).click()
    expect(page.locator("#live")).to_contain_text("State: paused")
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_enabled()
    page.get_by_role("button", name="Step", exact=True).click()
    expect(page.locator("#live")).to_contain_text("Last committed tick: 1")
    expect(page.get_by_role("button", name="Stop", exact=True)).to_be_enabled()
    page.get_by_role("button", name="Stop", exact=True).click()
    expect(page.locator("#live")).to_contain_text("State: stopped")
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_disabled()
    with service.catalog.open_attempt(ref.attempt_id) as archive:
        assert any(e.kind == "attempt_finished" for e in archive.entries())


@pytest.mark.parametrize("runtime_browser", ["archive"], indirect=True)
def test_browser_archive_only_all_rows_literal_prose_and_no_world(runtime_browser):
    from playwright.sync_api import expect

    from living_world.archives import AttemptConfig, AttemptLease, JournalEntry

    page, service, _, session, observed, _, _ = runtime_browser
    malicious = "<img src=x onerror=alert(1)>"
    config = AttemptConfig(
        "ollama", "generic", 7, "test", {"provider": {"model": malicious}}
    )
    setup = service.catalog.reserve_setup(config)
    with AttemptLease(setup):
        service.catalog.fail_setup(setup, "model_missing")
    corrupt = service.catalog.reserve(
        AttemptConfig("recorded", "generic", 7, "test", {})
    )
    (corrupt.directory / "archive.sqlite3").write_bytes(b"PRIVATE")
    outcome_ref = service.catalog.reserve(
        AttemptConfig("recorded", "generic", 7, "test", {})
    )
    with (
        AttemptLease(outcome_ref),
        service.catalog.open_attempt(
            outcome_ref.attempt_id, read_only=False
        ) as archive,
    ):
        archive.record(
            tuple(
                JournalEntry(
                    "candidate_aborted", {"base_revision": n, "reason": malicious}
                )
                for n in range(52)
            )
            + (
                JournalEntry(
                    "attempt_finished",
                    {
                        "lifecycle": "failed",
                        "outcome": "service_failed",
                        "last_revision": None,
                    },
                ),
            ),
            lifecycle="failed",
            reason="service_failed",
        )
    login(page, session)
    expect(page.locator("#live")).to_contain_text("No live attempt yet")
    expect(page.locator("#archives")).to_contain_text("service_failed")
    row = page.get_by_role("row").filter(
        has=page.get_by_role("button", name=corrupt.attempt_id, exact=True)
    )
    expect(row).to_contain_text("Unavailable")
    page.get_by_role("button", name=setup.attempt_id, exact=True).click()
    expect(page.locator("#configuration")).to_contain_text(malicious)
    expect(page.locator("#source")).to_contain_text("No committed checkpoint")
    assert page.locator("#configuration img").count() == 0
    page.get_by_role("button", name=outcome_ref.attempt_id, exact=True).click()
    expect(page.locator("#journal")).to_contain_text("Latest 50 entries; total 53")
    expect(page.locator("#journal")).to_contain_text(malicious)
    page.get_by_role("button", name=corrupt.attempt_id, exact=True).click()
    expect(page.locator("#details")).to_have_text("Saved attempt details unavailable.")
    assert not [p for m, p, _ in observed if m == "POST"]


def test_browser_lost_admitted_response_receipt_and_same_id_retry(runtime_browser):
    from playwright.sync_api import expect

    page, service, ref, session, observed, _, _ = runtime_browser
    login(page, session)
    envelopes = []
    hold_receipts = {"hold": True}

    def lose_after_admission(route):
        envelopes.append(route.request.post_data_json)
        if len(envelopes) == 1:
            response = route.fetch()
            assert response.status == 202
            route.abort()
        else:
            route.continue_()

    page.route("**/runtime/commands", lose_after_admission)
    page.route(
        "**/runtime/commands/*",
        lambda route: (
            route.fulfill(status=404, json={"detail": "not_found"})
            if hold_receipts["hold"]
            else route.continue_()
        ),
    )
    page.get_by_role("button", name="Step", exact=True).click()
    expect(
        page.get_by_role("button", name="Retry delivery", exact=True)
    ).to_be_visible()
    expect(page.locator("#live")).to_contain_text("Last committed tick: 1")
    page.wait_for_timeout(1100)
    assert len(envelopes) == 1
    page.get_by_role("button", name="Retry delivery", exact=True).click()
    expect(page.locator("#notice")).to_contain_text("applied")
    assert envelopes[0] == envelopes[1]
    assert service.controller.status().tick == 1
    with service.catalog.open_attempt(ref.attempt_id) as archive:
        assert archive.command(envelopes[0]["command_id"]).status == "applied"
    assert len([p for m, p, _ in observed if m == "POST"]) == 2


def test_browser_delayed_logout_reconnect_and_source_responses(runtime_browser):
    from playwright.sync_api import expect

    page, _, ref, session, _, _, _ = runtime_browser
    login(page, session)
    old = []

    def delayed(route):
        response = route.fetch()
        old.append((route, response))

    page.route("**/runtime/status", delayed)
    deadline = time.monotonic() + 4
    while not old and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert old
    page.get_by_role("button", name="Disconnect", exact=True).click()
    page.unroute("**/runtime/status", delayed)
    login(page, session)
    for route, response in old:
        from contextlib import suppress

        from playwright.sync_api import Error

        with suppress(Error):
            route.fulfill(response=response)
    expect(page.locator("#notice")).to_have_text("Connected.")
    page.route("**/archives/*/checkpoints", delayed)
    old.clear()
    page.get_by_role("button", name=ref.attempt_id, exact=True).click()
    deadline = time.monotonic() + 3
    while not old and time.monotonic() < deadline:
        page.wait_for_timeout(50)
    assert old
    page.get_by_role("button", name="Return to live", exact=True).click()
    for route, response in old:
        route.fulfill(response=response)
    expect(page.locator("#details-panel")).to_be_hidden()
    expect(page.locator("#source")).to_contain_text("Live attempt")
    expect(page.locator("#controls")).to_be_visible()


def test_browser_parent_ready_rejects_foreign_and_extra_messages(runtime_browser):
    from playwright.sync_api import expect

    page, _, _, session, observed, _, _ = runtime_browser

    # Capture the real trusted child HTML response, keeping its script from reporting ready.
    def child_without_ready(route):
        response = route.fetch()
        body = response.text().replace(
            "/inspector/assets/inspector.js", "/unused-child-script"
        )
        route.fulfill(response=response, body=body)

    page.route("**/inspector", child_without_ready)
    login(page, session)
    expect(page.locator("iframe")).to_have_count(1)
    page.wait_for_timeout(150)
    frame = next(f for f in page.frames if f.url == "about:srcdoc")
    frame.evaluate(
        "window.received = []; window.addEventListener('message',e => window.received.push(e.data.type))"
    )
    assert not [p for _, p, _ in observed if p.endswith("/world")]
    page.evaluate("""() => {
      const frame = document.querySelector('iframe');
      for(const e of [
        {origin:window.origin,source:window,data:{type:'living-world-inspector-ready'}},
        {origin:'https://foreign.test',source:frame.contentWindow,data:{type:'living-world-inspector-ready'}},
        {origin:window.origin,source:frame.contentWindow,data:{type:'living-world-inspector-ready',extra:true}}
      ]) window.dispatchEvent(new MessageEvent('message',e));
    }""")
    page.wait_for_timeout(100)
    assert not [p for _, p, _ in observed if p.endswith("/world")]
    assert frame.evaluate("window.received") == []
    page.evaluate(
        "() => window.dispatchEvent(new MessageEvent('message',{origin:window.origin,source:document.querySelector('iframe').contentWindow,data:{type:'living-world-inspector-ready'}}))"
    )
    page.wait_for_timeout(100)
    assert frame.evaluate("window.received") == [
        "living-world-inspector-connect",
        "living-world-inspector-pin",
    ]
    page.evaluate("window.oldFrame = document.querySelector('iframe').contentWindow")
    page.get_by_role("button", name="Return to live", exact=True).click()
    page.wait_for_timeout(150)
    replacement = next(f for f in page.frames if f.url == "about:srcdoc")
    replacement.evaluate(
        "window.received = []; window.addEventListener('message',e => window.received.push(e.data.type))"
    )
    page.evaluate(
        "() => window.dispatchEvent(new MessageEvent('message',{origin:window.origin,source:window.oldFrame,data:{type:'living-world-inspector-ready'}}))"
    )
    page.wait_for_timeout(100)
    assert replacement.evaluate("window.received") == []
    assert session.token not in page.content()


def test_browser_real_version_rejection_and_resume(runtime_browser):
    from playwright.sync_api import expect
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope
    from living_world.runtime import RuntimeState

    page, service, _, session, observed, _, _ = runtime_browser
    login(page, session)
    controller = service.controller
    # Change the operational version between the last displayed status and click.
    service.submit(
        CommandEnvelope("external", "step", controller.status().state_version)
    ).result(3)
    wait_for(controller, lambda s: s.state is RuntimeState.PAUSED and s.tick == 1)
    page.get_by_role("button", name="Step", exact=True).click()
    expect(page.locator("#notice")).to_contain_text("rejected")
    assert controller.status().tick == 1
    expect(page.locator("#live")).to_contain_text("Last committed tick: 1")
    page.get_by_role("button", name="Resume", exact=True).click()
    expect(page.locator("#live")).to_contain_text("State: completed")
    expect(page.get_by_role("button", name="Resume", exact=True)).to_be_disabled()
    assert len([p for m, p, _ in observed if m == "POST"]) == 2


@pytest.mark.parametrize(
    "failure", ["nonce", "version", "prefix", "unsafe_number", "state_array"]
)
def test_browser_malformed_dto_never_becomes_fresh(runtime_browser, failure):
    from playwright.sync_api import expect

    page, _, _, session, _, _, _ = runtime_browser
    login(page, session)

    def malformed(route):
        response = route.fetch()
        body = response.json()
        headers = dict(response.headers)
        if failure == "nonce":
            headers["x-csrf-token"] = "malformed"
        elif failure == "version":
            body["live"]["state_version"] = -1
        elif failure == "prefix":
            body["live"]["inspection_prefix"] = "/live/checkpoints/01"
        elif failure == "state_array":
            body["live"]["state"] = ["paused"]
        else:
            body["live"]["tick"] = 9007199254740992
        route.fulfill(status=200, json=body, headers=headers)

    page.route("**/runtime/status", malformed)
    if failure == "nonce":
        expect(page.locator("#session")).to_be_hidden()
        expect(page.locator("#notice")).to_contain_text("Connection rejected")
    else:
        expect(page.locator("#freshness")).to_contain_text("stale")
        expect(page.get_by_role("button", name="Step", exact=True)).to_be_disabled()


def test_browser_live_pin_preserves_child_filter_focus_and_history_bytes(
    runtime_browser,
):
    from playwright.sync_api import expect

    page, service, ref, session, _, _, _ = runtime_browser
    login(page, session)
    frame = page.frame_locator('iframe[title="World Inspector"]')
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    frame.get_by_role("button", name="History", exact=True).click()
    box = frame.get_by_label("Filter history")
    box.fill("literal selection")
    box.evaluate("e => e.setSelectionRange(2,5)")
    frame_id = page.locator("iframe").evaluate(
        "e => {e.dataset.testIdentity = 'same'; return e.dataset.testIdentity}"
    )
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope
    from living_world.runtime import RuntimeState

    service.submit(
        CommandEnvelope(
            "external-pin", "step", service.controller.status().state_version
        )
    ).result(3)
    wait_for(
        service.controller, lambda s: s.tick == 1 and s.state is RuntimeState.PAUSED
    )
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")
    expect(box).to_have_value("literal selection")
    expect(box).to_be_focused()
    assert box.evaluate("e => [e.selectionStart,e.selectionEnd]") == [2, 5]
    assert page.locator("iframe").get_attribute("data-test-identity") == frame_id
    page.get_by_role("button", name=ref.attempt_id, exact=True).click()
    page.get_by_label("Complete checkpoint").select_option("0")
    expect(frame.locator("#tick")).to_have_text("Reported tick: 0")
    files = [
        p
        for p in ref.directory.rglob("*")
        if p.is_file() and p.name not in {"archive.sqlite3-shm", "archive.sqlite3-wal"}
    ]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
    frame.get_by_role("button", name="Refresh", exact=True).click()
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}


def test_browser_late_receipt_cannot_release_new_same_action(runtime_browser):
    from playwright.sync_api import expect

    page, service, _, session, _, _, _ = runtime_browser
    login(page, session)
    held = []
    count = {"posts": 0}

    def delayed(route):
        count["posts"] += 1
        if count["posts"] == 1:
            route.fetch()
            from test_runtime_service import wait_for

            wait_for(service.controller, lambda s: s.tick == 1)
            # An identical delivery discovers the actual durable applied receipt.
            held.append((route, route.fetch()))
        else:
            route.abort()

    page.route("**/runtime/commands", delayed)
    page.get_by_role("button", name="Step", exact=True).click()
    expect(page.locator("#live")).to_contain_text("Last committed tick: 1")
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_enabled()
    page.get_by_role("button", name="Step", exact=True).click()
    expect(
        page.get_by_role("button", name="Retry delivery", exact=True)
    ).to_be_visible()
    held[0][0].fulfill(response=held[0][1])
    page.wait_for_timeout(200)
    expect(
        page.get_by_role("button", name="Retry delivery", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_disabled()
    assert service.controller.status().tick == 1


def test_archive_rows_show_start_parent_tick_without_selection(runtime_browser):
    from playwright.sync_api import expect

    from living_world.archives import AttemptConfig

    page, service, ref, session, _, _, _ = runtime_browser
    child = service.catalog.reserve(
        AttemptConfig("recorded", "generic", 7, "test", {}), parent=(ref.attempt_id, 0)
    )
    summaries = {s.ref.attempt_id: s for s in service.catalog.attempts()}
    login(page, session)
    live_row = page.get_by_role("row").filter(
        has=page.get_by_role("button", name=ref.attempt_id, exact=True)
    )
    child_row = page.get_by_role("row").filter(
        has=page.get_by_role("button", name=child.attempt_id, exact=True)
    )
    expect(live_row).to_contain_text(summaries[ref.attempt_id].started_at)
    expect(live_row).to_contain_text("None")
    expect(live_row).to_contain_text("Tick 0")
    expect(child_row).to_contain_text(f"{ref.attempt_id}; checkpoint 0")
    expect(child_row).to_contain_text("No checkpoint")
    expect(page.locator("#details-panel")).to_be_hidden()
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator(".overflow").evaluate("e => e.scrollWidth > e.clientWidth")


def test_browser_status_poll_preserves_control_keyboard_focus(runtime_browser):
    from playwright.sync_api import expect

    page, _, _, session, _, _, _ = runtime_browser
    page.get_by_label("Administrator token").fill(session.token)
    page.get_by_label("Administrator token").press("Enter")
    expect(page.locator("#notice")).to_have_text("Connected.")
    button = page.get_by_role("button", name="Step", exact=True)
    button.focus()
    page.wait_for_timeout(1200)
    expect(button).to_be_focused()


@pytest.mark.parametrize(
    "terminal,malformed_from",
    [("applied", "post"), ("rejected", "post"), ("applied", "receipt")],
)
def test_browser_null_terminal_receipt_keeps_original_envelope(
    runtime_browser, terminal, malformed_from
):
    from playwright.sync_api import expect
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope
    from living_world.runtime import RuntimeState

    page, service, _, session, _, base, _ = runtime_browser
    login(page, session)
    controller = service.controller
    if terminal == "rejected":
        # Keep the last genuine status visible while another operator changes it.
        previous = page.request.get(
            base + "/runtime/status",
            headers={"Authorization": "Bearer " + session.token},
        )
        page.route("**/runtime/status", lambda route: route.fulfill(response=previous))
        service.submit(
            CommandEnvelope("outside", "step", controller.status().state_version)
        ).result(3)
        wait_for(controller, lambda s: s.state is RuntimeState.PAUSED and s.tick == 1)
    envelopes = []
    malformed = {"enabled": True}

    def delivery(route):
        envelopes.append(route.request.post_data_json)
        response = route.fetch()
        if malformed["enabled"] and malformed_from == "post":
            if terminal == "applied":
                wait_for(
                    controller, lambda s: s.state is RuntimeState.PAUSED and s.tick == 1
                )
                response = page.request.get(
                    base + "/runtime/commands/" + envelopes[-1]["command_id"],
                    headers={"Authorization": "Bearer " + session.token},
                )
            body = response.json()
            assert body["status"] == terminal
            body["revision"] = None
            route.fulfill(status=200 if terminal == "applied" else 409, json=body)
        else:
            route.fulfill(response=response)

    def receipt(route):
        response = route.fetch()
        body = response.json()
        if malformed["enabled"] and response.status == 200:
            body["revision"] = None
        route.fulfill(response=response, json=body)

    page.route("**/runtime/commands", delivery)
    page.route("**/runtime/commands/*", receipt)
    page.get_by_role("button", name="Step", exact=True).click()
    expect(
        page.get_by_role("button", name="Retry delivery", exact=True)
    ).to_be_visible()
    page.wait_for_timeout(1200)
    expect(page.get_by_role("button", name="Step", exact=True)).to_be_disabled()
    expect(
        page.get_by_role("button", name="Retry delivery", exact=True)
    ).to_be_visible()
    assert len(envelopes) == 1
    malformed["enabled"] = False
    page.get_by_role("button", name="Retry delivery", exact=True).click()
    expect(page.locator("#notice")).to_contain_text(terminal)
    assert envelopes[0] == envelopes[1]
    assert controller.status().tick == 1


@pytest.mark.parametrize("operation", ["select", "refresh"])
def test_browser_shared_detail_limit_selection_refresh_and_cache(
    runtime_browser, operation
):
    from playwright.sync_api import expect

    from living_world.archives import AttemptConfig

    page, service, _, session, _, _, _ = runtime_browser
    for _ in range(3):
        service.catalog.reserve(AttemptConfig("recorded", "generic", 7, "test", {}))
    identities = [s.ref.attempt_id for s in service.catalog.attempts()]
    active = {}
    calls = []
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    peak = {"count": 0}

    def hold(route):
        identity = route.request.url.rsplit("/", 1)[-1]
        calls.append(identity)
        sequence = len(calls)
        active[sequence] = (route, None)
        peak["count"] = max(peak["count"], len(active))
        active[sequence] = (route, route.fetch())

    for identity in identities:
        page.route("**/archives/" + identity, hold)
    login(page, session)
    deadline = time.monotonic() + 3
    while len(active) < 2 and time.monotonic() < deadline:
        page.wait_for_timeout(30)
    assert len(active) == 2
    selected = identities[2]
    if operation == "select":
        page.get_by_role("button", name=selected, exact=True).click()
    else:
        page.get_by_role("button", name="Refresh archives", exact=True).click()
    page.wait_for_timeout(200)
    assert len(active) == 2, "selection/refresh started a third outstanding detail GET"
    assert len(calls) == 2
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        for key in list(active):
            route, response = active[key]
            if response is not None:
                del active[key]
                route.fulfill(response=response)
        page.wait_for_timeout(50)
        if not active and len(calls) >= (4 if operation == "select" else 6):
            break
    assert not active
    assert peak["count"] == 2
    if operation == "refresh":
        page.get_by_role("button", name=selected, exact=True).click()
    expect(page.locator("#details")).to_contain_text(selected)
    count = len(calls)
    page.get_by_role("button", name=selected, exact=True).click()
    expect(page.locator("#details")).to_contain_text(selected)
    page.wait_for_timeout(100)
    assert len(calls) == count
    # A current generation joins selection with its catalog job instead of duplicating it.
    assert calls.count(selected) == 1
    assert errors == []
