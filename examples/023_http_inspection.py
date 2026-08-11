"""Inspect persisted NPC cognition without exposing it to NPC reasoning."""

import asyncio
import json
from collections.abc import Mapping

from fastapi import FastAPI

from living_world.api.server import create_app
from living_world.core.definition import Definition
from living_world.core.memory import CognitiveSalience
from living_world.simulation.simulation_engine import SimulationEngine


def get_json(app: FastAPI, path: str) -> object:
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
    engine.definitions.register_many((Definition(key="npc"), Definition(key="well")))
    caretaker = engine.entities.create(
        definition_key="npc",
        name="Mara",
        attributes={
            "npc_identity": {
                "name": "Mara",
                "description": "A patient well caretaker.",
                "capability_descriptions": ["Recognizes changes in water quality."],
            },
            "occupation": {
                "title": "Well caretaker",
                "description": "Maintains the public well.",
            },
            "schedule": [{"start_tick": 0, "end_tick": 8, "activity": "working"}],
        },
    )
    well = engine.entities.create(definition_key="well", name="Public Well")
    observation = engine.observations.record(
        observer=caretaker.id,
        subject=well.id,
        description="The public well water looks cloudy.",
        confidence=0.9,
    )
    salience = CognitiveSalience(importance=0.8, is_core=True)
    memory = engine.memories.record(
        holder_id=caretaker.id,
        subject_id=well.id,
        summary="The well became cloudy after heavy rain.",
        salience=salience,
        source_observation_ids=(observation.id,),
    )
    experience = engine.experiences.record(
        holder_id=caretaker.id,
        subject_id=well.id,
        summary="Heavy rain can disturb the public well.",
        supporting_observations=(observation.id,),
        supporting_memories=(memory.id,),
        salience=salience,
    )
    engine.beliefs.record_from_experience(
        experience=experience,
        proposition="The well should be checked after storms.",
        confidence=0.8,
        importance=0.8,
        status="core",
    )
    engine.knowledge.record(
        holder_id=caretaker.id,
        subject_id=well.id,
        statement="The well was cloudy this morning.",
        source_description="From inspecting the water.",
        salience=salience,
        supporting_observations=(observation.id,),
    )
    engine.npc_relationships.record(
        holder_id=caretaker.id,
        subject_id=well.id,
        summary="I am responsible for maintaining this well.",
        salience=salience,
        source_observation_ids=(observation.id,),
    )

    app = create_app(engine)
    print("World summary:", get_json(app, "/world"))
    print("NPC presentation:", get_json(app, "/world/npcs"))
    print("Memories:", get_json(app, "/world/memories"))
    print("Knowledge:", get_json(app, "/world/knowledge"))
    print(
        "Mara's persisted cognitive history:",
        get_json(app, f"/world/cognitive-history/{caretaker.id}"),
    )


if __name__ == "__main__":
    main()
