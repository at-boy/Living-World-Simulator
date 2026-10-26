"""CLI composition around the single-owner archived runtime service."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field, replace
from threading import Event, Lock, Thread
from typing import Literal, cast

from living_world import __version__
from living_world.archives import (
    ArchiveError,
    ArchiveReservationError,
    AttemptConfig,
    AttemptLease,
    AttemptRef,
    RunCatalog,
    load_retained_inputs,
    retain_inputs,
)
from living_world.archives.catalog import SETUP_CODES
from living_world.archives.model import (
    BoundaryDisturbance,
    identifier,
    parse_boundary_disturbance,
)
from living_world.founders import FoundersOutcome, materialize_founders_assets
from living_world.repositories.world_snapshot import decode_world, encode_world
from living_world.running import StopControl
from living_world.scenarios.scenario import YAMLScenarioLoader
from living_world.simulation.simulation_engine import SimulationEngine

from .broker import ERROR_CODES, ProviderConfig, provider_config
from .contracts import RuntimeState
from .controller import RunController
from .launch import RuntimeStartupError
from .legacy import LegacyArchiveSession
from .recorded import SnapshotRepository
from .service import RuntimeService

_PROVIDER_FLAGS = (
    "driver",
    "model",
    "base_url",
    "timeout_seconds",
    "max_output_tokens",
    "max_requests",
)
_CONFIG_FLAGS = (*_PROVIDER_FLAGS, "max_ticks", "continuous", "save_every")


@dataclass(frozen=True)
class ArchivedRunResult:
    scenario_key: str
    start_tick: int
    end_tick: int
    resumed: bool
    stop_reason: str
    terminal_condition: str | None
    proposals_finalized: bool | None


class RuntimeCLIError(RuntimeError):
    def __init__(
        self, exit_code: int, reason: str, ref: AttemptRef | None = None
    ) -> None:
        if exit_code not in (2, 3, 4, 5, 6) or reason not in (
            SETUP_CODES
            | ERROR_CODES
            | {
                "invalid_configuration",
                "incompatible_save",
                "archive_failed",
                "mirror_failed",
                "initialization_failed",
                "service_failed",
                "service_closed",
                "service_not_ready",
                "tick_failed",
                "audit_failed",
                "shutdown_failed",
            }
        ):
            raise ValueError("Invalid CLI failure.")
        self.exit_code, self.reason, self.ref = exit_code, reason, ref
        super().__init__(reason)


def _provided(arguments: argparse.Namespace, names: tuple[str, ...]) -> bool:
    return any(getattr(arguments, name, None) is not None for name in names)


def validate_archived_options(
    a: argparse.Namespace, parser: argparse.ArgumentParser
) -> bool:
    """Reject ambiguous/ignored flags before catalog allocation or provider IO."""

    def reject() -> None:
        parser.error("invalid_configuration: incompatible or missing target/options")

    if a.command == "inspect":
        archived = a.attempt is not None
        if sum(bool(v) for v in (a.scenario, a.founders, a.attempt)) != 1:
            reject()
        if archived:
            if a.database is not None:
                reject()
        elif (
            a.database is None or a.checkpoint is not None or a.archive_root is not None
        ):
            reject()
        target = a.attempt
    else:
        archived = a.command == "serve" or any(
            (a.preset, a.resume_attempt, a.fork_attempt, a.replay_attempt)
        )
        if (
            sum(
                bool(v)
                for v in (
                    a.scenario,
                    a.founders,
                    a.preset,
                    a.resume_attempt,
                    a.fork_attempt,
                    a.replay_attempt,
                )
            )
            != 1
        ):
            reject()
        target = a.resume_attempt or a.fork_attempt or a.replay_attempt
        if a.command == "serve":
            if a.founders and _provided(a, _PROVIDER_FLAGS):
                reject()
            if a.checkpoint is not None and not (a.resume_attempt or a.fork_attempt):
                reject()
            if a.checkpoint_only and not a.founders:
                reject()
        if archived:
            if a.proposal_tape is not None or (
                a.checkpoint_only and a.command != "serve"
            ):
                reject()
            if a.preset and (
                a.driver != "ollama" or not a.model or a.checkpoint is not None
            ):
                reject()
            if a.replay_attempt and _provided(a, _CONFIG_FLAGS):
                reject()
            if a.preset and a.max_ticks == 0:
                reject()
        elif _provided(a, _PROVIDER_FLAGS) or a.checkpoint is not None:
            reject()
        if a.founders and a.proposal_tape:
            reject()
        try:
            if _provided(
                a, ("model", "base_url", "timeout_seconds", "max_output_tokens")
            ):
                ProviderConfig(
                    **{
                        k: getattr(a, k)
                        for k in (
                            "model",
                            "base_url",
                            "timeout_seconds",
                            "max_output_tokens",
                        )
                        if getattr(a, k) is not None
                    },
                    **({} if a.model else {"model": "validation"}),
                )
        except (ValueError, TypeError):
            reject()
    if target:
        try:
            identifier(target)
        except ArchiveError:
            reject()
    return archived


def load_archived_inspection(
    catalog: RunCatalog, attempt_id: str, revision: int | None
) -> SimulationEngine:
    try:
        with catalog.open_attempt(attempt_id, read_only=True) as archive:
            inputs = load_retained_inputs(archive.ref)
            snapshot = archive.checkpoint(revision).snapshot
            engine = SimulationEngine(SnapshotRepository(snapshot))
            engine.load_scenario(inputs.scenario_path)
            if encode_world(engine.state) != snapshot:
                raise ValueError
            return engine
    except (ArchiveError, OSError):
        raise RuntimeCLIError(4, "archive_failed") from None
    except (ValueError, TypeError):
        raise RuntimeCLIError(3, "incompatible_save") from None


def _model(value: str) -> str:
    return value if ":" in value.rsplit("/", 1)[-1] else value + ":latest"


def _requested(a: argparse.Namespace, catalog: RunCatalog) -> AttemptConfig:
    with catalog.open_attempt(a.resume_attempt or a.fork_attempt) as archive:
        original = archive.config
        inputs = load_retained_inputs(archive.ref)
    if not _provided(a, _CONFIG_FLAGS):
        return original
    settings = dict(original.settings)
    limits = dict(cast(Mapping[str, object], settings.get("limits", {})))
    if a.driver is not None and original.mode != a.driver:
        raise RuntimeCLIError(2, "invalid_configuration")
    if original.mode != "ollama" and _provided(a, _PROVIDER_FLAGS):
        raise RuntimeCLIError(2, "invalid_configuration")
    if a.max_ticks is not None or a.continuous:
        limits["max_ticks"] = None if a.continuous else a.max_ticks
        if original.mode == "recorded":
            limits["continuous"] = bool(a.continuous)
    for name in ("save_every", "max_requests"):
        if getattr(a, name) is not None:
            limits[name] = getattr(a, name)
    settings["limits"] = limits
    if original.mode == "ollama":
        old = provider_config(original)
        provider = dict(cast(Mapping[str, object], settings.get("provider", {})))
        for name in ("model", "base_url", "timeout_seconds", "max_output_tokens"):
            if getattr(a, name) is not None:
                provider[name] = getattr(a, name)
        if _model(cast(str, provider["model"])) != _model(old.model):
            provider.pop("model_digest", None)
        settings["provider"] = provider
    try:
        candidate = replace(original, settings=settings)
    except (ValueError, TypeError, ArchiveError):
        raise RuntimeCLIError(2, "invalid_configuration") from None
    if a.resume_attempt:

        def budget(config: AttemptConfig) -> tuple[object, object, object]:
            values = cast(Mapping[str, object], config.settings.get("limits", {}))
            maximum = values.get("max_ticks", 20 if config.mode == "ollama" else None)
            if (
                config.mode == "recorded"
                and maximum is None
                and not values.get("continuous", False)
            ):
                maximum = (
                    YAMLScenarioLoader().load(inputs.scenario_path).default_max_ticks
                )
            return maximum, values.get("save_every", 1), values.get("max_requests", 40)

        same = budget(original) == budget(candidate)
        if original.mode == "ollama":
            old, new = provider_config(original), provider_config(candidate)
            same = same and replace(old, model=_model(old.model)) == replace(
                new, model=_model(new.model)
            )
        if not same:
            raise RuntimeCLIError(2, "invalid_configuration")
        return original
    return candidate


def _exit(code: str) -> int:
    if code == "invalid_configuration":
        return 2
    if code == "incompatible_save":
        return 3
    if code in (
        "archive_failed",
        "mirror_failed",
        "initialization_failed",
        "setup_failed",
        "audit_failed",
    ):
        return 4
    return (
        6
        if code in SETUP_CODES
        or code in ERROR_CODES - {"tick_failed", "service_failed"}
        else 5
    )


@dataclass(frozen=True)
class ArchivedLaunch:
    """Expose the runtime owner before its one-shot, potentially blocking launch."""

    service: RuntimeService
    _start: Callable[[bool], RunController] = field(repr=False)

    def launch(self, *, paused: bool) -> RunController:
        return self._start(paused)


def prepare_archived_launch(
    arguments: argparse.Namespace,
    *,
    catalog: RunCatalog,
    on_reserved: Callable[[AttemptRef], None],
    disturbance: Literal["none", "resource_loss", "work_blockage"] | None = None,
) -> ArchivedLaunch:
    """Prepare an owner without reserving inputs or starting provider work."""
    if disturbance is not None and (
        type(disturbance) is not str
        or disturbance not in ("none", "resource_loss", "work_blockage")
    ):
        raise RuntimeCLIError(2, "invalid_configuration")
    a = argparse.Namespace(**vars(arguments))
    if disturbance is not None and (a.founders or a.replay_attempt):
        raise RuntimeCLIError(2, "invalid_configuration")
    config = None
    if a.resume_attempt or a.fork_attempt:
        config = _requested(a, catalog)
        if disturbance is not None:
            value = config.settings.get("boundary_disturbance")
            active = "none" if value is None else parse_boundary_disturbance(value).kind
            if config.mode != "ollama" or disturbance != active:
                raise RuntimeCLIError(2, "invalid_configuration")
    cadence_config = config
    if a.replay_attempt:
        with catalog.open_attempt(a.replay_attempt) as source:
            cadence_config = source.config
    save_every = a.save_every or 1
    if cadence_config is not None:
        save_every = cast(
            int,
            cast(Mapping[str, object], cadence_config.settings.get("limits", {})).get(
                "save_every", 1
            ),
        )
    service = RuntimeService(
        catalog, on_reserved=on_reserved, mirror_path=a.database, save_every=save_every
    )
    guard = Lock()
    used = False

    def start(paused: bool) -> RunController:
        nonlocal used, config
        if type(paused) is not bool:
            raise RuntimeCLIError(2, "invalid_configuration")
        with guard:
            if used:
                raise RuntimeCLIError(2, "invalid_configuration")
            used = True
        if a.preset:
            with materialize_founders_assets() as assets:
                scenario = YAMLScenarioLoader().load(assets.scenario)
                settings: dict[str, object] = {
                    "launch_source": "cli",
                    "driver_format": 1,
                    "provider": {
                        name: getattr(a, name)
                        for name in (
                            "model",
                            "base_url",
                            "timeout_seconds",
                            "max_output_tokens",
                        )
                        if getattr(a, name) is not None
                    },
                    "limits": {
                        "max_ticks": (
                            None
                            if a.continuous
                            else (a.max_ticks if a.max_ticks is not None else 20)
                        ),
                        "max_requests": a.max_requests or 40,
                        "save_every": save_every,
                    },
                }
                if disturbance not in (None, "none"):
                    settings["disturbance"] = disturbance
                    settings["boundary_disturbance"] = BoundaryDisturbance(
                        kind=disturbance,
                        format=2 if disturbance == "work_blockage" else 1,
                    ).as_document()
                config = AttemptConfig(
                    "ollama", scenario.key, scenario.seed, __version__, settings
                )
                ref = catalog.reserve_setup(config)
                try:
                    with AttemptLease(ref):
                        inputs = retain_inputs(ref, assets.scenario, tape_path=None)
                except Exception:  # noqa: BLE001 - preserve allocated setup identity
                    with suppress(Exception), AttemptLease(ref):
                        catalog.fail_setup(ref, "setup_failed")
                    raise RuntimeCLIError(4, "setup_failed", ref) from None
            try:
                return service.start(config, inputs, paused=paused)
            except RuntimeStartupError as error:
                if error.code != "service_closed" or error.ref is not None:
                    raise
                try:
                    with AttemptLease(ref):
                        catalog.fail_setup(ref, "setup_failed")
                except Exception:  # noqa: BLE001 - preserve unowned attempt identity
                    raise RuntimeCLIError(4, "archive_failed", ref) from None
                raise RuntimeStartupError(ref, "service_closed") from None
        elif a.founders:
            with materialize_founders_assets() as assets:
                scenario = YAMLScenarioLoader().load(assets.scenario)
                maximum = a.max_ticks
                if a.founders == "stall" and maximum is None and not a.continuous:
                    maximum = 5
                settings = {
                    "launch_source": "cli",
                    "driver_format": 1,
                    "finalize_proposals": not a.checkpoint_only,
                    "recorded_outcome": a.founders,
                    "limits": {
                        "max_ticks": maximum,
                        "continuous": bool(a.continuous),
                        "save_every": save_every,
                    },
                }
                config = AttemptConfig(
                    "recorded", scenario.key, scenario.seed, __version__, settings
                )
                session = LegacyArchiveSession(catalog, config)
                try:
                    try:
                        session.__enter__()
                        inputs = session.retain(
                            assets.scenario,
                            tape_path=assets.tape_for(FoundersOutcome(a.founders)),
                        )
                    except Exception:  # noqa: BLE001 - preserve allocated identity
                        with suppress(Exception):
                            session.fail("initialization_failed")
                        raise RuntimeCLIError(
                            4, "initialization_failed", session.ref
                        ) from None
                finally:
                    try:
                        session.close()
                    except Exception:  # noqa: BLE001 - preserve preparation identity
                        raise RuntimeCLIError(
                            4, "archive_failed", session.ref
                        ) from None
            try:
                return service.start(config, inputs, paused=paused)
            except RuntimeStartupError as error:
                if error.code != "service_closed" or error.ref is not None:
                    raise
                try:
                    try:
                        session.__enter__()
                        session.fail("initialization_failed")
                    finally:
                        session.close()
                except Exception:  # noqa: BLE001 - preserve unowned attempt identity
                    raise RuntimeCLIError(4, "archive_failed", session.ref) from None
                raise RuntimeStartupError(session.ref, "service_closed") from None
        elif a.resume_attempt:
            return service.resume(a.resume_attempt, a.checkpoint, paused=paused)
        elif a.fork_attempt:
            assert config is not None
            return service.fork(
                a.fork_attempt, a.checkpoint, config=config, paused=paused
            )
        else:
            return service.replay(a.replay_attempt, a.checkpoint, paused=paused)

    return ArchivedLaunch(service, start)


def run_archived(
    arguments: argparse.Namespace, control: StopControl
) -> ArchivedRunResult | None:
    a = arguments
    catalog = RunCatalog(a.archive_root or RunCatalog.default_root())
    ref: AttemptRef | None = None
    announced: set[str] = set()
    ready, done, stop_seen, watcher_failed = Event(), Event(), Event(), Event()
    service: RuntimeService | None = None

    def announce(value: AttemptRef) -> None:
        nonlocal ref
        ref = value
        if value.attempt_id not in announced:
            print(
                f"attempt={value.attempt_id} archive={value.directory.absolute()}",
                file=sys.stderr,
                flush=True,
            )
            announced.add(value.attempt_id)
        ready.set()

    def watch() -> None:
        while not done.wait(0.01):
            if not ready.is_set():
                continue
            try:
                if control.stop_requested():
                    stop_seen.set()
                    assert service is not None
                    service.shutdown()
                    return
            except BaseException:  # noqa: BLE001
                watcher_failed.set()
                assert service is not None
                with suppress(Exception):
                    service.shutdown(failure_code="service_failed")
                return

    watcher: Thread | None = None
    try:
        prepared = prepare_archived_launch(a, catalog=catalog, on_reserved=announce)
        service = prepared.service
        watcher = Thread(target=watch, name="living-world-cli-stop", daemon=False)
        watcher.start()
        controller = prepared.launch(paused=False)
        while True:
            status = controller.status()
            if watcher_failed.is_set():
                raise RuntimeCLIError(5, "service_failed", ref)
            if status.state.terminal:
                break
            if (
                status.state is RuntimeState.PROVIDER_ERROR_PAUSED
                and status.error_code != "request_budget_exhausted"
            ):
                code = status.error_code or "service_failed"
                service.shutdown(failure_code=code)
                raise RuntimeCLIError(_exit(code), code, ref)
            done.wait(0.01)
        service.shutdown()
        # Final owner settlement can replace a terminal state with a mirror failure.
        status = controller.status()
        if status.state is RuntimeState.FAILED:
            code = status.error_code or "service_failed"
            raise RuntimeCLIError(_exit(code), code, ref)
        assert ref is not None
        with catalog.open_attempt(ref.attempt_id) as archive:
            initial, final = archive.checkpoint(0), archive.checkpoint()
            outcome = next(
                (
                    entry.payload["outcome"]
                    for entry in reversed(archive.entries())
                    if entry.kind == "attempt_finished"
                ),
                None,
            )
            reason = (
                "operator_stop"
                if status.state is RuntimeState.STOPPED
                else "tick_limit"
            )
            terminal = None
            if outcome == "request_budget_exhausted":
                reason = "request_budget_exhausted"
            elif outcome is not None and status.state is RuntimeState.COMPLETED:
                reason, terminal = "terminal_condition", cast(str, outcome)
            world = decode_world(final.snapshot)
            finalized = None
            if archive.config.mode == "recorded" and world.replay_binding is not None:
                finalized = (
                    bool(archive.config.settings.get("finalize_proposals", True))
                    and reason != "operator_stop"
                )
            return ArchivedRunResult(
                archive.config.scenario_key,
                decode_world(initial.snapshot).tick,
                world.tick,
                bool(a.resume_attempt or a.fork_attempt),
                reason,
                terminal,
                finalized,
            )
    except Exception as error:  # noqa: BLE001 - sanitize all CLI runtime failures
        if (
            isinstance(error, (RuntimeStartupError, RuntimeCLIError))
            and error.ref is not None
        ) or isinstance(error, ArchiveReservationError):
            announce(error.ref)
        if watcher_failed.is_set():
            failure = RuntimeCLIError(5, "service_failed", ref)
        elif (
            isinstance(error, RuntimeStartupError)
            and error.code == "cancelled"
            and stop_seen.is_set()
        ):
            print("stop_reason=operator_stop", file=sys.stderr)
            return None
        else:
            failure = normalize_archived_failure(error, ref)
        if ref is None:
            retain_failed_initialization(catalog, on_reserved=announce)
        raise failure from None
    finally:
        done.set()
        cleanup_failed = False
        if service is not None:
            try:
                service.shutdown()
            except Exception:  # noqa: BLE001
                cleanup_failed = True
        if watcher is not None:
            watcher.join(timeout=6)
            cleanup_failed = cleanup_failed or watcher.is_alive()
        if cleanup_failed or watcher_failed.is_set():
            raise RuntimeCLIError(5, "service_failed", ref) from None


def normalize_archived_failure(
    error: Exception, ref: AttemptRef | None
) -> RuntimeCLIError:
    """Translate runtime failures without IO or leaking underlying diagnostics."""
    if isinstance(error, RuntimeCLIError):
        return error
    if isinstance(error, RuntimeStartupError):
        return RuntimeCLIError(_exit(error.code), error.code, ref)
    if isinstance(error, (ArchiveError, OSError)):
        return RuntimeCLIError(4, "archive_failed", ref)
    return RuntimeCLIError(5, "service_failed", ref)


def retain_failed_initialization(
    catalog: RunCatalog, *, on_reserved: Callable[[AttemptRef], None]
) -> AttemptRef:
    """Retain the existing failed initialization identity without recursive repair."""
    ref: AttemptRef | None = None
    try:
        failed = LegacyArchiveSession(
            catalog,
            AttemptConfig(
                "recorded",
                "uninitialized",
                0,
                __version__,
                {"launch_source": "cli", "driver_format": 1},
            ),
        )
        ref = failed.ref
        on_reserved(ref)
        with failed:
            failed.fail("initialization_failed")
        return ref
    except Exception as error:  # noqa: BLE001 - closed metadata persistence boundary
        if isinstance(error, ArchiveReservationError):
            ref = error.ref
            on_reserved(ref)
        raise RuntimeCLIError(4, "archive_failed", ref) from None
