"""One owned spawned process per bounded, filtered provider request."""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import os
import shutil
import time
import unicodedata
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from multiprocessing.process import BaseProcess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, Protocol, cast

from living_world.archives import AttemptConfig
from living_world.archives.model import actions, canonical, validate_request
from living_world.cognition.llama_cpp_cognition_client import LlamaCppCognitionClient
from living_world.cognition.local_llm_cognition_format import (
    parse_decision_response,
    serialize_decision_request,
)
from living_world.cognition.npc_cognition_client import (
    ActionOption,
    NPCCognitionClient,
    NPCCognitionClientError,
    NPCDecision,
)
from living_world.cognition.npc_context import NPCContext
from living_world.cognition.ollama_cognition_client import OllamaCognitionClient
from living_world.cognition.retrieval import RetrievedCognition
from living_world.perception.local_llm_http import (
    HttpObservation,
    LocalLLMHttpError,
    UrllibJsonHttpTransport,
    validate_local_base_url,
)

from .feedback import DecisionInput
from .inference_spool import (
    atomic_publish,
    closed_json,
    create_trace_spool,
    publish_trace_snapshot,
    read_bounded,
    read_trace_snapshot,
    validate_directory,
)
from .inference_trace import (
    InferenceObservation,
    PreparedInference,
    empty_response_trace,
    prepare_inference,
    settle_observation,
    utc_now,
)

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
    kind: Literal["ollama", "llama_cpp"] = "ollama"
    model_file: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("ollama", "llama_cpp"):
            raise ValueError("Unknown provider kind.")
        if self.kind == "ollama" and self.model_file is not None:
            raise ValueError("Ollama does not use a local model file.")
        if self.kind == "llama_cpp" and (
            not isinstance(self.model_file, str)
            or not self.model_file
            or len(self.model_file) > 4096
            or not Path(self.model_file).is_absolute()
            or any(unicodedata.category(c).startswith("C") for c in self.model_file)
        ):
            raise ValueError("Expected an absolute local model path.")
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


def provider_document(config: ProviderConfig) -> dict[str, object]:
    """Canonical provider metadata preserving historical Ollama fingerprints."""
    values = asdict(config)
    if config.kind == "ollama":
        del values["kind"]
        del values["model_file"]
    return values


