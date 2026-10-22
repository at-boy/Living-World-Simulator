"""Bounded process ownership and configuration regressions."""

import pytest

from living_world.runtime.broker import BrokerResult, DecisionBroker, ProviderConfig


def test_config_and_result_reject_invalid_values() -> None:
    for kwargs in (
        {"timeout_seconds": float("inf")},
        {"max_output_tokens": True},
        {"max_response_bytes": 0},
        {"temperature": float("nan")},
        {"seed": True},
        {"model_digest": ""},
    ):
        with pytest.raises((TypeError, ValueError)):
            ProviderConfig(model="local", **kwargs)
    with pytest.raises(ValueError):
        BrokerResult("job", None, None, None, 0.0)
    broker = DecisionBroker()
    broker.close()
    broker.close()
    with pytest.raises(ValueError):
        broker.poll("unknown")


def test_real_spawn_success_timeout_cleanup_and_restart() -> None:
    import json
    import multiprocessing
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from living_world.cognition.npc_context import NPCContext
    from living_world.runtime.feedback import DecisionInput

    class Handler(BaseHTTPRequestHandler):
        slow = False
        speech = "I will watch." + "\\" * 100000

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            if Handler.slow:
                time.sleep(5)
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(
                    json.dumps(
                        {
                            "response": json.dumps(
                                {"spoken_text": Handler.speech, "action_request": None}
                            )
                        }
                    ).encode()
                )
            except BrokenPipeError:
                pass

        def log_message(self, format: str, *args: object) -> None:
            pass

    before = {p.pid for p in multiprocessing.active_children()}
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        decision_input = DecisionInput(
            "entity_private",
            "founder",
            NPCContext("Erik", (), (), (), ()),
            (),
            (),
            "a" * 64,
        )
        broker = DecisionBroker()
        broker.start(
            "first",
            ProviderConfig(model="local", base_url=base, timeout_seconds=5),
            decision_input,
        )
        with pytest.raises(ValueError):
            broker.start("overlap", ProviderConfig(model="local"), decision_input)
        limit = time.monotonic() + 6
        result = None
        while result is None and time.monotonic() < limit:
            result = broker.poll("first")
            time.sleep(0.01)
        assert result is not None and result.decision is not None
        assert result.decision.spoken_text == Handler.speech
        assert result.response_digest is not None
        broker.close()
        Handler.slow = True
        broker.start(
            "second",
            ProviderConfig(model="local", base_url=base, timeout_seconds=1.0),
            decision_input,
        )
        result = None
        limit = time.monotonic() + 3
        while result is None and time.monotonic() < limit:
            result = broker.poll("second")
            time.sleep(0.01)
        assert result is not None and result.error_code == "timeout"
        broker.start(
            "third", ProviderConfig(model="local", base_url=base), decision_input
        )
        broker.close()
        assert broker.poll("third").error_code == "cancelled"
        assert {p.pid for p in multiprocessing.active_children()} == before
        server.shutdown()
        thread.join(timeout=2)
