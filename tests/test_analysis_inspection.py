"""Explicit selected-only offline checkpoint reads."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from test_inspection_api import ASGIClient
from test_runtime_revision_source import archive_world, inventory

from living_world.api.auth import AdminSession
from living_world.api.trace_analysis import create_analysis_app
from living_world.archives import RunCatalog


def client_for(catalog):
    auth = AdminSession.issue()
    client = ASGIClient(create_analysis_app(catalog, auth=auth))
    return client, {"Authorization": f"Bearer {auth.token}"}


def test_exact_selected_world_and_panels(tmp_path, monkeypatch):
    from living_world.api import analysis_revision_source as module
    from living_world.api.inspection import EngineWorldInspector

    catalog, ref, snapshots = archive_world(tmp_path)
    bad = catalog.root / uuid4().hex / uuid4().hex
    bad.mkdir(parents=True)
    (bad / "archive.sqlite3").write_bytes(b"private broken unrelated archive")
    before = inventory(catalog.root)

    def forbidden(*args, **kwargs):
        pytest.fail("offline selection enumerated full archives or probed ownership")

    from living_world.archives import AttemptLease

    monkeypatch.setattr(RunCatalog, "attempts", forbidden)
    monkeypatch.setattr(AttemptLease, "is_owned", forbidden)
    loader = module.load_archived_inspection
    loaded = []

    def checked(*args):
        from living_world.repositories.world_snapshot import encode_world

        engine = loader(*args)
        assert encode_world(engine.state) == snapshots[args[2]]
        loaded.append(engine)
        return engine

    monkeypatch.setattr(module, "load_archived_inspection", checked)
    client, headers = client_for(catalog)
    for revision in (0, 1):
        prefix = f"/archives/{ref.attempt_id}/checkpoints/{revision}"
        html = client.request("GET", prefix + "/inspector", headers=headers)
        assert html.status_code == 200
        assert f'data-inspection-prefix="{prefix}"' in html.body.decode()
        assert html.body.count(b'data-inspection-kind="historical"') == 1
        expected = EngineWorldInspector(loaded[-1])
        for suffix, method in (
            ("world", "world_summary"),
            ("world/entities", "entities"),
            ("world/events", "events"),
            ("world/resources", "resources"),
            ("world/needs", "needs"),
            ("world/work-orders", "work_orders"),
        ):
            import json

            response = client.request("GET", prefix + "/" + suffix, headers=headers)
            assert response.status_code == 200
            assert response.json() == json.loads(
                json.dumps(getattr(expected, method)())
            )
            assert response.headers["cache-control"] == "no-store"
    assert len(loaded) == 2
    assert inventory(catalog.root) == before


@pytest.mark.parametrize(
    "revision", ["-1", "+1", "1.0", "١", "9" * 21, "9007199254740992"]
)
def test_auth_and_invalid_selection_before_storage(tmp_path, monkeypatch, revision):
    from living_world.api import analysis_revision_source as module

    def forbidden(*args, **kwargs):
        pytest.fail("invalid request reached storage")

    monkeypatch.setattr(module, "resolve_trace_attempt", forbidden)
    root = tmp_path / "absent"
    client, headers = client_for(RunCatalog(root))
    for suffix in ("inspector", "world/tick"):
        path = f"/archives/{uuid4().hex}/checkpoints/{revision}/{suffix}"
        assert client.request("GET", path).status_code == 401
        assert client.request("GET", path, headers=headers).status_code == 404
    assert (
        client.request(
            "GET", "/archives/bad/checkpoints/0/world", headers=headers
        ).status_code
        == 404
    )
    assert not root.exists()


def test_source_lru_failure_concurrency_and_cached_detachment(tmp_path, monkeypatch):
    from living_world.api import analysis_revision_source as module
    from living_world.api.revision_source import RevisionSourceError

    catalog, ref, _ = archive_world(tmp_path, revisions=10)
    source = module.AnalysisRevisionSource(catalog)
    loader, loads = module.load_archived_inspection, []

    def counted(*args):
        loads.append(args[2])
        return loader(*args)

    monkeypatch.setattr(module, "load_archived_inspection", counted)
    views = [source.open(ref.attempt_id, n) for n in range(8)]
    assert source.open(ref.attempt_id, 0) is views[0]
    with pytest.raises(RevisionSourceError):
        source.open(ref.attempt_id, 100)
    assert source.open(ref.attempt_id, 1) is views[1]
    source.open(ref.attempt_id, 8)
    assert source.open(ref.attempt_id, 0) is views[0]
    assert source.open(ref.attempt_id, 2) is not views[2]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: source.open(ref.attempt_id, 9), range(24)))
    assert all(view is results[0] for view in results)
    assert loads.count(9) == 1
    (ref.directory / "inputs.json").write_text("private tamper")
    assert source.open(ref.attempt_id, 9) is results[0]
    before = inventory(catalog.root)
    with pytest.raises(RevisionSourceError) as caught:
        source.open(ref.attempt_id, 3)
    assert caught.value.code == "archive_invalid"
    assert source.open(ref.attempt_id, 0) is views[0]
    assert inventory(catalog.root) == before


@pytest.mark.parametrize(
    "damage,code",
    [
        ("missing", 404),
        ("database", 409),
        ("input", 409),
        ("duplicate", 404),
        ("symlink", 409),
    ],
)
def test_selected_errors_sanitized(tmp_path, damage, code):
    import shutil

    catalog, ref, _ = archive_world(tmp_path)
    database = ref.directory / "archive.sqlite3"
    if damage == "missing":
        database.unlink()
    elif damage == "database":
        database.write_bytes(b"private database diagnostic")
    elif damage == "input":
        (ref.directory / "inputs.json").write_text("private input diagnostic")
    elif damage == "duplicate":
        shutil.copytree(ref.directory, catalog.root / uuid4().hex / ref.attempt_id)
    else:
        database.unlink()
        database.symlink_to(tmp_path / "private")
    before = inventory(catalog.root) if damage != "symlink" else None
    client, headers = client_for(catalog)
    response = client.request(
        "GET", f"/archives/{ref.attempt_id}/checkpoints/0/inspector", headers=headers
    )
    assert response.status_code == code
    assert response.json() == {
        "detail": "not_found" if code == 404 else "archive_invalid"
    }
    if before is not None:
        assert inventory(catalog.root) == before


def test_unavailable_canonical_and_assets(tmp_path):
    from living_world.archives import AttemptConfig

    catalog, ref, _ = archive_world(tmp_path)
    empty = catalog.reserve(AttemptConfig("recorded", "empty", 0, "test", {}))
    client, headers = client_for(catalog)
    for identity, revision in (
        (empty.attempt_id, "0"),
        (uuid4().hex, "0"),
        (ref.attempt_id, "2"),
    ):
        assert (
            client.request(
                "GET",
                f"/archives/{identity}/checkpoints/{revision}/inspector",
                headers=headers,
            ).status_code
            == 404
        )
    response = client.request(
        "GET", f"/archives/{ref.attempt_id}/checkpoints/000/world/tick", headers=headers
    )
    assert response.json() == {"tick": 0}
    for asset in ("inspector.css", "inspector.js"):
        assert client.request("GET", "/inspector/assets/" + asset).status_code == 200
    for path in (
        "/inspector/assets/unknown",
        "/openapi.json",
        "/live/checkpoints/0/world",
        "/archives/anything/checkpoints",
    ):
        assert client.request("GET", path, headers=headers).status_code == 404


@pytest.mark.parametrize(
    "identity,revision",
    [
        ("bad", 0),
        ("../private", 0),
        (None, 0),
        (uuid4().hex, True),
        (uuid4().hex, -1),
        (uuid4().hex, "0"),
        (uuid4().hex, 1.5),
    ],
)
def test_source_invalid_arguments_do_not_resolve(
    tmp_path, monkeypatch, identity, revision
):
    from living_world.api import analysis_revision_source as module
    from living_world.api.revision_source import RevisionSourceError

    def forbidden(*args, **kwargs):
        pytest.fail("invalid source arguments reached catalog")

    monkeypatch.setattr(module, "resolve_trace_attempt", forbidden)
    with pytest.raises(RevisionSourceError) as caught:
        module.AnalysisRevisionSource(RunCatalog(tmp_path / "absent")).open(
            identity, revision
        )
    assert caught.value.code == "not_found"
    assert not (tmp_path / "absent").exists()


def test_auth_assets_and_discovery_never_reconstruct_or_own(tmp_path, monkeypatch):
    from living_world.api import analysis_revision_source as module
    from living_world.archives import AttemptLease
    from living_world.runtime import RunController, RuntimeService
    from living_world.runtime.broker import DecisionBroker
    from living_world.simulation.simulation_engine import SimulationEngine

    catalog, ref, _ = archive_world(tmp_path)
    before = inventory(catalog.root)

    def forbidden(*args, **kwargs):
        pytest.fail(
            "offline route constructed runtime, acquired/probed ownership or stepped"
        )

    for cls, name in (
        (RunController, "__init__"),
        (RuntimeService, "__init__"),
        (DecisionBroker, "__init__"),
        (AttemptLease, "__enter__"),
        (AttemptLease, "is_owned"),
        (SimulationEngine, "step"),
    ):
        monkeypatch.setattr(cls, name, forbidden)
    client, headers = client_for(catalog)
    loader = module.load_archived_inspection
    monkeypatch.setattr(module, "load_archived_inspection", forbidden)
    for path in (
        "/analysis",
        "/analysis/status",
        "/analysis/attempts",
        f"/analysis/attempts/{ref.attempt_id}/traces",
        "/inspector/assets/inspector.js",
        "/inspector/assets/inspector.css",
    ):
        assert client.request("GET", path, headers=headers).status_code == 200
    resolver = module.resolve_trace_attempt
    monkeypatch.setattr(module, "resolve_trace_attempt", forbidden)
    for suffix in (
        "inspector",
        "world",
        "world/tick",
        "world/entities",
        "world/events",
        "world/memories",
        "world/cognitive-history/private",
    ):
        path = f"/archives/{ref.attempt_id}/checkpoints/0/{suffix}"
        assert client.request("GET", path).status_code == 401
        assert (
            client.request(
                "GET", path, headers={**headers, "Origin": "http://evil.invalid"}
            ).status_code
            == 403
        )
    monkeypatch.setattr(module, "resolve_trace_attempt", resolver)
    monkeypatch.setattr(module, "load_archived_inspection", loader)
    response = client.request(
        "GET",
        f"/archives/{ref.attempt_id}/checkpoints/00/inspector?token=secret&prefix=https://evil.invalid",
        headers=headers,
    )
    assert response.status_code == 200
    assert b"secret" not in response.body and b"evil.invalid" not in response.body
    assert inventory(catalog.root) == before


def test_failed_reconstruction_preserves_every_cached_view(tmp_path, monkeypatch):
    from living_world.api import analysis_revision_source as module
    from living_world.api.revision_source import RevisionSourceError

    catalog, ref, _ = archive_world(tmp_path, revisions=9)
    source = module.AnalysisRevisionSource(catalog)
    views = [source.open(ref.attempt_id, revision) for revision in range(8)]

    def broken(*args):
        raise RuntimeError("private loader path and diagnostic")

    monkeypatch.setattr(module, "load_archived_inspection", broken)
    with pytest.raises(RevisionSourceError) as caught:
        source.open(ref.attempt_id, 8)
    assert caught.value.code == str(caught.value) == "archive_invalid"
    assert caught.value.__cause__ is None
    assert all(
        source.open(ref.attempt_id, revision) is view
        for revision, view in enumerate(views)
    )
