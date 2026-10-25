"""Authenticated pinned inspector routes and actual loopback Chrome protocol."""

from pathlib import Path

from test_runtime_operator_api import headers, operator


def test_protected_html_validates_source_and_public_assets(tmp_path: Path) -> None:
    client, service, _controller, ref, session = operator(tmp_path)
    try:
        historical = f"/archives/{ref.attempt_id}/checkpoints/0"
        for prefix, kind in (
            ("/live/checkpoints/00", "live"),
            (historical, "historical"),
        ):
            assert client.request("GET", prefix + "/inspector").status_code == 401
            response = client.request(
                "GET",
                prefix + "/inspector?token=secret&prefix=https://evil.test",
                headers=headers(session),
            )
            assert response.status_code == 200
            html = response.body.decode()
            assert f'data-inspection-prefix="{prefix.replace("/00", "/0")}"' in html
            assert f'data-inspection-kind="{kind}"' in html
            assert "evil.test" not in html and "secret" not in html
            assert session.token not in html and session.csrf_nonce not in html
            assert response.headers["cache-control"] == "no-store"
        for prefix in (
            "/live/checkpoints/-1",
            "/live/checkpoints/999",
            "/archives/bad/checkpoints/0",
        ):
            response = client.request(
                "GET", prefix + "/inspector", headers=headers(session)
            )
            assert response.status_code == 404
        for asset in ("inspector.js", "inspector.css"):
            response = client.request("GET", "/inspector/assets/" + asset)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert session.token.encode() not in response.body
        assert (
            client.request("GET", "/inspector/assets/inspector.html").status_code == 404
        )
        assert client.request("GET", "/inspector").status_code == 404
    finally:
        service.shutdown()


import os
import socket
import threading
import time
from collections.abc import Iterator

import pytest
from fastapi.responses import HTMLResponse
from test_runtime_revision_source import inventory

from living_world.api.auth import AdminSession
from living_world.api.operator import create_operator_app


@pytest.fixture
def embedded(tmp_path: Path) -> Iterator[tuple]:
    import uvicorn

    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent; set LIVING_WORLD_BROWSER_EXECUTABLE")

    from test_runtime_service import reserved

    from living_world.archives import retain_inputs
    from living_world.runtime import RuntimeService

    catalog, config, _unused, _inputs = reserved(tmp_path)
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        scenario.read_text().replace(
            "name: Ada", "name: '<img src=x onerror=alert(1)>'"
        )
    )
    ref = catalog.reserve(config)
    inputs = retain_inputs(ref, scenario, tape_path=None)
    service = RuntimeService(catalog)
    controller = service.start(config, inputs, paused=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        session = AdminSession.issue(origin=base)
        app = create_operator_app(service, controller, auth=session)
        requests = []
        delay = {"prefix": None}
        release = threading.Event()
        entered = threading.Event()

        @app.middleware("http")
        async def observe(request, call_next):
            import asyncio

            path = request.url.path
            if "/world" in path:
                requests.append(
                    (path, request.headers.get("authorization"), request.method)
                )
            response = await call_next(request)
            if (
                delay["prefix"]
                and path.startswith(delay["prefix"])
                and "/world" in path
            ):
                entered.set()
                await asyncio.to_thread(release.wait, 5)
            return response

        @app.get("/test-parent")
        def parent():
            return HTMLResponse(
                '<!doctype html><iframe id="child"></iframe><iframe id="sibling"></iframe>'
            )

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
                    executable_path=executable,
                    headless=True,
                )
                page = browser.new_page()
                page.goto(base + "/test-parent")
                page.evaluate(
                    """() => {window.ready = []; window.addEventListener('message', e => {
                    if(e.origin === window.origin && e.source === document.querySelector('#child').contentWindow && e.data.type === 'living-world-inspector-ready') window.ready.push(e.data);
                });}"""
                )

                def load(prefix="/live/checkpoints/0", transform=None):
                    html = page.request.get(
                        base + prefix + "/inspector",
                        headers={"Authorization": "Bearer " + session.token},
                    ).text()
                    if transform:
                        html = transform(html)
                    page.evaluate(
                        "html => document.querySelector('#child').srcdoc = html", html
                    )
                    page.wait_for_function(
                        "document.querySelector('#child').contentDocument.querySelector('#status')?.textContent.length > 0"
                    )
                    return (
                        page.frames[-1]
                        if page.frames[-1].url == "about:srcdoc"
                        else next(f for f in page.frames if f.url == "about:srcdoc")
                    )

                yield page, load, session, requests, service, ref, delay, entered, release, tmp_path
                release.set()
                browser.close()
        finally:
            release.set()
            server.should_exit = True
            thread.join(8)
            service.shutdown()
            assert not thread.is_alive()


def message(page, value):
    page.evaluate(
        "v => document.querySelector('#child').contentWindow.postMessage(v, window.origin)",
        value,
    )


