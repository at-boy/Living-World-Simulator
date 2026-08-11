import asyncio
import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from living_world import __version__
from living_world.api.inspection import EngineWorldInspector, WorldInspector
from living_world.api.server import create_app
from living_world.cognition.npc_context import NPCContextAssembler
from living_world.cognition.retrieval import RetrievalQuery
from living_world.core.belief import Belief, BeliefStatus
from living_world.core.definition import Definition
from living_world.core.event import Event
from living_world.core.experience import Experience
from living_world.core.knowledge import Knowledge
from living_world.core.memory import CognitiveSalience, Memory
from living_world.core.npc_relationship import NPCRelationship
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

    npc = engine.entities.create(
        definition_key="npc",
        name="Erik",
        attributes={
            "npc_identity": {
                "name": "Erik",
                "description": "A careful forester.",
                "capability_descriptions": ["Reads the health of trees."],
            },
            "occupation": {
                "title": "Forester",
                "description": "Tends the grove.",
            },
            "schedule": [{"start_tick": 0, "end_tick": 8, "activity": "working"}],
            "active_activity": "working",
        },
    )
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
    for suffix, summary in (
        ("000002", "The oak shelters the path."),
        ("000001", "The oak survived winter."),
    ):
        engine.memories.add(
            Memory(
                id=f"memory_{suffix}",
                tick=0,
                holder_id=npc.id,
                subject_id=tree.id,
                summary=summary,
                salience=CognitiveSalience(importance=0.7),
                source_observation_ids=("observation_000001",),
            )
        )
    for suffix, statement in (
        ("000002", "The grove has shelter."),
        ("000001", "The oak survived winter."),
    ):
        engine.knowledge.add(
            Knowledge(
                id=f"knowledge_{suffix}",
                tick=0,
                holder_id=npc.id,
                subject_id=tree.id,
                statement=statement,
                source_description="From time in the grove.",
                salience=CognitiveSalience(importance=0.7),
                metadata={"nested": {"safe": [True]}},
            )
        )
    for suffix, summary in (
        ("000002", "I trust this tree."),
        ("000001", "I know this tree."),
    ):
        engine.npc_relationships.add(
            NPCRelationship(
                id=f"npc_relationship_{suffix}",
                tick=0,
                holder_id=npc.id,
                subject_id=tree.id,
                summary=summary,
                salience=CognitiveSalience(importance=0.7),
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

    assert client.get("/health").json() == {"status": "ok", "version": __version__}
    assert client.get("/world/tick").json() == {"tick": 0}
    assert client.get("/world").json() == {
        "tick": 0,
        "entity_count": 2,
        "relationship_count": 2,
        "event_count": 2,
        "observation_count": 2,
        "memory_count": 2,
        "knowledge_count": 2,
        "belief_count": 2,
        "experience_count": 2,
        "npc_relationship_count": 2,
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
        ("/world/memories", "memory"),
        ("/world/knowledge", "knowledge"),
        ("/world/beliefs", "belief"),
        ("/world/experiences", "experience"),
    ):
        response = client.get(endpoint)
        assert response.status_code == 200
        assert [record["id"] for record in response.json()] == [
            f"{prefix}_000001",
            f"{prefix}_000002",
        ]

    assert client.get("/world/npcs").json() == [
        {
            "id": "entity_000001",
            "identity": {
                "name": "Erik",
                "description": "A careful forester.",
                "capability_descriptions": ["Reads the health of trees."],
            },
            "occupation": {
                "title": "Forester",
                "description": "Tends the grove.",
            },
            "schedule": [{"start_tick": 0, "end_tick": 8, "activity": "working"}],
            "active_activity": "working",
        }
    ]
    assert client.get("/world/memories").json()[0]["source_observation_ids"] == [
        "observation_000001"
    ]
    assert client.get("/world/knowledge").json()[0]["metadata"] == {
        "nested": {"safe": [True]}
    }
    belief = client.get("/world/beliefs").json()[0]
    assert belief["supporting_observations"] == []
    assert belief["history"] == []
    experience = client.get("/world/experiences").json()[0]
    assert experience["supporting_memories"] == []
    assert experience["history"] == []


def test_release_version_surfaces_are_consistent() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    version_file = (repository_root / "VERSION").read_text(encoding="utf-8").strip()
    with (repository_root / "pyproject.toml").open("rb") as metadata_file:
        project_version = tomllib.load(metadata_file)["project"]["version"]
    _, client = make_client()

    assert version_file == "0.5.0"
    assert project_version == version_file
    assert __version__ == version_file
    assert client.get("/health").json() == {
        "status": "ok",
        "version": version_file,
    }


def test_cognitive_history_is_holder_scoped_ordered_and_handles_empty_holders() -> None:
    engine, client = make_client()

    other_holder = engine.entities.create(definition_key="npc", name="Liv")
    engine.memories.add(
        Memory(
            id="memory_000003",
            tick=0,
            holder_id=other_holder.id,
            subject_id="entity_000002",
            summary="Only Liv remembers the lightning strike.",
            salience=CognitiveSalience(importance=1.0, is_core=True),
        )
    )

    history = client.get("/world/cognitive-history/entity_000001")
    assert history.status_code == 200
    payload = history.json()
    assert payload["holder_id"] == "entity_000001"
    assert list(payload) == [
        "holder_id",
        "observations",
        "memories",
        "knowledge",
        "beliefs",
        "experiences",
        "npc_relationships",
    ]
    for category, prefix in (
        ("observations", "observation"),
        ("memories", "memory"),
        ("knowledge", "knowledge"),
        ("beliefs", "belief"),
        ("experiences", "experience"),
        ("npc_relationships", "npc_relationship"),
    ):
        assert [record["id"] for record in payload[category]] == [
            f"{prefix}_000001",
            f"{prefix}_000002",
        ]
    assert "lightning strike" not in json.dumps(payload)
    context = NPCContextAssembler(engine.state).assemble(
        holder_id="entity_000001",
        query=RetrievalQuery(holder_id="entity_000001", topic="oak"),
    )
    npc_text = tuple(
        record.text for record in context.core_cognition + context.retrieved_information
    )
    assert npc_text
    assert all("lightning strike" not in text for text in npc_text)

    empty_holder = engine.entities.create(definition_key="npc", name="Sven")
    empty = client.get(f"/world/cognitive-history/{empty_holder.id}")
    assert empty.status_code == 200
    assert all(
        not records for key, records in empty.json().items() if key != "holder_id"
    )
    assert client.get("/world/cognitive-history/missing").status_code == 404


def test_empty_inspection_collections_return_arrays() -> None:
    client = ASGIClient(create_app(SimulationEngine()))

    for endpoint in (
        "/world/npcs",
        "/world/observations",
        "/world/memories",
        "/world/knowledge",
        "/world/beliefs",
        "/world/experiences",
    ):
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json() == []


def test_world_inspector_protocol_declares_the_complete_surface() -> None:
    inspector: WorldInspector = EngineWorldInspector(SimulationEngine())

    assert inspector.npcs() == ()
    assert inspector.memories() == ()
    assert inspector.knowledge() == ()
    assert inspector.cognitive_history("missing") is None


def test_inspection_payloads_are_detached_from_world_state() -> None:
    engine, client = make_client()

    payload = client.get("/world/entities/entity_000002").json()
    payload["attributes"]["resources"]["wood"] = 0

    assert (
        client.get("/world/entities/entity_000002").json()["attributes"]["resources"][
            "wood"
        ]
        == 120
    )

    history = client.get("/world/cognitive-history/entity_000001").json()
    history["knowledge"][0]["metadata"]["nested"]["safe"][0] = False
    assert client.get("/world/knowledge").json()[0]["metadata"]["nested"]["safe"] == [
        True
    ]

    inspector = EngineWorldInspector(engine)
    knowledge = inspector.knowledge()[0]
    metadata = knowledge["metadata"]
    assert isinstance(metadata, dict)
    nested = metadata["nested"]
    assert isinstance(nested, dict)
    safe = nested["safe"]
    assert isinstance(safe, list)
    safe[0] = False

    state_metadata = engine.state.knowledge["knowledge_000001"].metadata
    assert state_metadata["nested"]["safe"] == (True,)
    fresh_metadata = inspector.knowledge()[0]["metadata"]
    assert fresh_metadata == {"nested": {"safe": [True]}}

    history = inspector.cognitive_history("entity_000001")
    assert history is not None
    memories = history["memories"]
    assert isinstance(memories, list)
    source_ids = memories[0]["source_observation_ids"]
    assert isinstance(source_ids, list)
    source_ids.append("observation_changed")
    assert engine.state.memories["memory_000001"].source_observation_ids == (
        "observation_000001",
    )
    fresh_history = inspector.cognitive_history("entity_000001")
    assert fresh_history is not None
    assert fresh_history["memories"][0]["source_observation_ids"] == [
        "observation_000001"
    ]


def test_inspection_is_get_only_and_does_not_expand_npc_context() -> None:
    engine, client = make_client()

    assert all(
        route.methods <= {"GET"}
        for route in client.app.routes
        if getattr(route, "path", "").startswith("/world")
    )
    assert client.post("/world").status_code == 405
    paths = {route.path for route in client.app.routes}
    assert "/world/conversations" not in paths
    assert "/world/councils" not in paths

    raw_tree = client.get("/world/entities/entity_000002").json()
    assert raw_tree["attributes"]["resources"]["wood"] == 120

    context = NPCContextAssembler(engine.state).assemble(holder_id="entity_000001")
    npc_information = "\n".join(context.retrieved_information)
    assert "120" not in npc_information
    assert "92" not in npc_information
