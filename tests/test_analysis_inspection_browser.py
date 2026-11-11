"""Real HTTP/Chrome historical checkpoint embedding and stale-session safety."""

import os
import socket
import threading
import time
from pathlib import Path

import pytest
from test_runtime_revision_source import archive_world, inventory
from test_trace_browser import connect, release_held, wait_held

from living_world.api.auth import AdminSession
from living_world.api.trace_analysis import create_analysis_app
from living_world.archives import AttemptLease


@pytest.fixture
def historical(tmp_path):
    import uvicorn
    from test_trace_analysis_reader import fail, start

    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent")
    catalog, ref, _ = archive_world(tmp_path)
    with (
        AttemptLease(ref),
        catalog.open_attempt(ref.attempt_id, read_only=False) as archive,
    ):
        start(archive)
        fail(archive, b"saved")
    before = inventory(catalog.root)
    observed, errors = [], []
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        auth = AdminSession.issue(origin=base)
        app = create_analysis_app(catalog, auth=auth)

        @app.middleware("http")
        async def observe(req, call_next):
            observed.append((str(req.url), req.headers.get("authorization")))
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
                    page = browser.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "/analysis")
                    yield page, auth, ref, observed
                    assert not errors
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(8)
            assert not thread.is_alive()
    assert inventory(catalog.root) == before


def select(page, auth, ref):
    connect(page, auth)
    page.get_by_role("button", name=ref.attempt_id, exact=True).click()


def test_explicit_checkpoints_and_trace_survives_failure(historical):
    from playwright.sync_api import expect

    page, auth, ref, observed = historical
    select(page, auth, ref)
    expect(page.locator("#world-section")).to_be_visible()
    assert not [url for url, _ in observed if "/checkpoints/" in url]
    for revision in (0, 1):
        page.get_by_label("Checkpoint revision").fill(str(revision))
        page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
        frame = page.frame_locator('iframe[title="Saved World Inspector"]')
        expect(frame.locator("#status")).to_have_text("Snapshots loaded.")
        expect(frame.locator("body")).to_contain_text(
            f"Historical checkpoint · revision {revision}"
        )
        expect(
            frame.locator("#records").get_by_role(
                "row", name=f"tick {revision}", exact=True
            )
        ).to_be_visible()
        frame.get_by_role("button", name="Entities", exact=True).click()
        expect(frame.locator("#records")).to_contain_text("Ada")
    page.get_by_role("button", name="req", exact=True).click()
    page.get_by_role("button", name="Preview response", exact=True).click()
    expect(page.locator("#preview")).to_have_text("saved")
    page.locator("#world-revision").fill("99")
    expect(page.locator("#world-preview iframe")).to_have_count(0)
    page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
    expect(page.locator("#world-status")).to_contain_text("unavailable")
    expect(page.locator("#preview")).to_have_text("saved")
    assert auth.token not in page.content()
    assert all(auth.token not in url for url, _ in observed)
    assert (
        page.evaluate("JSON.stringify([localStorage,sessionStorage,document.cookie])")
        == '[{},{},""]'
    )


@pytest.mark.parametrize("value", ["-1", "1.5", "9007199254740992", ""])
def test_invalid_local_revision_never_fetches(historical, value):
    from playwright.sync_api import expect

    page, auth, ref, observed = historical
    select(page, auth, ref)
    page.locator("#world-revision").fill(value)
    page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
    expect(page.locator("#world-status")).to_contain_text("valid")
    assert not [url for url, _ in observed if "/checkpoints/" in url]