def connect(page, session):
    message(page, {"type": "living-world-inspector-connect", "token": session.token})


def test_embedded_waits_for_exact_parent_schema_and_clears(embedded):
    from playwright.sync_api import expect

    page, load, session, requests, _service, _ref, delay, entered, release, _root = (
        embedded
    )
    frame = load()
    expect(frame.locator("#status")).to_have_text("Waiting for operator connection.")
    frame.get_by_role("button", name="Entities", exact=True).click()
    page.wait_for_timeout(80)
    assert not requests
    assert page.evaluate("window.ready") == [{"type": "living-world-inspector-ready"}]
    bad = {"type": "living-world-inspector-connect", "token": session.token}
    for value in ({**bad, "extra": True}, {**bad, "token": "short"}, [bad]):
        message(page, value)
    page.evaluate(
        "v => document.querySelector('#sibling').contentWindow.eval('parent.document.querySelector(\"#child\").contentWindow.postMessage(' + JSON.stringify(v) + ', parent.origin)')",
        bad,
    )
    frame.evaluate(
        "v => window.dispatchEvent(new MessageEvent('message', {data:v, origin:'https://foreign.test', source:window.parent}))",
        bad,
    )
    page.wait_for_timeout(80)
    assert not requests
    connect(page, session)
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    assert requests and all(
        auth == "Bearer " + session.token and method == "GET"
        for _, auth, method in requests
    )
    count = len(requests)
    connect(page, session)
    for prefix in (
        "https://evil.test",
        "/live/checkpoints/01",
        "/live/checkpoints/-1",
        "/live/checkpoints/9007199254740992",
        "/live/checkpoints/1?x",
        "/live/checkpoints/1/",
    ):
        message(page, {"type": "living-world-inspector-pin", "prefix": prefix})
    page.wait_for_timeout(80)
    assert len(requests) == count
    assert session.token not in frame.content()
    assert (
        page.evaluate("JSON.stringify([localStorage,sessionStorage,document.cookie])")
        == '[{},{},""]'
    )
    delay["prefix"] = "/live/checkpoints/0"
    frame.get_by_role("button", name="Refresh", exact=True).click()
    assert entered.wait(3)
    message(page, {"type": "living-world-inspector-clear"})
    expect(frame.locator("#records")).to_be_empty()
    expect(frame.locator("#content")).to_have_attribute("aria-busy", "false")
    release.set()
    count = len(requests)
    connect(page, session)
    frame.get_by_role("button", name="History", exact=True).click()
    page.wait_for_timeout(80)
    assert len(requests) == count
    expect(frame.locator("#records")).to_be_empty()


def step(service):
    from test_runtime_service import wait_for

    from living_world.archives import CommandEnvelope
    from living_world.runtime import RuntimeState

    controller = service.controller
    service.submit(
        CommandEnvelope("browser-step", "step", controller.status().state_version)
    ).result(3)
    wait_for(
        controller, lambda state: state.tick == 1 and state.state is RuntimeState.PAUSED
    )


def test_live_pin_coherence_filter_focus_and_navigation_race(embedded):
    from playwright.sync_api import expect

    page, load, session, requests, service, _ref, delay, entered, release, _root = (
        embedded
    )
    frame = load()
    connect(page, session)
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    assert {path for path, _, _ in requests} == {
        "/live/checkpoints/0/world",
        "/live/checkpoints/0/world/run",
        "/live/checkpoints/0/world/replay",
    }
    step(service)
    frame.get_by_role("button", name="History", exact=True).click()
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    filter_box = frame.get_by_label("Filter history")
    filter_box.fill("literal filter")
    filter_box.evaluate("e => e.setSelectionRange(2, 6)")
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/1"}
    )
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")
    expect(filter_box).to_have_value("literal filter")
    expect(filter_box).to_be_focused()
    assert filter_box.evaluate("e => [e.selectionStart,e.selectionEnd]") == [2, 6]
    assert requests[-1][0].startswith("/live/checkpoints/1/")
    delay["prefix"] = "/live/checkpoints/0"
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/0"}
    )
    assert entered.wait(3)
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/1"}
    )
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")
    release.set()
    page.wait_for_timeout(100)
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")
    expect(frame.locator("#content")).to_have_attribute("aria-busy", "false")
    release.clear()
    entered.clear()
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/0"}
    )
    assert entered.wait(3)
    frame.get_by_role("button", name="Entities", exact=True).click()
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/1"}
    )
    expect(frame.locator("#view-title")).to_have_text("Entities")
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    release.set()
    page.wait_for_timeout(80)
    expect(frame.locator("#view-title")).to_have_text("Entities")
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")


