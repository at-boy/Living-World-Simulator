"""Actual ASGI route and state-preservation checks for packaged inspector."""

import pytest
from test_inspection_api import ASGIClient

from living_world.api.inspection import _snapshot_value
from living_world.api.server import create_app
from living_world.core.definition import Definition
from living_world.simulation.simulation_engine import SimulationEngine


@pytest.mark.parametrize(
    "path,content_type",
    [
        ("/inspector", "text/html"),
        ("/inspector/assets/inspector.css", "text/css"),
        ("/inspector/assets/inspector.js", "text/javascript"),
    ],
)
def test_packaged_inspector_get_only(path: str, content_type: str) -> None:
    client = ASGIClient(create_app(SimulationEngine()))
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.body
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert client.request(method, path).status_code == 405
    assert client.get("/inspector/assets/unknown.js").status_code == 404


def test_inspector_reads_leave_engine_and_events_unchanged() -> None:
    engine = SimulationEngine()
    engine.definitions.register(Definition("thing"))
    entity = engine.entities.create(
        definition_key="thing", name="<img src=x onerror=alert(1)>"
    )
    before = _snapshot_value(engine.state)
    client = ASGIClient(create_app(engine))
    for path in (
        "/inspector",
        "/world",
        "/world/entities",
        f"/world/entities/{entity.id}",
        "/world/events",
    ):
        assert client.get(path).status_code == 200
    assert client.get("/world/entities/missing").status_code == 404
    payload = client.get(f"/world/entities/{entity.id}").json()
    payload["attributes"]["changed"] = True
    assert _snapshot_value(engine.state) == before
