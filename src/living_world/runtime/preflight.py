"""Bounded installed-model discovery, with no simulation or catalog access."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import stat
import threading
import time
import unicodedata
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from living_world.archives import ArchiveError, AttemptConfig
from living_world.archives.catalog import (
    SETUP_CODES,
    normalized_digest,
    validate_setup_config,
)
from living_world.perception.local_llm_http import (
    LocalLLMHttpError,
    UrllibJsonHttpTransport,
)

from .broker import (
    ProviderConfig,
    encoded_body,
    provider_config,
    provider_document,
    reap_owned_process,
)


class ProviderPreflightError(Exception):
    """A fixed safe error code, never provider text or transport details."""

    def __init__(self, code: str) -> None:
        if code not in SETUP_CODES:
            raise ValueError("Unknown preflight error.")
        self.code = code
        super().__init__(code)


def _model_name(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or any(c.isspace() or unicodedata.category(c).startswith("C") for c in value)
    ):
        raise ProviderPreflightError("invalid_preflight")
    return value


def _identity(
    config: ProviderConfig, response: Mapping[str, object]
) -> tuple[str, str]:
    models = response.get("models")
    if not isinstance(models, list):
        raise ProviderPreflightError("invalid_preflight")
    entries: dict[str, str] = {}
    for item in models:
        if not isinstance(item, dict):
            raise ProviderPreflightError("invalid_preflight")
        name = _model_name(item.get("name"))
        if name in entries or ("model" in item and item["model"] != name):
            raise ProviderPreflightError("invalid_preflight")
        try:
            entries[name] = normalized_digest(item.get("digest"))
        except (ArchiveError, ValueError):
            raise ProviderPreflightError("invalid_preflight") from None
    candidates = {config.model}
    if ":" not in config.model.rsplit("/", 1)[-1]:
        candidates.add(config.model + ":latest")
    found = candidates & entries.keys()
    if not found:
        raise ProviderPreflightError("model_missing")
    if len(found) != 1:
        raise ProviderPreflightError("invalid_preflight")
    name = found.pop()
    digest = entries[name]
    if config.model_digest is not None:
        try:
            pinned = normalized_digest(config.model_digest)
        except (ArchiveError, ValueError):
            raise ProviderPreflightError("invalid_preflight") from None
        if pinned != digest:
            raise ProviderPreflightError("model_digest_mismatch")
    return name, digest


def _llama_props(config: ProviderConfig, response: Mapping[str, object]) -> Path:
    if response.get("model_alias") != config.model:
        raise ProviderPreflightError("invalid_preflight")
    value = response.get("model_path")
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 4096
        or not Path(value).is_absolute()
        or any(unicodedata.category(c).startswith("C") for c in value)
    ):
        raise ProviderPreflightError("invalid_preflight")
    try:
        expected = Path(config.model_file or "").resolve(strict=True)
    except FileNotFoundError:
        raise ProviderPreflightError("model_missing") from None
    except (OSError, ValueError, RuntimeError):
        raise ProviderPreflightError("invalid_preflight") from None
    try:
        actual = Path(value).resolve(strict=True)
    except (OSError, ValueError, RuntimeError):
        raise ProviderPreflightError("invalid_preflight") from None
    if actual != expected:
        raise ProviderPreflightError("invalid_preflight")
    return actual


def _file_signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _llama_identity(
    config: ProviderConfig, transport: UrllibJsonHttpTransport
) -> tuple[str, str]:
    def get(route: str) -> Mapping[str, object]:
        return transport.get_json(
            url=config.base_url + route, timeout_seconds=config.timeout_seconds
        )

    models = get("/v1/models").get("data")
    if not isinstance(models, list) or any(
        not isinstance(item, dict) for item in models
    ):
        raise ProviderPreflightError("invalid_preflight")
    names = [_model_name(item.get("id")) for item in models]
    if config.model not in names:
        raise ProviderPreflightError("model_missing")
    if names.count(config.model) != 1:
        raise ProviderPreflightError("invalid_preflight")
    props = get("/props")
    path = _llama_props(config, props)
    opened = False
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        opened = True
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or stream.read(4) != b"GGUF":
                raise ProviderPreflightError("invalid_preflight")
            hasher = hashlib.sha256(b"GGUF")
            while block := stream.read(1024 * 1024):
                hasher.update(block)
            after = os.fstat(stream.fileno())
        if (
            _file_signature(before) != _file_signature(after)
            or Path(config.model_file or "").resolve(strict=True) != path
            or _file_signature(path.stat()) != _file_signature(after)
        ):
            raise ProviderPreflightError("invalid_preflight")
    except FileNotFoundError:
        raise ProviderPreflightError(
            "invalid_preflight" if opened else "model_missing"
        ) from None
    except (OSError, ValueError, RuntimeError):
        raise ProviderPreflightError("invalid_preflight") from None
    repeated = get("/props")
    try:
        repeated_path = _llama_props(config, repeated)
        unchanged = _file_signature(path.stat()) == _file_signature(after)
    except (OSError, ProviderPreflightError):
        raise ProviderPreflightError("invalid_preflight") from None
    if (
        not unchanged
        or repeated_path != path
        or repeated.get("model_alias") != props.get("model_alias")
        or repeated.get("model_path") != props.get("model_path")
    ):
        raise ProviderPreflightError("invalid_preflight")
    digest = hasher.hexdigest()
    if config.model_digest is not None and config.model_digest != digest:
        raise ProviderPreflightError("model_digest_mismatch")
    return config.model, digest


def _worker(config: ProviderConfig, result_path: str) -> None:
    try:
        transport = UrllibJsonHttpTransport(config.max_response_bytes)
        if config.kind == "llama_cpp":
            name, digest = _llama_identity(config, transport)
        else:
            response = transport.get_json(
                url=config.base_url + "/api/tags",
                timeout_seconds=config.timeout_seconds,
            )
            name, digest = _identity(config, response)
        result: dict[str, object] = {"model": name, "digest": digest}
    except LocalLLMHttpError as error:
        result = {"error": error.code}
    except ProviderPreflightError as error:
        result = {"error": error.code}
    except Exception:  # noqa: BLE001
        result = {"error": "worker_failed"}
    raw = encoded_body(result).encode()
    if len(raw) > 8192:
        raw = b'{"error":"worker_failed"}'
    path = Path(result_path)
    partial = path.with_suffix(".partial")
    with partial.open("xb") as stream:
        stream.write(raw)
    os.replace(partial, path)


def _read_result(path: Path, config: ProviderConfig) -> ProviderConfig:
    try:
        with path.open("rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            raise ValueError
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise TypeError
        if set(result) == {"error"}:
            code = result["error"]
            if not isinstance(code, str) or code not in SETUP_CODES:
                raise ValueError
            raise ProviderPreflightError(code)
        if set(result) != {"model", "digest"}:
            raise ValueError
        name = _model_name(result["model"])
        digest = normalized_digest(result["digest"])
        if digest != result["digest"]:
            raise ValueError
        # Validate the selected frame independently of the child parser.
        if config.kind == "llama_cpp":
            if name != config.model:
                raise ValueError
            if config.model_digest is not None and config.model_digest != digest:
                raise ProviderPreflightError("model_digest_mismatch")
            checked_name, checked_digest = name, digest
        else:
            checked_name, checked_digest = _identity(
                config, {"models": [{"name": name, "digest": digest}]}
            )
        return replace(config, model=checked_name, model_digest=checked_digest)
    except ProviderPreflightError:
        raise
    except (ArchiveError, OSError, ValueError, TypeError, UnicodeError):
        raise ProviderPreflightError("worker_failed") from None


def preflight_provider(
    requested: AttemptConfig, *, cancel_event: threading.Event | None = None
) -> AttemptConfig:
    """Resolve installed identity under a parent wall deadline and cancellation."""
    if cancel_event is not None and cancel_event.is_set():
        raise ProviderPreflightError("cancelled")
    try:
        config = provider_config(requested)
        _model_name(config.model)
        if config.model_digest is not None:
            checked = normalized_digest(config.model_digest)
            if config.kind == "llama_cpp" and checked != config.model_digest:
                raise ValueError
    except (ArchiveError, ValueError, TypeError, AttributeError):
        raise ProviderPreflightError("invalid_preflight") from None
    deadline = time.monotonic() + config.timeout_seconds
    try:
        with TemporaryDirectory(prefix="living-world-preflight-") as directory:
            path = Path(directory) / "result.json"
            process = multiprocessing.get_context("spawn").Process(
                target=_worker, args=(config, str(path))
            )
            try:
                process.start()
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise ProviderPreflightError("cancelled")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ProviderPreflightError("timeout")
                    if not process.is_alive():
                        if process.exitcode != 0:
                            raise ProviderPreflightError("worker_failed")
                        effective_provider = _read_result(path, config)
                        settings = dict(requested.settings)
                        settings["provider"] = provider_document(effective_provider)
                        effective = replace(requested, settings=settings)
                        validate_setup_config(requested, effective)
                        if time.monotonic() >= deadline:
                            raise ProviderPreflightError("timeout")
                        if cancel_event is not None and cancel_event.is_set():
                            raise ProviderPreflightError("cancelled")
                        return effective
                    process.join(timeout=min(0.02, remaining))
            finally:
                reap_owned_process(process)
    except (ProviderPreflightError, KeyboardInterrupt):
        raise
    except Exception:  # noqa: BLE001
        raise ProviderPreflightError("worker_failed") from None
