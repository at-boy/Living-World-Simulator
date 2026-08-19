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
| `GET /world/placements` | Canonically ordered exact spatial placements |
| `GET /world/external-references` | External anchors and exact engine policy |
| `GET /world/external-dispatches` | Durable dispatch records and lifecycle |
| `GET /world/events` | World events |
| `GET /world/npcs` | NPC identity, occupation, schedule, and active activity presentation |
| `GET /world/observations` | Persisted observations |
| `GET /world/memories` | Persisted memories and provenance |
| `GET /world/knowledge` | Persisted knowledge and provenance |
| `GET /world/beliefs` | Persisted beliefs, history, and provenance |
| `GET /world/experiences` | Persisted experiences, history, and provenance |
| `GET /world/cognitive-history/{holder_id}` | Holder-scoped cognitive records, or `404` if the holder is unknown |

Collection routes return `[]` when no records exist. Existing record
collections are ordered deterministically by record identifier; placements use
ADR-0016's canonical container/geometry/entity order. A known holder with no
cognitive records receives a response whose category collections are empty.

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

# Spatial placements

`GET /world/placements` returns the dedicated spatial placement collection in
canonical container/geometry/entity order. Each detached record contains the
entity ID, optional containing entity ID, geometry (`null`, point, or bounds),
optional bounds kind, and overlap policy. `/world` includes `placement_count`.

This is privileged exact engine geometry. It is not an NPC perception or
context payload and must not be passed to cognition.

# External-world references

`GET /world/external-references` returns detached records in lexical ID order;
`/world` includes `external_world_reference_count`. Internal IDs and exact
goods, capacity, delay, cost, reliability, and contact state are privileged
operator data and must never be copied into an NPC prompt or context.

`GET /world/external-dispatches` returns detached records in lexical ID order;
`/world` includes `external_dispatch_count`. Source/reference IDs, reservations,
ticks, and exact state are privileged and must not be used as NPC context.
# Goal inspection

`GET /world/goals` returns a deterministic, detached privileged snapshot of
goal definitions, lifecycle state, objectives, typed criteria, and evidence.
This operator endpoint is not an NPC-context or mutation interface.
