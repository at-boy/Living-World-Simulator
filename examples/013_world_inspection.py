import asyncio
import json
from collections.abc import Mapping

from fastapi import FastAPI

from living_world.api.server import create_app
from living_world.core.definition import Definition
from living_world.core.resource_definition import ResourceDefinition
from living_world.simulation.simulation_engine import SimulationEngine


def get_json(app: FastAPI, path: str) -> object:
    """Make an in-process HTTP GET request to the inspection application."""

    return asyncio.run(_get_json(app, path))


async def _get_json(app: FastAPI, path: str) -> object:
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

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("example", 50000),
            "server": ("example", 80),
        },
        receive,
        send,
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return json.loads(body)


def main() -> None:
    engine = SimulationEngine()
    engine.definitions.register_many(
        (
            Definition(key="npc"),
            Definition(key="tree", initial_attributes={"resources": {"wood": 120}}),
        )
    )
    engine.resource_definitions.register(ResourceDefinition(key="wood"))

    ranger = engine.entities.create(definition_key="npc", name="Erik")
    oak = engine.entities.create(definition_key="tree", name="Old Oak")
    engine.relationships.create(kind="observes", source_id=ranger.id, target_id=oak.id)
    engine.events.record(kind="world_initialized", subject_id=oak.id)
    observation = engine.observations.record(
        observer=ranger.id,
        subject=oak.id,
        description="The Old Oak appears mature.",
        confidence=0.8,
    )
    experience = engine.experiences.record(
        holder_id=ranger.id,
        subject_id=oak.id,
        summary="Old oaks provide reliable timber.",
        supporting_observations=(observation.id,),
    )
    engine.beliefs.record_from_experience(
        experience=experience,
        proposition="The Old Oak is a valuable resource.",
        confidence=0.8,
        importance=0.7,
        status="important",
    )

    app = create_app(engine)
    print("World summary:", get_json(app, "/world"))
    print("Old Oak snapshot:", get_json(app, f"/world/entities/{oak.id}"))
    print("Events:", get_json(app, "/world/events"))


if __name__ == "__main__":
    main()