@pytest.mark.parametrize(
    "operation", ["revision", "attempt", "refresh", "disconnect", "reconnect"]
)
def test_late_html_cannot_restore_frame(historical, operation):
    from playwright.sync_api import expect

    page, auth, ref, _ = historical
    select(page, auth, ref)
    held = []

    def hold(route):
        held.append((route, route.fetch()))

    page.route("**/checkpoints/*/inspector", hold)
    try:
        page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
        wait_held(page, held)
        if operation == "revision":
            page.locator("#world-revision").fill("1")
        elif operation == "attempt":
            page.get_by_role("button", name=ref.attempt_id, exact=True).click()
        elif operation == "refresh":
            page.get_by_role("button", name="Refresh calls", exact=True).click()
        else:
            page.get_by_role("button", name="Disconnect", exact=True).click()
            if operation == "reconnect":
                connect(page, auth)
        release_held(held, status=401 if operation == "reconnect" else 200)
        page.wait_for_timeout(100)
        expect(page.locator("#world-preview iframe")).to_have_count(0)
        if operation == "reconnect":
            expect(page.locator("#notice")).to_have_text("Connected.")
    finally:
        release_held(held)


def test_ready_handshake_rejects_wrong_schema_origin_source_and_old_frame(historical):
    from playwright.sync_api import expect

    page, auth, ref, _ = historical
    select(page, auth, ref)
    held = []

    def hold(route):
        held.append((route, route.fetch()))

    page.route("**/inspector/assets/inspector.js", hold)
    try:
        page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
        wait_held(page, held)
        page.evaluate("""() => {
          window.testFrame = document.querySelector("#world-preview iframe").contentWindow;
          window.testSent = [];
          testFrame.postMessage = (...args) => testSent.push(args);
          window.sendReady = (data, origin = window.origin, source = testFrame) =>
            window.dispatchEvent(new MessageEvent("message", {data, origin, source}));
          sendReady({type:"living-world-inspector-ready",extra:true});
          sendReady({type:"living-world-inspector-ready"}, "https://evil.invalid");
          sendReady({type:"living-world-inspector-ready"}, window.origin, window);
          sendReady([]);
        }""")
        assert page.evaluate("testSent.length") == 0
        page.evaluate('sendReady({type:"living-world-inspector-ready"})')
        assert page.evaluate("testSent") == [
            [
                {"type": "living-world-inspector-connect", "token": auth.token},
                page.url.split("/analysis")[0],
            ]
        ]
        page.evaluate('sendReady({type:"living-world-inspector-ready"})')
        assert page.evaluate("testSent.length") == 1
        page.locator("#world-revision").fill("1")
        expect(page.locator("#world-preview iframe")).to_have_count(0)
        page.unroute("**/inspector/assets/inspector.js", hold)
        release_held(held)
        page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
        expect(
            page.frame_locator('iframe[title="Saved World Inspector"]').locator(
                "#status"
            )
        ).to_have_text("Snapshots loaded.")
        count = page.evaluate("testSent.length")
        page.evaluate('sendReady({type:"living-world-inspector-ready"})')
        assert page.evaluate("testSent.length") == count
    finally:
        release_held(held)


def test_auth_rejection_clears_loaded_world(historical):
    from playwright.sync_api import expect

    page, auth, ref, _ = historical
    select(page, auth, ref)
    page.get_by_role("button", name="Inspect checkpoint", exact=True).click()
    expect(page.locator("#world-preview iframe")).to_have_count(1)
    page.route("**/analysis/attempts?*", lambda route: route.fulfill(status=401))
    page.get_by_role("button", name="Refresh attempts", exact=True).click()
    expect(page.locator("#world-preview iframe")).to_have_count(0)
    expect(page.locator("#world-section")).to_be_hidden()
    expect(page.locator("#notice")).to_contain_text("Connection rejected")


# Reuse the existing real live/offline server fixture; the live UI must never
# offer the offline-only entry point even though operator historical routes exist.
from test_trace_browser import trace_browser  # noqa: F401


def test_controls_only_offline(trace_browser):  # noqa: F811 - imported pytest fixture
    from playwright.sync_api import expect

    page, auth, archive, _, _, _, observed, mode = trace_browser
    select(page, auth, archive.ref)
    if mode == "live":
        expect(page.locator("#world-section")).to_be_hidden()
    else:
        expect(page.locator("#world-section")).to_be_visible()
    assert not [url for _, url, _ in observed if "/checkpoints/" in url]
