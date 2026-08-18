# HTTP inspection API

The HTTP inspection API is a privileged, read-only view of a running
`SimulationEngine`. It returns detached JSON snapshots of authoritative world
state for operator tools, debugging, and visualization.

## Run the standalone development application

Install the development dependencies, then start the bundled empty in-memory
world on the loopback interface:

```bash
make install
.venv/bin/uvicorn living_world.api.server:app --host 127.0.0.1 --port 8000
```

This module-level application owns a newly created `SimulationEngine`; it is
useful for checking the API but is not connected to another process or an
already-running simulation. Open <http://127.0.0.1:8000/docs> for FastAPI's
interactive route documentation, or query it directly:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/world
curl http://127.0.0.1:8000/world/entities
```

## Attach the API to an application engine

Applications should pass their engine to `create_app` and serve the returned
ASGI application. For example:

```python
import uvicorn

from living_world.api.server import create_app
from living_world.simulation.simulation_engine import SimulationEngine


engine = SimulationEngine()
# Compose or load the world here, then retain this engine for simulation.
inspection_app = create_app(engine)

uvicorn.run(inspection_app, host="127.0.0.1", port=8000)
```

`create_app(engine)` reads the current state of that same engine for every
request. `examples/013_world_inspection.py` and
`examples/023_http_inspection.py` demonstrate in-process requests against a
composed world without opening a network port.

## Routes

| Route | Result |
| --- | --- |
| `GET /health` | Service status and version |
| `GET /world/tick` | Current simulation tick |
| `GET /world/run` | Scenario run metadata, or `404` for an unbound world |
| `GET /world` | Counts for the principal world-state collections |
| `GET /world/entities` | All entities |
| `GET /world/entities/{entity_id}` | One entity, or `404` if unknown |
| `GET /world/definitions` | Entity definitions |
| `GET /world/resources` | Resource definitions |
| `GET /world/relationships` | World relationships |
| `GET /world/events` | World events |
| `GET /world/npcs` | NPC identity, occupation, schedule, and active activity presentation |
| `GET /world/observations` | Persisted observations |
| `GET /world/memories` | Persisted memories and provenance |
| `GET /world/knowledge` | Persisted knowledge and provenance |
| `GET /world/beliefs` | Persisted beliefs, history, and provenance |
| `GET /world/experiences` | Persisted experiences, history, and provenance |
| `GET /world/cognitive-history/{holder_id}` | Holder-scoped cognitive records, or `404` if the holder is unknown |

Collection routes return `[]` when no records exist. Collections are ordered
deterministically by record identifier. A known holder with no cognitive
records receives a response whose category collections are empty.

`/world` includes a `run` object for scenario-bound worlds and `null` for
legacy or manually composed worlds. The fingerprint and seed are privileged
operator diagnostics and must never be copied into NPC-facing context.

For example, after obtaining an NPC identifier from `/world/npcs`:

```bash
curl http://127.0.0.1:8000/world/cognitive-history/entity_000001
```

## Security and information boundary

The API deliberately exposes authoritative attributes, internal identifiers,
record histories, and provenance. It has no authentication or authorization
layer of its own, so bind it to loopback or place it behind access controls
appropriate to the embedding application. Do not expose it as an unprotected
public service.

Inspection responses are operator output only. Never pass them into NPC
prompts, `NPCContext`, cognitive retrieval, perception, or cognition clients.
The API is GET-only and does not step or mutate the simulation. Conversations,
meetings, councils, invitation feedback, and action-resolution return values
are ephemeral and therefore have no inspection routes.
