"""Model-free live broker/archive demonstration, followed by offline replay."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from manual.local_founders_runtime import run_experiment

from living_world.archives import RunCatalog
from living_world.cli import build_parser


@contextmanager
def synthetic_ollama_provider() -> Iterator[str]:
    """Own a synthetic no-action HTTP fixture; this is never native evidence."""

    class Handler(BaseHTTPRequestHandler):
        def reply(self, body: dict[str, object]) -> None:
            encoded = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self) -> None:
            if self.path != "/api/tags":
                self.send_error(404)
                return
            self.reply({"models": [{"name": "synthetic:latest", "digest": "a" * 64}]})

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            if self.path != "/api/generate":
                self.send_error(404)
                return
            self.reply(
                {
                    "response": json.dumps(
                        {"spoken_text": "I will wait.", "action_request": None}
                    )
                }
            )

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = Thread(
        target=server.serve_forever, name="synthetic-ollama-http", daemon=False
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def fresh_options(root: Path, url: str) -> list[str]:
    return [
        "run",
        "--preset",
        "founders",
        "--driver",
        "ollama",
        "--model",
        "synthetic",
        "--base-url",
        url,
        "--request-contract",
        "founders_empty_arguments_v1",
        "--archive-root",
        str(root),
        "--max-requests",
        "30",
        "--max-ticks",
        "10",
        "--timeout-seconds",
        "5",
    ]


def source_files(directory: Path) -> dict[Path, tuple[bytes, int]]:
    return {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in directory.rglob("*")
        if p.is_file()
    }


def main() -> None:
    with TemporaryDirectory(prefix="living-world-synthetic-") as temporary:
        root = Path(temporary)
        with synthetic_ollama_provider() as url:
            result = run_experiment(
                build_parser().parse_args(fresh_options(root, url)),
                steps=3,
                timeout_seconds=20,
            )
        assert (
            result.exit_code == 0
            and result.steps_completed == 3
            and result.end_tick == 3
        )
        catalog = RunCatalog(root)
        assert result.attempt_id is not None
        with catalog.open_attempt(result.attempt_id) as source:
            checkpoints = [source.checkpoint(i) for i in range(4)]
            kinds = [entry.kind for entry in source.entries()]
            assert "request_started" in kinds and "response_validated" in kinds
            digests = tuple(
                dict.fromkeys(
                    entry.payload[field]["body_digest"]
                    for entry in source.entries()
                    for field in ("request_trace", "response_trace")
                    if field in entry.payload
                    and entry.payload[field]["body_digest"] is not None
                )
            )
            assert digests and all(
                blob.body for blob in source.inference_blobs(digests)
            )
            directory = source.ref.directory
        before = source_files(directory)
        replay = run_experiment(
            build_parser().parse_args(
                [
                    "run",
                    "--replay-attempt",
                    result.attempt_id,
                    "--archive-root",
                    str(root),
                ]
            ),
            steps=3,
            timeout_seconds=20,
        )
        assert replay.exit_code == 0 and replay.steps_completed == 3
        assert replay.attempt_id is not None
        with catalog.open_attempt(replay.attempt_id) as child:
            for revision, expected in enumerate(checkpoints):
                actual = child.checkpoint(revision)
                assert actual.snapshot == expected.snapshot
                assert actual.feedback_cursor == expected.feedback_cursor
                assert actual.driver_cursor == expected.driver_cursor
        assert before == source_files(directory)
    print(
        "PASS: synthetic HTTP broker committed 3 ticks; exact world/feedback replay ran offline (not native acceptance)."
    )


if __name__ == "__main__":
    main()
