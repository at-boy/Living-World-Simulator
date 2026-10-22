"""One owned spawned process per bounded, filtered provider request."""

from __future__ import annotations

import json
import math
import multiprocessing
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from multiprocessing.process import BaseProcess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from living_world.archives import AttemptConfig
from living_world.archives.model import actions, canonical, validate_request
from living_world.cognition.local_llm_cognition_format import (
    parse_decision_response,
    serialize_decision_request,
)
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClientError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
from living_world.cognition.retrieval import RetrievedCognition
from living_world.perception.local_llm_http import (
    LocalLLMHttpError,
    UrllibJsonHttpTransport,
    validate_local_base_url,
)

from .feedback import DecisionInput

ERROR_CODES = frozenset(
    {
        "timeout",
        "transport",
        "http_error",
        "invalid_response",
        "oversized_response",
        "unsafe_response",
        "cancelled",
        "worker_failed",
        "uncertain",
    }
)


@dataclass(frozen=True)
class ProviderConfig:
    model: str
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 30.0
    max_output_tokens: int = 512
    max_response_bytes: int = 1048576
    temperature: float = 0.0
    seed: int | None = None
    model_digest: str | None = None

    def __post_init__(self) -> None:
        OllamaCognitionClient(
            model=self.model,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            max_output_tokens=self.max_output_tokens,
            temperature=self.temperature,
            seed=self.seed,
        )
        if type(self.max_response_bytes) is not int or self.max_response_bytes <= 0:
            raise ValueError("Response limit must be positive.")
        if self.model_digest is not None and (
            not isinstance(self.model_digest, str) or not self.model_digest.strip()
        ):
            raise ValueError("Declared model digest must be nonempty.")
        object.__setattr__(self, "base_url", validate_local_base_url(self.base_url))
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(self, "temperature", float(self.temperature))


def provider_config(config: AttemptConfig) -> ProviderConfig:
    if config.mode != "ollama" or config.settings.get("driver_format", 1) != 1:
        raise ValueError("Expected supported Ollama configuration.")
    limits = cast(Mapping[str, object], config.settings.get("limits", {}))
    for key, expected in (
        ("max_perceptions", 8),
        ("max_memories", 8),
        ("max_request_characters", 16000),
    ):
        if limits.get(key, expected) != expected:
            raise ValueError("Feedback limits are fixed.")
    maximum = limits.get("max_requests", 40)
    if type(maximum) is not int or maximum <= 0:
        raise ValueError("Request budget must be positive.")
    values = dict(cast(Mapping[str, object], config.settings.get("provider", {})))
    values.setdefault("seed", config.seed)
    return ProviderConfig(**values)  # type: ignore[arg-type]


def client_for(
    config: ProviderConfig, transport: UrllibJsonHttpTransport | None = None
) -> OllamaCognitionClient:
    return OllamaCognitionClient(
        model=config.model,
        base_url=config.base_url,
        timeout_seconds=config.timeout_seconds,
        max_output_tokens=config.max_output_tokens,
        temperature=config.temperature,
        seed=config.seed,
        transport=transport,
    )


def encoded_body(payload: Mapping[str, object]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def decision_document(decision: NPCDecision) -> dict[str, object]:
    request = decision.action_request
    return {
        "spoken_text": decision.spoken_text,
        "action_request": (
            None
            if request is None
            else {
                "action_key": request.action_key,
                "target_label": request.target_label,
                "rationale": request.rationale,
                "arguments": dict(request.arguments),
            }
        ),
    }


def _safe_input(request_json: str) -> tuple[NPCContext, tuple[ActionOption, ...]]:
    request = json.loads(request_json)
    validate_request(request)
    context = NPCContext(
        request["identity"],
        tuple(request["self_knowledge"]),
        tuple(request["current_perceptions"]),
        tuple(RetrievedCognition(**item) for item in request["core_cognition"]),
        tuple(RetrievedCognition(**item) for item in request["retrieved_information"]),
        tuple(request["conversation_history"]),
    )
    return context, actions(request)


@dataclass(frozen=True)
class BrokerResult:
    job_id: str
    decision: NPCDecision | None
    error_code: str | None
    response_digest: str | None
    elapsed_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, str) or not self.job_id.strip():
            raise ValueError("Expected job identity.")
        if (self.decision is None) == (self.error_code is None):
            raise ValueError("Expected decision or error.")
        if self.decision is not None and not isinstance(self.decision, NPCDecision):
            raise TypeError("Expected parsed decision.")
        if self.error_code is not None and self.error_code not in ERROR_CODES:
            raise ValueError("Unknown provider error.")
        if self.response_digest is not None:
            from living_world.archives.model import digest

            digest(self.response_digest)
        if (
            type(self.elapsed_seconds) not in (int, float)
            or not math.isfinite(self.elapsed_seconds)
            or self.elapsed_seconds < 0
        ):
            raise ValueError("Expected finite elapsed time.")


