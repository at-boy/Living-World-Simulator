import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from living_world.api.server import create_app
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.core.belief import Belief, BeliefStatus
from living_world.core.definition import Definition
from living_world.core.event import Event
from living_world.core.experience import Experience
from living_world.core.observation import Observation
from living_world.core.relationship import Relationship
from living_world.core.resource_definition import ResourceDefinition
from living_world.simulation.simulation_engine import SimulationEngine


@dataclass(frozen=True, slots=True)
class HTTPResponse:
    status_code: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


class ASGIClient:
    """Minimal HTTP client that exercises the FastAPI ASGI application."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def get(self, path: str) -> HTTPResponse:
        return self.request("GET", path)

    def post(self, path: str) -> HTTPResponse:
        return self.request("POST", path)

    def request(self, method: str, path: str) -> HTTPResponse:
        return asyncio.run(self._request(method, path))

    async def _request(self, method: str, path: str) -> HTTPResponse:
        messages: list[Mapping[str, object]] = []
        request_sent = False
        response_complete = asyncio.Event()

        async def receive() -> Mapping[str, object]:
            nonlocal request_sent
            if request_sent:
                await response_complete.wait()
                return {"type": "http.disconnect"}
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: Mapping[str, object]) -> None:
            messages.append(message)
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                response_complete.set()

        await self.app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )

        status_message = next(
            message for message in messages if message["type"] == "http.response.start"
        )
        body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return HTTPResponse(status_code=int(status_message["status"]), body=body)


def make_client() -> tuple[SimulationEngine, ASGIClient]:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="npc", initial_attributes={"private": "operator-only"}),
            Definition(
                key="tree",
                initial_attributes={"resources": {"wood": 120}, "health": 92},
            ),
        )
    )
    engine.resource_definitions.register(ResourceDefinition(key="wood"))
    engine.resource_definitions.register(ResourceDefinition(key="water"))

    npc = engine.entities.create(definition_key="npc", name="Erik")
    tree = engine.entities.create(definition_key="tree", name="Old Oak")
    engine.relationships.add(
        Relationship(
            id="relationship_000002",
            kind="guards",
            source_id=npc.id,
            target_id=tree.id,
        )
    )
    engine.relationships.add(
        Relationship(
            id="relationship_000001",
            kind="knows",
            source_id=tree.id,
            target_id=npc.id,
        )
    )
    engine.events.add(
        Event(id="event_000002", tick=0, kind="grew", attributes={"wood": 120})
    )
    engine.events.add(Event(id="event_000001", tick=0, kind="seeded"))
    engine.observations.add(
        Observation(
            id="observation_000002",
            tick=0,
            observer=npc.id,
            subject=tree.id,
            description="The Old Oak looks strong.",
            confidence=0.9,
            evidence={"health": 92},
            metadata={"source": "perception"},
        )
    )
    engine.observations.add(
        Observation(
            id="observation_000001",
            tick=0,
            observer=npc.id,
            subject=tree.id,
            description="The Old Oak is a tree.",
            confidence=0.7,
            evidence={},
            metadata={},
        )
    )
    engine.beliefs.add(
        Belief(
            id="belief_000002",
            tick=0,
            holder_id=npc.id,
            subject_id=tree.id,
            proposition="The Old Oak is useful.",
            confidence=0.8,
            importance=0.7,
            status=BeliefStatus.IMPORTANT,
        )
    )
    engine.beliefs.add(
        Belief(
            id="belief_000001",
            tick=0,
            holder_id=npc.id,
            subject_id=tree.id,
            proposition="The Old Oak is old.",
            confidence=0.6,
            importance=0.5,
            status=BeliefStatus.ACTIVE,
        )
    )
    engine.experiences.add(
        Experience(
            id="experience_000002",
            tick=0,
            holder_id=npc.id,
            subject_id=tree.id,
            summary="Old oaks provide strong timber.",
        )
    )
    engine.experiences.add(
        Experience(
            id="experience_000001",
            tick=0,
            holder_id=npc.id,
            subject_id=tree.id,
            summary="The grove is quiet.",
        )
    )
    return engine, ASGIClient(create_app(engine))


def test_inspection_endpoints_return_authoritative_snapshots_in_id_order() -> None:
    _, client = make_client()

    assert client.get("/health").json() == {"status": "ok", "version": "0.2.3"}
    assert client.get("/world/tick").json() == {"tick": 0}
    assert client.get("/world").json() == {
        "tick": 0,
        "entity_count": 2,
        "relationship_count": 2,
        "event_count": 2,
        "observation_count": 2,
        "belief_count": 2,
        "experience_count": 2,
        "definition_count": 2,
        "resource_definition_count": 2,
    }

    assert [record["id"] for record in client.get("/world/entities").json()] == [
        "entity_000001",
        "entity_000002",
    ]
    entity = client.get("/world/entities/entity_000002")
    assert entity.status_code == 200
    assert entity.json() == {
        "id": "entity_000002",
        "definition_key": "tree",
        "name": "Old Oak",
        "attributes": {"resources": {"wood": 120}, "health": 92},
        "created_tick": 0,
        "destroyed_tick": None,
    }
    assert client.get("/world/entities/missing").status_code == 404

    assert [record["key"] for record in client.get("/world/definitions").json()] == [
        "npc",
        "tree",
    ]
    assert [record["key"] for record in client.get("/world/resources").json()] == [
        "water",
        "wood",
    ]

    for endpoint, prefix in (
        ("/world/relationships", "relationship"),
        ("/world/events", "event"),
        ("/world/observations", "observation"),
        ("/world/beliefs", "belief"),
        ("/world/experiences", "experience"),
    ):
        response = client.get(endpoint)
        assert response.status_code == 200
        assert [record["id"] for record in response.json()] == [
            f"{prefix}_000001",
            f"{prefix}_000002",
        ]


def test_inspection_payloads_are_detached_from_world_state() -> None:
    _, client = make_client()

    payload = client.get("/world/entities/entity_000002").json()
    payload["attributes"]["resources"]["wood"] = 0

    assert (
        client.get("/world/entities/entity_000002").json()["attributes"]["resources"][
            "wood"
        ]
        == 120
    )


def test_inspection_is_get_only_and_does_not_expand_npc_context() -> None:
    engine, client = make_client()

    assert all(
        route.methods <= {"GET"}
        for route in client.app.routes
        if getattr(route, "path", "").startswith("/world")
    )
    assert client.post("/world").status_code == 405

    raw_tree = client.get("/world/entities/entity_000002").json()
    assert raw_tree["attributes"]["resources"]["wood"] == 120

    context = NPCContextAssembler(engine.state).assemble(holder_id="entity_000001")
    npc_information = "\n".join(context.retrieved_information)
    assert "120" not in npc_information
    assert "92" not in npc_information
