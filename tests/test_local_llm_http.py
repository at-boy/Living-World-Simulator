import pytest

from living_world.perception.local_llm_http import (
    LocalLLMHttpError,
    validate_local_base_url,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://127.0.0.1:11434/", "http://127.0.0.1:11434"),
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://[::1]:8080/", "http://[::1]:8080"),
    ],
)
def test_validate_local_base_url_accepts_loopback_urls(
    url: str,
    expected: str,
) -> None:
    assert validate_local_base_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://ollama.com",
        "http://192.168.1.10:11434",
        "http://example.com",
        "not-a-url",
    ],
)
def test_validate_local_base_url_rejects_non_local_urls(url: str) -> None:
    with pytest.raises(ValueError, match="loopback HTTP URL"):
        validate_local_base_url(url)


def test_http_error_message_does_not_include_response_body() -> None:
    error = LocalLLMHttpError("Local LLM server returned HTTP 500.")

    assert str(error) == "Local LLM server returned HTTP 500."


@pytest.mark.parametrize(
    "url",
    [
        "http://user@localhost:80",
        "http://localhost:bad",
        "http://localhost:99999",
        "http://local\nhost:80",
        "http:// localhost:80",
        "http://[::1",
        "http://[::1]junk",
    ],
)
def test_rejects_malformed_or_credentialled_loopback(url: str) -> None:
    with pytest.raises(ValueError):
        validate_local_base_url(url)


def test_bounded_transport_exposes_digest_and_classified_error() -> None:
    from living_world.perception.local_llm_http import UrllibJsonHttpTransport

    transport = UrllibJsonHttpTransport(max_response_bytes=32)
    assert transport.last_response_digest is None
    assert LocalLLMHttpError("safe", code="timeout").code == "timeout"


def test_actual_loopback_http_bounds_redirect_encoding_timeout_and_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from living_world.perception.local_llm_http import UrllibJsonHttpTransport

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://example.com/")
                self.end_headers()
                return
            if self.path == "/error":
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"private error body")
                return
            if self.path == "/slow":
                time.sleep(0.2)
            raw = {"/huge": b"x" * 100, "/invalid": b"\xff", "/badjson": b"no"}.get(
                self.path, b'{"ok":true}'
            )
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(raw)
            except BrokenPipeError:
                pass

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
        monkeypatch.setenv("no_proxy", "")
        transport = UrllibJsonHttpTransport(max_response_bytes=32)
        assert transport.post_json(url=base + "/ok", payload={}, timeout_seconds=1) == {
            "ok": True
        }
        assert (
            transport.last_response_digest == hashlib.sha256(b'{"ok":true}').hexdigest()
        )
        for path, code in [
            ("/redirect", "http_error"),
            ("/error", "http_error"),
            ("/huge", "oversized_response"),
            ("/invalid", "invalid_response"),
            ("/badjson", "invalid_response"),
            ("/slow", "timeout"),
        ]:
            with pytest.raises(LocalLLMHttpError) as caught:
                transport.post_json(url=base + path, payload={}, timeout_seconds=0.05)
            assert caught.value.code == code
            assert "private" not in str(caught.value)
            if path in {"/huge", "/redirect", "/error", "/slow"}:
                assert transport.last_response_digest is None
        server.shutdown()
        thread.join(timeout=2)