@pytest.mark.parametrize(
    "replacement",
    [
        'data-inspection-kind="wrong"',
        "",
    ],
)
def test_invalid_bootstrap_never_fetches(embedded, replacement):
    from playwright.sync_api import expect

    page, load, session, requests, *_ = embedded
    frame = load(
        transform=lambda html: html.replace('data-inspection-kind="live"', replacement)
    )
    connect(page, session)
    frame.get_by_role("button", name="Refresh", exact=True).click()
    page.wait_for_timeout(80)
    assert not requests
    expect(frame.locator("#records")).to_be_empty()
    assert not page.evaluate("window.ready")


def test_historical_fixed_pin_read_only_and_error_recovery(embedded):
    from playwright.sync_api import expect

    page, load, session, requests, service, ref, _delay, _entered, _release, root = (
        embedded
    )
    step(service)
    before = inventory(root)
    frame = load(f"/archives/{ref.attempt_id}/checkpoints/0")
    connect(page, session)
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    count = len(requests)
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/1"}
    )
    page.wait_for_timeout(80)
    assert len(requests) == count
    frame.get_by_role("button", name="Spatial", exact=True).click()
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    expect(frame.locator("#snapshot-source")).to_have_text(
        "Historical checkpoint · revision 0"
    )
    assert all(
        path.startswith(f"/archives/{ref.attempt_id}/checkpoints/0/")
        and method == "GET"
        for path, _, method in requests
    )
    assert inventory(root) == before


def test_live_missing_pin_refresh_recovers(embedded):
    from playwright.sync_api import expect

    page, load, session, _requests, *_ = embedded
    frame = load()
    connect(page, session)
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/999"}
    )
    expect(frame.locator("#status")).to_have_text("Snapshot not found.")
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/0"}
    )
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    frame.get_by_role("button", name="Refresh", exact=True).click()
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")


def test_live_entity_return_target_literal_text_and_focus_choice(embedded):
    from playwright.sync_api import expect

    page, load, session, requests, service, _ref, delay, entered, release, _root = (
        embedded
    )
    frame = load()
    connect(page, session)
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    step(service)
    frame.get_by_role("button", name="Spatial", exact=True).click()
    entity = frame.get_by_role(
        "button", name="<img src=x onerror=alert(1)>", exact=True
    )
    entity.click()
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    back = frame.get_by_role("button", name="Back to Spatial", exact=True)
    back.focus()
    requests.clear()
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/1"}
    )
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")
    expect(back).to_be_focused()
    expect(frame.locator("#view-title")).to_have_text("Entity detail")
    assert len(requests) == 10 and all(
        path.startswith("/live/checkpoints/1/") for path, _, _ in requests
    )
    expect(frame.locator("#content img")).to_have_count(0)
    back.click()
    expect(frame.locator("#view-title")).to_have_text("Spatial")
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    entity.focus()
    delay["prefix"] = "/live/checkpoints/0"
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/0"}
    )
    assert entered.wait(3)
    refresh = frame.get_by_role("button", name="Refresh", exact=True)
    refresh.focus()
    release.set()
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    expect(refresh).to_be_focused()
    page.set_viewport_size({"width": 360, "height": 720})
    refresh.focus()
    page.keyboard.press("Enter")
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    assert frame.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_html_authorization_precedes_archive_access_and_corruption_is_safe(
    tmp_path, monkeypatch
):
    from living_world.api.revision_source import RevisionSource
    from living_world.archives import AttemptConfig

    client, service, _controller, _ref, session = operator(tmp_path)
    original = RevisionSource.open
    calls = []

    def observed(source, attempt_id, revision):
        calls.append((attempt_id, revision, threading.get_ident()))
        return original(source, attempt_id, revision)

    monkeypatch.setattr(RevisionSource, "open", observed)
    try:
        corrupt = service.catalog.reserve(
            AttemptConfig("recorded", "generic", 7, "test", {})
        )
        (corrupt.directory / "archive.sqlite3").write_bytes(b"PRIVATE")
        path = f"/archives/{corrupt.attempt_id}/checkpoints/0/inspector"
        assert client.request("GET", path).status_code == 401
        assert not calls
        response = client.request("GET", path, headers=headers(session))
        assert response.status_code == 409
        assert response.json() == {"detail": "archive_invalid"}
        assert calls and calls[0][2] != threading.get_ident()
        assert "PRIVATE" not in response.body.decode()
        assert response.headers["cache-control"] == "no-store"
    finally:
        service.shutdown()


def test_connection_uses_initial_validated_source_kind(embedded):
    from playwright.sync_api import expect

    page, load, session, _requests, service, *_ = embedded
    frame = load()
    connect(page, session)
    expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
    step(service)
    frame.evaluate("document.documentElement.dataset.inspectionKind = 'historical'")
    message(
        page, {"type": "living-world-inspector-pin", "prefix": "/live/checkpoints/1"}
    )
    expect(frame.locator("#tick")).to_have_text("Reported tick: 1")
    expect(frame.locator("#snapshot-source")).to_have_text(
        "Live checkpoint · revision 1"
    )