def _worker(config: ProviderConfig, request_json: str, result_path: str) -> None:
    """Only provider configuration, filtered JSON and owned path cross spawn."""
    transport = UrllibJsonHttpTransport(config.max_response_bytes)
    decision: NPCDecision | None = None
    code: str | None = None
    try:
        context, offered = _safe_input(request_json)
        client = client_for(config, transport)
        if len(encoded_body(client.build_payload(context, offered))) > 16000:
            code = "invalid_response"
        else:
            decision = client.decide(context, offered)
    except NPCCognitionClientError as error:
        cause = error.__cause__
        code = (
            cause.code if isinstance(cause, LocalLLMHttpError) else "invalid_response"
        )
    except Exception:  # noqa: BLE001
        code = "worker_failed"
    result = {
        "decision": None if decision is None else decision_document(decision),
        "error_code": code,
        "response_digest": transport.last_response_digest,
    }
    raw = encoded_body(result).encode()
    if len(raw) > 8 * config.max_response_bytes + 4096:
        raw = encoded_body(
            {"decision": None, "error_code": "worker_failed", "response_digest": None}
        ).encode()
    path = Path(result_path)
    partial = path.with_suffix(".partial")
    with partial.open("xb") as stream:
        stream.write(raw)
    os.replace(partial, path)


def reap_owned_process(process: BaseProcess) -> None:
    """Reap only a process created and owned by the calling component."""
    if process.pid is not None:
        if process.is_alive():
            process.terminate()
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)
        process.close()


class DecisionBroker:
    """Restartable ownership with no framed blocking IPC or persistent worker."""

    def __init__(self) -> None:
        self._process: BaseProcess | None = None
        self._directory: TemporaryDirectory[str] | None = None
        self._job: str | None = None
        self._used: set[str] = set()
        self._results: dict[str, BrokerResult] = {}
        self._started = 0.0
        self._deadline = 0.0
        self._limit = 0
        self._options: tuple[ActionOption, ...] = ()

    def start(
        self, job_id: str, config: ProviderConfig, decision_input: DecisionInput
    ) -> None:
        if (
            self._process is not None
            or job_id in self._used
            or not isinstance(job_id, str)
            or not job_id.strip()
        ):
            raise ValueError("Overlapping or reused job identity.")
        request = serialize_decision_request(
            decision_input.context, decision_input.options
        )
        self._used.add(job_id)
        self._job = job_id
        self._options = decision_input.options
        self._started = time.monotonic()
        self._deadline = self._started + config.timeout_seconds
        self._limit = 8 * config.max_response_bytes + 4096
        self._directory = TemporaryDirectory(prefix="living-world-provider-")
        self._process = multiprocessing.get_context("spawn").Process(
            target=_worker,
            args=(config, request, str(Path(self._directory.name) / "result.json")),
        )
        try:
            self._process.start()
        except Exception:
            self._cleanup()
            self._results[job_id] = BrokerResult(
                job_id, None, "worker_failed", None, time.monotonic() - self._started
            )
            raise

    def _cleanup(self) -> None:
        process = self._process
        if process is not None:
            reap_owned_process(process)
            self._process = None
        if self._directory is not None:
            self._directory.cleanup()
            self._directory = None
        self._options = ()

    def poll(self, job_id: str) -> BrokerResult | None:
        if job_id not in self._used:
            raise ValueError("Unknown job identity.")
        if job_id in self._results:
            return self._results[job_id]
        if job_id != self._job or self._process is None:
            raise ValueError("Unknown active job identity.")
        now = time.monotonic()
        decision: NPCDecision | None = None
        code: str | None = None
        response_digest: str | None = None
        if now >= self._deadline:
            code = "timeout"
        elif self._process.is_alive():
            return None
        else:
            try:
                assert self._directory is not None
                with (Path(self._directory.name) / "result.json").open("rb") as stream:
                    raw = stream.read(self._limit + 1)
                if len(raw) > self._limit:
                    raise ValueError
                result = json.loads(raw)
                if set(result) != {"decision", "error_code", "response_digest"}:
                    raise ValueError
                code, response_digest = result["error_code"], result["response_digest"]
                if result["decision"] is not None:
                    decision = parse_decision_response(
                        canonical(result["decision"]), self._options
                    )
                BrokerResult(
                    job_id, decision, code, response_digest, now - self._started
                )
            except Exception:  # noqa: BLE001
                decision, code, response_digest = None, "worker_failed", None
        result = BrokerResult(
            job_id, decision, code, response_digest, now - self._started
        )
        self._cleanup()
        self._results[job_id] = result
        return result

    def close(self) -> None:
        if self._process is not None and self._job is not None:
            self._results[self._job] = BrokerResult(
                self._job, None, "cancelled", None, time.monotonic() - self._started
            )
        self._cleanup()
