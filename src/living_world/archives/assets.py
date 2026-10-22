"""Immutable reconstruction inputs with verified content-addressed objects."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Mapping
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

from living_world.archives.lease import AttemptLease, safe_path, validate_ref
from living_world.archives.model import (
    ArchiveFormatError,
    AttemptRef,
    canonical,
    digest,
    document,
    loads,
)
from living_world.archives.store import AttemptArchive
from living_world.definitions.yaml_loader import YAMLWorldDefinitionLoader
from living_world.replay.loader import YAMLProposalTapeLoader
from living_world.scenarios.scenario import YAMLScenarioLoader, _UniqueKeyLoader


def private_name(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ArchiveFormatError("Expected relative private input path.")
    path = Path(value)
    if (
        path.is_absolute()
        or any(p in ("..", ".") for p in value.split("/"))
        or "" in value.split("/")
    ):
        raise ArchiveFormatError("Input path escapes private tree.")
    return value


def _source_definition(base: Path, declaration: object) -> tuple[str, Path]:
    """Inspect original components before normalizing the private capture role."""
    if (
        not isinstance(declaration, str)
        or not declaration
        or "\\" in declaration
        or Path(declaration).is_absolute()
    ):
        raise ArchiveFormatError("Expected a relative source definition path.")
    components: list[str] = []
    for component in declaration.split("/"):
        if component in ("", "."):
            continue
        if component == "..":
            if not components:
                raise ArchiveFormatError(
                    "Source definition escapes scenario directory."
                )
            components.pop()
        else:
            components.append(component)
            # Check before any subsequent '..' could erase a symlink component.
            safe_path(base.joinpath(*components))
    name = private_name("/".join(components))
    return name, safe_path(base / name, regular=True)


def atomic_document(path: Path, value: object) -> None:
    safe_path(path)
    descriptor, name = tempfile.mkstemp(prefix=".manifest-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical(value).encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def fsync_directory(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


@dataclass(frozen=True)
class RetainedInputs:
    scenario_path: Path
    definition_path: Path
    tape_path: Path | None
    hashes: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.hashes, Mapping):
            raise ArchiveFormatError("Expected input hashes.")
        for name, value in self.hashes.items():
            private_name(name)
            digest(value)
        paths = (self.scenario_path, self.definition_path) + (
            () if self.tape_path is None else (self.tape_path,)
        )
        if len(set(paths)) != len(paths):
            raise ArchiveFormatError("Input roles overlap.")
        roots: list[Path] = []
        for path in paths:
            if not isinstance(path, Path) or not path.is_absolute():
                raise ArchiveFormatError("Expected absolute input file paths.")
            safe_path(path, regular=True)
            matches = [
                path.parents[len(Path(name).parts) - 1]
                for name in self.hashes
                if path.as_posix().endswith("/" + name)
            ]
            roots.append(
                next((root for root in matches if root.name == "inputs"), Path("/"))
            )
        if not roots or len(set(roots)) != 1 or roots[0].name != "inputs":
            raise ArchiveFormatError("Input files must share a private input tree.")
        if set(self.hashes) != {
            path.relative_to(roots[0]).as_posix() for path in paths
        }:
            raise ArchiveFormatError("Unexpected input files.")
        object.__setattr__(self, "hashes", MappingProxyType(dict(self.hashes)))


def _validate_tree(
    ref: AttemptRef,
    tree: Path,
    scenario: str,
    definitions: str,
    tape: str | None,
    hashes: Mapping[str, str],
) -> None:
    roles = (scenario, definitions) + (() if tape is None else (tape,))
    if len(set(roles)) != len(roles) or set(roles) != set(hashes):
        raise ArchiveFormatError("Input roles and files mismatch.")
    actual: set[str] = set()
    for path in tree.rglob("*"):
        safe_path(path)
        if path.is_file():
            actual.add(path.relative_to(tree).as_posix())
        elif not path.is_dir():
            raise ArchiveFormatError("Unexpected private input node.")
    if actual != set(hashes):
        raise ArchiveFormatError("Unexpected private input files.")
    for name, expected in hashes.items():
        path = safe_path(tree / private_name(name), regular=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest(expected):
            raise ArchiveFormatError("Retained input hash mismatch.")
    try:
        loaded = YAMLScenarioLoader().load(tree / scenario)
        if loaded.definition_path != tree / definitions:
            raise ArchiveFormatError("Definition role mismatch.")
        YAMLWorldDefinitionLoader().load(loaded.definition_path)
        setup = safe_path(ref.directory / "setup.json")
        if setup.exists():
            from living_world.archives.catalog import validate_setup_inputs

            validate_setup_inputs(ref, hashes)
        complete = safe_path(ref.directory / "setup_complete.json")
        if setup.exists() and not complete.exists():
            from living_world.archives.catalog import (
                RunCatalog,
                validate_setup_reservation,
            )

            config = RunCatalog(validate_ref(ref)).setup_config(ref)
            if safe_path(ref.directory / "attempt.json").exists():
                validate_setup_reservation(ref, config)
        else:
            with AttemptArchive.open(ref, read_only=True) as archive:
                config = archive.config
        if loaded.key != config.scenario_key or loaded.seed != config.seed:
            raise ArchiveFormatError("Scenario identity/config mismatch.")
        if tape is not None:
            recorded = YAMLProposalTapeLoader().load(tree / tape)
            if (
                recorded.scenario_key != loaded.key
                or recorded.scenario_fingerprint != loaded.configuration_fingerprint
            ):
                raise ArchiveFormatError("Recorded tape scenario mismatch.")
    except (ValueError, OSError, TypeError, UnicodeError, yaml.YAMLError) as exc:
        raise ArchiveFormatError("Retained loader validation failed.") from exc


def load_retained_inputs(ref: AttemptRef) -> RetainedInputs:
    validate_ref(ref)
    try:
        manifest = safe_path(ref.directory / "inputs.json", regular=True)
        data = document(
            loads(manifest.read_text()),
            {
                "format",
                "lineage_id",
                "attempt_id",
                "scenario",
                "definitions",
                "tape",
                "files",
            },
        )
        if (
            type(data["format"]) is not int
            or data["format"] != 1
            or data["lineage_id"] != ref.lineage_id
            or data["attempt_id"] != ref.attempt_id
        ):
            raise ArchiveFormatError("Retained manifest format/identity mismatch.")
        scenario = private_name(data["scenario"])
        definitions = private_name(data["definitions"])
        tape = None if data["tape"] is None else private_name(data["tape"])
        files = data["files"]
        if not isinstance(files, Mapping):
            raise ArchiveFormatError("Expected input files mapping.")
        hashes = {private_name(name): digest(value) for name, value in files.items()}
        tree = safe_path(ref.directory / "inputs")
        _validate_tree(ref, tree, scenario, definitions, tape, hashes)
        return RetainedInputs(
            tree / scenario,
            tree / definitions,
            None if tape is None else tree / tape,
            hashes,
        )
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ArchiveFormatError("Invalid retained inputs.") from exc


def retain_inputs(
    ref: AttemptRef, scenario_path: Path, *, tape_path: Path | None
) -> RetainedInputs:
    """Capture once, validate staged bytes and publish an immutable input manifest."""
    root = validate_ref(ref)
    lease = (
        nullcontext()
        if AttemptLease.owned_by_current_thread(ref)
        else AttemptLease(ref)
    )
    with lease:
        staging: Path | None = None
        try:
            scenario_path = safe_path(scenario_path, regular=True)
            scenario_bytes = scenario_path.read_bytes()
            # Inspect only the existing loader's required path field. Full schema and
            # fingerprint validation run exclusively on the captured staged files.
            raw = yaml.load(scenario_bytes, Loader=_UniqueKeyLoader)
            if not isinstance(raw, dict):
                raise ArchiveFormatError("Expected scenario mapping.")
            definition_name, definition_path = _source_definition(
                scenario_path.parent, raw.get("definitions")
            )
            captured = {
                "scenario/" + scenario_path.name: scenario_bytes,
                "scenario/" + definition_name: definition_path.read_bytes(),
            }
            scenario = "scenario/" + scenario_path.name
            definitions = "scenario/" + definition_name
            tape = None
            if tape_path is not None:
                tape_path = safe_path(tape_path, regular=True)
                tape = "tape/" + tape_path.name
                captured[tape] = tape_path.read_bytes()
            if len(captured) != (2 if tape is None else 3):
                raise ArchiveFormatError("Input roles overlap.")
            hashes = {
                name: hashlib.sha256(value).hexdigest()
                for name, value in captured.items()
            }
            existing_manifest = safe_path(ref.directory / "inputs.json")
            if existing_manifest.exists():
                existing = load_retained_inputs(ref)
                if (
                    dict(existing.hashes) != hashes
                    or existing.scenario_path.relative_to(
                        ref.directory / "inputs"
                    ).as_posix()
                    != scenario
                    or existing.definition_path.relative_to(
                        ref.directory / "inputs"
                    ).as_posix()
                    != definitions
                    or (
                        None
                        if existing.tape_path is None
                        else existing.tape_path.relative_to(
                            ref.directory / "inputs"
                        ).as_posix()
                    )
                    != tape
                ):
                    raise ArchiveFormatError("Divergent immutable input retry.")
                return existing
            tree = safe_path(ref.directory / "inputs")
            if tree.exists():
                raise ArchiveFormatError("Unpublished input tree already exists.")
            staging = Path(tempfile.mkdtemp(prefix=".inputs-", dir=ref.directory))
            for name, value in captured.items():
                path = staging / name
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with path.open("xb") as handle:
                    os.chmod(path, 0o600)
                    handle.write(value)
                    handle.flush()
                    os.fsync(handle.fileno())
            _validate_tree(ref, staging, scenario, definitions, tape, hashes)
            objects = safe_path(root / "objects")
            objects.mkdir(mode=0o700, exist_ok=True)
            for name, value in captured.items():
                obj = safe_path(objects / hashes[name])
                try:
                    descriptor = os.open(
                        obj, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                    )
                except FileExistsError:
                    safe_path(obj, regular=True)
                    if hashlib.sha256(obj.read_bytes()).hexdigest() != hashes[name]:
                        raise ArchiveFormatError("Content object hash mismatch.")
                else:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(value)
                        handle.flush()
                        os.fsync(handle.fileno())
            os.rename(staging, tree)
            staging = None
            fsync_directory(ref.directory)
            atomic_document(
                existing_manifest,
                {
                    "format": 1,
                    "lineage_id": ref.lineage_id,
                    "attempt_id": ref.attempt_id,
                    "scenario": scenario,
                    "definitions": definitions,
                    "tape": tape,
                    "files": hashes,
                },
            )
            return load_retained_inputs(ref)
        except (OSError, ValueError, TypeError, UnicodeError, yaml.YAMLError) as exc:
            raise ArchiveFormatError("Could not retain reconstruction inputs.") from exc
        finally:
            if staging is not None:
                shutil.rmtree(staging)
