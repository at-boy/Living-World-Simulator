"""Owner-only construction and resource settlement for the runtime service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Literal, cast

from living_world.archives import (
    ArchiveError,
    ArchiveFormatError,
    AttemptArchive,
    AttemptConfig,
    AttemptLease,
    AttemptRef,
    Checkpoint,
    ForkPoint,
    JournalEntry,
    RetainedInputs,
    RunCatalog,
    load_retained_inputs,
    retain_inputs,
)
from living_world.archives.catalog import (
    SETUP_CODES,
    ArchiveReservationError,
    read_reservation,
)
from living_world.archives.lease import validate_ref
from living_world.archives.model import canonical
from living_world.repositories.world_snapshot import encode_world
from living_world.scenarios.scenario import YAMLScenarioLoader

from .broker import (
    ERROR_CODES,
    DecisionBroker,
    client_for,
    encoded_body,
    provider_config,
)
from .contracts import ScenarioComposition, TickDriver
from .feedback import FoundersFeedback
from .founders import FoundersLiveComposition
from .journal_replay import JournalReplayComposition, JournalReplayDriver
from .ollama_driver import OllamaTickDriver, effective_config_fingerprint
from .preflight import ProviderPreflightError, preflight_provider
from .recorded import RecordedScenarioComposition, RecordedTickDriver

_STARTUP_CODES = (
    SETUP_CODES
    | ERROR_CODES
    | {
        "invalid_configuration",
        "incompatible_save",
        "archive_failed",
        "initialization_failed",
        "service_closed",
        "service_not_ready",
        "service_failed",
        "mirror_failed",
    }
)


class RuntimeStartupError(RuntimeError):
    """Safe closed failure code and, when allocated, durable attempt identity."""

    def __init__(self, ref: AttemptRef | None, code: str) -> None:
        if code not in _STARTUP_CODES:
            raise ValueError("Unknown runtime startup code.")
        self.ref, self.code = ref, code
        super().__init__(code)


@dataclass
class _Launch:
    ref: AttemptRef
    archive: AttemptArchive
    composition: ScenarioComposition
    driver: TickDriver
    max_ticks: int | None
    stack: ExitStack

    def close(self) -> None:
        self.stack.close()


class _LaunchFactory:
    def __init__(
        self,
        catalog: RunCatalog,
        cancel_event: Event,
        on_reserved: Callable[[AttemptRef], None] | None,
    ) -> None:
        self.catalog, self.cancel_event, self.on_reserved = (
            catalog,
            cancel_event,
            on_reserved,
        )
        self.ref: AttemptRef | None = None
        self._stack = ExitStack()
        self._archive: AttemptArchive | None = None
        self._accepted = False
        self._pending = False

    def _cancel(self) -> None:
        if self.cancel_event.is_set():
            raise RuntimeStartupError(self.ref, "cancelled")

    def _guard(self, operation: Callable[[], _Launch]) -> _Launch:
        try:
            return operation()
        except BaseException as error:  # noqa: BLE001
            if isinstance(error, ArchiveReservationError):
                self.ref = error.ref
            code = (
                error.code
                if isinstance(error, (RuntimeStartupError, ProviderPreflightError))
                else (
                    "archive_failed"
                    if isinstance(error, (OSError, ArchiveError))
                    else (
                        "cancelled"
                        if isinstance(error, (KeyboardInterrupt, SystemExit))
                        else "service_failed"
                    )
                )
            )
            if self._accepted and self.ref is not None:
                with suppress(BaseException):
                    # A producer may have published SQLite and then failed before
                    # returning. Record its failure without repairing publication.
                    if (
                        self._archive is None
                        and (self.ref.directory / "archive.sqlite3").exists()
                    ):
                        self._archive = self._stack.enter_context(
                            AttemptArchive.open(self.ref, read_only=False)
                        )
                    if self._archive is not None:
                        self._archive.record(
                            (
                                JournalEntry(
                                    "attempt_finished",
                                    {
                                        "lifecycle": "failed",
                                        "outcome": code,
                                        "last_revision": self._archive.latest_revision,
                                    },
                                ),
                            )
                        )
                    elif self._pending:
                        self.catalog.fail_setup(
                            self.ref, code if code in SETUP_CODES else "setup_failed"
                        )
            with suppress(BaseException):
                self._stack.close()
            raise RuntimeStartupError(self.ref, code) from None

    def _lease(self, ref: AttemptRef) -> None:
        self.ref = ref
        self._stack.enter_context(AttemptLease(ref))

    def _notify(self) -> None:
        self._cancel()
        if self.on_reserved is not None:
            try:
                assert self.ref is not None
                self.on_reserved(self.ref)
            except BaseException:  # noqa: BLE001 - trusted callback cannot escape owner
                raise RuntimeStartupError(self.ref, "setup_failed") from None
        self._cancel()

    def _open(self) -> AttemptArchive:
        assert self.ref is not None
        self._archive = self._stack.enter_context(
            self.catalog.open_attempt(self.ref.attempt_id, read_only=False)
        )
        return self._archive

    def _feedback(self, config: AttemptConfig) -> FoundersFeedback:
        client = client_for(provider_config(config))
        return FoundersFeedback(
            lambda context, options: len(
                encoded_body(client.build_payload(context, options))
            )
        )

    def _recorded(
        self,
        config: AttemptConfig,
        inputs: RetainedInputs,
        base: Checkpoint | None = None,
    ) -> tuple[RecordedScenarioComposition, RecordedTickDriver, int | None]:
        limits = cast(Mapping[str, object], config.settings.get("limits", {}))
        maximum = None if limits.get("continuous", False) else limits.get("max_ticks")
        if maximum is None and not limits.get("continuous", False):
            maximum = YAMLScenarioLoader().load(inputs.scenario_path).default_max_ticks
        maximum = cast(int | None, maximum)
        composition = RecordedScenarioComposition(
            inputs,
            finalize_proposals=cast(
                bool, config.settings.get("finalize_proposals", True)
            ),
            max_ticks=maximum,
        )
        kind = (
            ("legacy_recorded" if inputs.tape_path is None else "recorded")
            if base is None
            else base.driver_cursor.get("mode")
        )
        if kind not in ("recorded", "legacy_recorded"):
            raise RuntimeStartupError(self.ref, "incompatible_save")
        driver = RecordedTickDriver(
            cursor_kind=cast(Literal["recorded", "legacy_recorded"], kind)
        )
        return composition, driver, maximum

    def _live(
        self, config: AttemptConfig, inputs: RetainedInputs
    ) -> tuple[FoundersLiveComposition, OllamaTickDriver, int | None]:
        broker = DecisionBroker()
        self._stack.callback(broker.close)
        limits = cast(Mapping[str, object], config.settings.get("limits", {}))
        return (
            FoundersLiveComposition(inputs),
            OllamaTickDriver(provider_config(config), self._feedback(config), broker),
            cast(int | None, limits.get("max_ticks", 20)),
        )

    def _validate(
        self,
        composition: ScenarioComposition,
        driver: RecordedTickDriver | OllamaTickDriver | JournalReplayDriver,
        base: Checkpoint,
        archive: AttemptArchive,
    ) -> bool:
        try:
            candidate = composition.restore(base.snapshot)
            if encode_world(candidate.state) != base.snapshot:
                raise ValueError
            driver.validate_checkpoint(candidate, base, archive)
            return composition.terminal_condition(candidate) is not None
        except (ArchiveError, ValueError, TypeError, KeyError):
            raise RuntimeStartupError(self.ref, "incompatible_save") from None

    def _bundle(
        self, composition: ScenarioComposition, driver: TickDriver, maximum: int | None
    ) -> _Launch:
        assert self.ref is not None and self._archive is not None
        self._cancel()
        return _Launch(
            self.ref, self._archive, composition, driver, maximum, self._stack.pop_all()
        )

    def start(self, config: AttemptConfig, inputs: RetainedInputs) -> _Launch:
        return self._guard(lambda: self._start(config, inputs))

    def _start(self, config: AttemptConfig, inputs: RetainedInputs) -> _Launch:
        roots = [
            path.parents[len(Path(name).parts) - 1]
            for path in (inputs.scenario_path, inputs.definition_path)
            for name in inputs.hashes
            if path.as_posix().endswith("/" + name)
        ]
        trees = {path for path in roots if path.name == "inputs"}
        if len(trees) != 1:
            raise RuntimeStartupError(None, "invalid_configuration")
        directory = trees.pop().parent
        self.ref = AttemptRef(directory.parent.name, directory.name, directory)
        if validate_ref(self.ref) != self.catalog.root:
            raise RuntimeStartupError(self.ref, "invalid_configuration")
        self._lease(self.ref)
        try:
            if load_retained_inputs(self.ref) != inputs:
                raise ValueError
            if config.mode == "ollama":
                if self.catalog.setup_config(self.ref) != config or any(
                    (self.ref.directory / name).exists()
                    for name in (
                        "attempt.json",
                        "archive.sqlite3",
                        "setup_complete.json",
                        "setup_failure.json",
                    )
                ):
                    raise ValueError
                self._pending = True
            elif config.mode == "recorded":
                archive = self._open()
                if (
                    archive.config != config
                    or archive.latest_revision is not None
                    or archive.entries()
                    or archive.lifecycle()
                ):
                    raise ValueError
            else:
                raise ValueError
        except (ArchiveError, ValueError, TypeError):
            raise RuntimeStartupError(self.ref, "invalid_configuration") from None
        self._accepted = True
        self._notify()
        if config.mode == "ollama":
            effective = preflight_provider(config, cancel_event=self.cancel_event)
            self.catalog.complete_setup(self.ref, effective)
            archive = self._open()
            composition, driver, maximum = self._live(effective, inputs)
        else:
            try:
                composition, driver, maximum = self._recorded(config, inputs)
                composition.initialize()
            except (ValueError, TypeError, ArchiveError):
                raise RuntimeStartupError(self.ref, "incompatible_save") from None
        return self._bundle(composition, driver, maximum)

    def resume(self, attempt_id: str, revision: int | None) -> _Launch:
        return self._guard(lambda: self._linked(attempt_id, revision, None))

    def fork(
        self, attempt_id: str, revision: int | None, config: AttemptConfig
    ) -> _Launch:
        return self._guard(lambda: self._linked(attempt_id, revision, config))

    def _linked(
        self, attempt_id: str, revision: int | None, requested: AttemptConfig | None
    ) -> _Launch:
        source = self._stack.enter_context(self.catalog.open_attempt(attempt_id))
        if source.config.mode == "ollama":
            ref = self.catalog.reserve_fork_setup(
                attempt_id, revision, requested=requested
            )
            self.ref = ref
            self._pending = True
            self._lease(ref)
            self._accepted = True
            self._notify()
            summary = next(item for item in self.catalog.attempts() if item.ref == ref)
            assert summary.parent is not None
            base = source.checkpoint(summary.parent[1])
            source_inputs = load_retained_inputs(source.ref)
            composition, driver, _ = self._live(source.config, source_inputs)
            terminal = self._validate(composition, driver, base, source)
            config = self.catalog.setup_config(ref)
            # Only semantic world terminality allows bypassing discovery. Operational
            # stop/failure/budget outcomes remain fresh resumable children.
            pinned = (
                cast(Mapping[str, object], config.settings.get("provider", {})).get(
                    "model_digest"
                )
                is not None
            )
            effective = (
                config
                if requested is None and terminal and pinned
                else preflight_provider(config, cancel_event=self.cancel_event)
            )
            self.catalog.complete_setup(ref, effective)
            archive = self._open()
            composition, driver, maximum = self._live(
                effective, load_retained_inputs(ref)
            )
            self._validate(composition, driver, archive.checkpoint(), archive)
            return self._bundle(composition, driver, maximum)
        if source.config.mode == "journal_replay":
            if requested is not None and requested != source.config:
                raise RuntimeStartupError(None, "invalid_configuration")
        elif requested is not None:
            original, changed = source.config, requested
            if (
                changed.mode,
                changed.scenario_key,
                changed.seed,
                changed.software_revision,
            ) != (
                original.mode,
                original.scenario_key,
                original.seed,
                original.software_revision,
            ) or canonical(
                {k: v for k, v in changed.settings.items() if k != "limits"}
            ) != canonical(
                {k: v for k, v in original.settings.items() if k != "limits"}
            ):
                raise RuntimeStartupError(None, "invalid_configuration")
        point = source.fork_point(revision)
        try:
            ref = self.catalog.fork(
                attempt_id, point.checkpoint.revision, config=requested
            )
        except ArchiveReservationError as error:
            # The trusted producer supplies the identity allocated before failure.
            # Verify its captured relationship before accepting failure ownership.
            ref = error.ref
            self.ref = ref
            if (
                validate_ref(ref) != self.catalog.root
                or ref.lineage_id != source.ref.lineage_id
                or ref.attempt_id == source.ref.attempt_id
            ):
                raise ArchiveFormatError("Invalid allocated fork identity.") from error
            child_config, parent, _, reservation_error = read_reservation(ref)
            if (
                parent != (attempt_id, point.checkpoint.revision)
                or child_config != (source.config if requested is None else requested)
                or reservation_error is not None
            ):
                raise ArchiveFormatError(
                    "Invalid allocated fork relationship."
                ) from error
            self._lease(ref)
            self._accepted = True
            raise
        self.ref = ref
        self._lease(ref)
        self._accepted = True
        self._notify()
        archive = self._open()
        inputs = load_retained_inputs(ref)
        if archive.config.mode == "recorded":
            composition, driver, maximum = self._recorded(
                archive.config, inputs, archive.checkpoint()
            )
        else:
            composition, driver, maximum = self._replay_parts(source, inputs)
        self._validate(composition, driver, archive.checkpoint(), archive)
        return self._bundle(composition, driver, maximum)

    def _replay_source(
        self, replay: AttemptArchive
    ) -> tuple[AttemptArchive, ForkPoint]:
        visited: set[str] = set()
        hashes = load_retained_inputs(replay.ref).hashes
        current = replay
        while current.config.mode == "journal_replay":
            if (
                current.ref.attempt_id in visited
                or current.parent is None
                or current.parent_journal_boundary is None
            ):
                raise RuntimeStartupError(self.ref, "incompatible_save")
            visited.add(current.ref.attempt_id)
            pair, boundary = current.parent, current.parent_journal_boundary
            parent = self._stack.enter_context(self.catalog.open_attempt(pair[0]))
            if load_retained_inputs(parent.ref).hashes != hashes:
                raise RuntimeStartupError(self.ref, "incompatible_save")
            if parent.config.mode == "ollama":
                point = ForkPoint(parent.checkpoint(pair[1]), boundary)
                if replay.config.settings.get(
                    "source_config_fingerprint"
                ) != effective_config_fingerprint(parent.config):
                    raise RuntimeStartupError(self.ref, "incompatible_save")
                return parent, point
            if parent.config.mode != "journal_replay" or parent.config != replay.config:
                raise RuntimeStartupError(self.ref, "incompatible_save")
            current = parent
        raise RuntimeStartupError(self.ref, "incompatible_save")

    def _replay_parts(
        self,
        source: AttemptArchive,
        inputs: RetainedInputs,
        point: ForkPoint | None = None,
    ) -> tuple[JournalReplayComposition, JournalReplayDriver, None]:
        try:
            if source.config.mode == "journal_replay":
                source, point = self._replay_source(source)
            assert point is not None
            source_inputs = load_retained_inputs(source.ref)
            live, live_driver, _ = self._live(source.config, source_inputs)
            self._validate(live, live_driver, point.checkpoint, source)
            composition = JournalReplayComposition(
                source, FoundersLiveComposition(inputs), source_point=point
            )
            driver = JournalReplayDriver(
                source,
                self._feedback(source.config),
                source_point=composition.source_point,
            )
            assert self._archive is not None
            driver.validate_checkpoint(
                composition.initialize(), source.checkpoint(0), self._archive
            )
            return composition, driver, None
        except (ArchiveError, ValueError, TypeError, KeyError):
            raise RuntimeStartupError(self.ref, "incompatible_save") from None

    def replay(self, attempt_id: str, revision: int | None) -> _Launch:
        return self._guard(lambda: self._replay(attempt_id, revision))

    def _replay(self, attempt_id: str, revision: int | None) -> _Launch:
        source = self._stack.enter_context(self.catalog.open_attempt(attempt_id))
        if source.config.mode != "ollama":
            raise RuntimeStartupError(None, "invalid_configuration")
        point = source.fork_point(revision)
        settings: dict[str, object] = {
            "source_config_fingerprint": effective_config_fingerprint(source.config),
            "limits": {"max_ticks": None},
        }
        if "launch_source" in source.config.settings:
            settings["launch_source"] = source.config.settings["launch_source"]
        config = AttemptConfig(
            "journal_replay",
            source.config.scenario_key,
            source.config.seed,
            source.config.software_revision,
            settings,
        )
        ref = self.catalog.reserve(
            config,
            parent=(attempt_id, point.checkpoint.revision),
            parent_journal_boundary=point.journal_boundary,
        )
        self.ref = ref
        self._lease(ref)
        self._accepted = True
        inputs = load_retained_inputs(source.ref)
        retain_inputs(ref, inputs.scenario_path, tape_path=inputs.tape_path)
        self._notify()
        self._open()
        composition, driver, maximum = self._replay_parts(
            source, load_retained_inputs(ref), point
        )
        return self._bundle(composition, driver, maximum)