class PayloadCognitionClient(NPCCognitionClient, Protocol):
    def build_payload(
        self, context: NPCContext, actions: tuple[ActionOption, ...]
    ) -> dict[str, object]: ...


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
) -> PayloadCognitionClient:
    client_type = (
        LlamaCppCognitionClient if config.kind == "llama_cpp" else OllamaCognitionClient
    )
    return client_type(
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
    response_trace: Mapping[str, object] | None = None
    response_body: bytes | None = None

    def __post_init__(self) -> None:
        if self.response_trace is not None:
            observation = InferenceObservation(self.response_trace, self.response_body)
            object.__setattr__(self, "response_trace", observation.response_trace)
        elif self.response_body is not None:
            raise ValueError("Body requires response trace.")
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


def _worker(
    config: ProviderConfig,
    request_json: str,
    result_path: str,
    prepared_body: bytes | None = None,
    metadata_json: str | None = None,
) -> None:
    """Only provider configuration, filtered JSON and owned path cross spawn."""
    worker_started = time.monotonic()
    worker_timestamp = utc_now()
    prepared = (
        None
        if prepared_body is None
        else PreparedInference(prepared_body, json.loads(cast(str, metadata_json)))
    )
    latest: InferenceObservation | None = None
    publication_failed = False

    def capture(http: HttpObservation) -> None:
        nonlocal latest, publication_failed
        trace = empty_response_trace()
        trace.update(
            body_state=(
                "unavailable"
                if http.body is None
                else "complete" if http.complete else "incomplete"
            ),
            body_digest=(
                None if http.body is None else hashlib.sha256(http.body).hexdigest()
            ),
            body_length=None if http.body is None else len(http.body),
            http_status=http.status_code,
        )
        cast(dict[str, object], trace["timestamps"]).update(
            http.timestamps, worker_started_at=worker_timestamp
        )
        cast(dict[str, object], trace["durations"]).update(http.durations)
        latest = InferenceObservation(trace, http.body)
        assert prepared is not None
        try:
            publish_trace_snapshot(Path(result_path).parent, prepared, latest)
        except Exception:
            publication_failed = True
            raise

    class BoundTransport(UrllibJsonHttpTransport):
        def post_json(
            self, *, url: str, payload: dict[str, object], timeout_seconds: float
        ) -> dict[str, object]:
            assert prepared is not None
            if (
                url != prepared.url
                or timeout_seconds != prepared.timeout_seconds
                or payload != json.loads(prepared.body)
            ):
                raise LocalLLMHttpError(
                    "Local LLM capture mismatch.", code="worker_failed"
                )
            return self.post_bytes(
                url=url,
                body=prepared.body,
                timeout_seconds=timeout_seconds,
                observer=capture,
            )

    transport = (UrllibJsonHttpTransport if prepared is None else BoundTransport)(
        config.max_response_bytes
    )
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
    if prepared is not None:
        from living_world.archives.model import plain

        trace = (
            empty_response_trace()
            if latest is None
            else cast(dict[str, object], plain(latest.response_trace))
        )
        cast(dict[str, object], trace["timestamps"])[
            "worker_started_at"
        ] = worker_timestamp
        cast(dict[str, object], trace["durations"])["worker_seconds"] = (
            time.monotonic() - worker_started
        )
        latest = InferenceObservation(trace, None if latest is None else latest.body)
        try:
            publish_trace_snapshot(Path(result_path).parent, prepared, latest)
        except Exception:  # noqa: BLE001 - capture failures must be fail-closed
            publication_failed = True
        if publication_failed:
            decision, code = None, "worker_failed"
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
    if prepared is not None:
        atomic_publish(path.parent, "result.json", raw)
        return
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

    def bind_trace(
        self, job_id: str, prepared: PreparedInference, *, spool_root: Path
    ) -> None:
        # Independent initialization supports injected brokers without super().__init__.
        if not hasattr(self, "_traces"):
            self._traces: dict[str, tuple[PreparedInference, Path]] = {}
            self._trace_validated: set[str] = set()
            self._trace_used: set[str] = set()
            self._trace_corrupt: set[str] = set()
            self._trace_snapshots: dict[str, InferenceObservation | None] = {}
        if (
            not isinstance(prepared, PreparedInference)
            or not isinstance(job_id, str)
            or job_id in self._trace_used
            or job_id in self._traces
            or job_id in getattr(self, "_used", ())
            or getattr(self, "_process", None) is not None
            or any(job not in getattr(self, "_results", {}) for job in self._traces)
        ):
            raise ValueError("Overlapping or reused trace identity.")
        directory = create_trace_spool(spool_root, job_id)
        self._traces[job_id] = (prepared, directory)
        self._trace_used.add(job_id)

    def acknowledge_trace(
        self, job_id: str, *, result: BrokerResult | None = None
    ) -> None:
        traces = getattr(self, "_traces", {})
        cached = getattr(self, "_results", {}).get(job_id)
        if job_id not in traces or (
            result is not None
            and (not isinstance(result, BrokerResult) or result.job_id != job_id)
        ):
            raise ValueError("Trace is not validated and settled.")
        if job_id in getattr(self, "_trace_started", set()):
            if (
                cached is None
                or (result is not None and result != cached)
                or job_id not in self._trace_validated
                or (
                    getattr(self, "_job", None) == job_id
                    and getattr(self, "_process", None) is not None
                )
            ):
                raise ValueError("Trace is not validated and settled.")
        elif type(self).start is DecisionBroker.start or (
            cached is None and result is None
        ):
            raise ValueError("Trace is not validated and settled.")
        prepared, directory = traces[job_id]
        # Revalidate immediately before owned cleanup, including unexpected files.
        snapshot = read_trace_snapshot(directory, prepared)
        if job_id in getattr(
            self, "_trace_started", set()
        ) and snapshot != self._trace_snapshots.get(job_id):
            raise ValueError("Trace changed after settlement.")
        validate_directory(directory)
        if any(
            p.name
            not in {
                "observation.json",
                "observation.partial",
                "result.json",
                "result.partial",
            }
            or p.is_symlink()
            or not p.is_file()
            for p in directory.iterdir()
        ):
            raise ValueError("Trace cleanup failed.")
        shutil.rmtree(directory)
        del traces[job_id]
        self._trace_validated.discard(job_id)
        self._trace_snapshots.pop(job_id, None)

    def _settle_trace(self, result: BrokerResult) -> BrokerResult:
        binding = getattr(self, "_traces", {}).get(result.job_id)
        if binding is None:
            return result
        prepared, directory = binding
        observation = None
        corrupt = result.job_id in self._trace_corrupt
        try:
            observation = read_trace_snapshot(directory, prepared)
            self._trace_validated.add(result.job_id)
        except Exception:  # noqa: BLE001 - capture failures must be fail-closed
            corrupt = True
        if result.decision is not None:
            trace = None if observation is None else observation.response_trace
            if (
                trace is None
                or trace["body_state"] != "complete"
                or trace["body_digest"] != result.response_digest
                or type(trace["http_status"]) is not int
                or not 200 <= cast(int, trace["http_status"]) < 300
            ):
                corrupt = True
        if corrupt:
            self._trace_validated.discard(result.job_id)
        else:
            self._trace_snapshots[result.job_id] = observation
        observation = settle_observation(
            None if corrupt else observation,
            dispatch_started_at=self._dispatch_started_at,
            settled_at=utc_now(),
            broker_seconds=time.monotonic() - self._started,
        )
        return BrokerResult(
            result.job_id,
            None if corrupt else result.decision,
            "worker_failed" if corrupt else result.error_code,
            None if corrupt else result.response_digest,
            time.monotonic() - self._started,
            observation.response_trace,
            observation.body,
        )

    def start(
        self, job_id: str, config: ProviderConfig, decision_input: DecisionInput
    ) -> None:
        if (
            not isinstance(job_id, str)
            or self._process is not None
            or job_id in self._used
            or not job_id.strip()
        ):
            raise ValueError("Overlapping or reused job identity.")
        traces = getattr(self, "_traces", {})
        binding = traces.get(job_id)
        if any(job != job_id and job not in self._results for job in traces):
            raise ValueError("Another trace is awaiting dispatch.")
        if binding is not None:
            expected = prepare_inference(
                config, decision_input.context, decision_input.options
            )
            prepared, _ = binding
            if prepared.body != expected.body or any(
                prepared.request_trace[key] != expected.request_trace[key]
                for key in prepared.request_trace
                if key != "prepared_at"
            ):
                raise ValueError("Prepared inference does not match request.")
        request = serialize_decision_request(
            decision_input.context, decision_input.options
        )
        self._used.add(job_id)
        if binding is not None:
            if not hasattr(self, "_trace_started"):
                self._trace_started: set[str] = set()
            self._trace_started.add(job_id)
        self._job = job_id
        self._options = decision_input.options
        self._started = time.monotonic()
        self._dispatch_started_at = utc_now()
        self._deadline = self._started + config.timeout_seconds
        self._limit = 8 * config.max_response_bytes + 4096
        if binding is None:
            self._directory = TemporaryDirectory(prefix="living-world-provider-")
            result_path = Path(self._directory.name) / "result.json"
            extra: tuple[bytes, str] | tuple[()] = ()
        else:
            prepared, directory = binding
            result_path = directory / "result.json"
            extra = (prepared.body, canonical(prepared.request_trace))
        self._process = multiprocessing.get_context("spawn").Process(
            target=_worker,
            args=(config, request, str(result_path), *extra),
        )
        try:
            self._process.start()
        except Exception:
            self._cleanup()
            self._results[job_id] = self._settle_trace(
                BrokerResult(
                    job_id,
                    None,
                    "worker_failed",
                    None,
                    time.monotonic() - self._started,
                )
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
                binding = getattr(self, "_traces", {}).get(job_id)
                if binding is None:
                    assert self._directory is not None
                    with (Path(self._directory.name) / "result.json").open(
                        "rb"
                    ) as stream:
                        raw = stream.read(self._limit + 1)
                else:
                    raw = read_bounded(binding[1], "result.json", self._limit)
                if len(raw) > self._limit:
                    raise ValueError
                result = closed_json(raw)
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
                binding = getattr(self, "_traces", {}).get(job_id)
                if binding is not None:
                    result_path = binding[1] / "result.json"
                    if result_path.exists() or result_path.is_symlink():
                        self._trace_corrupt.add(job_id)
                decision, code, response_digest = None, "worker_failed", None
        result = BrokerResult(
            job_id, decision, code, response_digest, now - self._started
        )
        self._cleanup()
        result = self._settle_trace(result)
        self._results[job_id] = result
        return result

    def close(self) -> None:
        if self._process is not None and self._job is not None:
            job = self._job
            result = BrokerResult(
                job, None, "cancelled", None, time.monotonic() - self._started
            )
            self._cleanup()
            self._results[job] = self._settle_trace(result)
        else:
            self._cleanup()
