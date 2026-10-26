# HTTP inspection API

Release candidate `0.6.0rc1`: see [release notes](releases/v0_6_0rc1.md)
and [current closeout evidence](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).

`GET /world/work-orders` returns detached ID-ordered work definition/state pairs
with ID-ordered reservation history. `/world` includes work and reservation
counts. This privileged data is not NPC context.

`GET /world/consequences` returns detached privileged consumption, storage, and
maintenance policy/state pairs ordered by policy ID. `GET /world` includes a
count for each policy type. These operator surfaces are not NPC-visible.

`GET /world/needs` returns privileged ID-ordered records shaped exactly as
`{"definition": <NeedDefinition>, "state": <NeedState>}`. `GET /world` includes
`need_count`; these operator views may expose exact thresholds and history.

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

## Packaged browser inspector

`GET /inspector` serves the packaged read-only World Inspector. Its fixed CSS
and JavaScript assets are served under `/inspector/assets/`; unknown assets
return 404 and mutating methods return 405. See [World Inspector](world_inspector_ui.md)
for view sources, independent snapshot semantics, browser verification and the
extension entry points. The module-level server owns an empty engine; an app
created with `create_app(engine)` reads that supplied engine. A separately loaded
database remains a snapshot rather than synchronizing another process.

## Packaged Spatial inspector

The packaged `/inspector` Spatial view consumes the existing detached
`GET /world/placements` and entity snapshots. Placement ordering and geometry
remain engine-owned. The browser adds no endpoints or mutating operations and
makes no atomic consistency claim across requests. See [World Inspector](world_inspector_ui.md)
for projection, accessibility, unplaced states and numeric-range handling.

## Saved-world serving

The public `load_inspection_engine(scenario_path, database_path)` factory requires
saved metadata, validates exact scenario identity and opens SQLite in read-only
mode. Canonical setup must already exist. `create_app(engine)` then exposes the
same GET-only API against that fixed snapshot. CLI serving binds only loopback;
install the optional `server` extra. Ordinary same-engine live reads remain
available by supplying the running engine directly to `create_app`.

## Reusable pinned revision inspection

`living_world.api.inspection_routes.create_inspection_router(resolve_inspector)`
provides the same ordered GET-only world routes as `create_app(engine)`. Its
synchronous resolver receives the request (including prefix path parameters),
runs in FastAPI's worker thread and resolves one `WorldInspector` per request.
Trusted embedding applications can mount the router under a server-chosen
prefix. Health and packaged inspector routes remain with `create_app`; packaged
assets and their default API URLs are unchanged. Root construction attaches the
router's concrete routes before startup to preserve the existing flat route
inventory with FastAPI's lazy router inclusion.

`living_world.api.revision_source.RevisionSource(catalog, controller=None)` opens
an explicit `(attempt_id, revision)` through `.open(...)`. Each miss validates
the archive and reconstructs the exact retained world with the shared pure
archived-inspection loader. No runner, provider, lease, controller publication
cache, initialization or step is used. The optional controller association is
validated but does not grant access to live owner state. Failed, stopped and
interrupted attempts remain inspectable when they have a complete valid world.

The per-source cache serializes reconstruction and retains at most eight exact
revision views in least-recently-used order. Views are detached from the live
owner and immutable by convention; callers must use the read-only inspector
interface. Failed misses preserve valid cached entries. A cached view remains
the previously validated revision; external archive tampering is detected on a
later miss, without source repair. Archive handles are closed before returning.

`RevisionSourceError.code` and its message are fixed safe values: `not_found`
for invalid identity/revision, unknown attempts or absent checkpoints/worlds;
`archive_invalid` for identified corrupt/incomplete archives, duplicate identity,
inaccessible catalog storage or failed exact reconstruction. The source never
creates missing storage or changes source files, timestamps or directory entries.
These are Python producer interfaces only. Authenticated operator routes,
controls and browser prefix wiring use the privileged adapter below. Source reads
remain fixed and do not expose NPC context.

## Authenticated local runtime operator application

`living_world.api.operator.create_operator_app(service, controller, auth=session)`
creates a separate privileged loopback application. The caller constructs and starts
`RuntimeService` explicitly; HTTP handlers never construct, poll, or step a runner.
The optional controller must be the service's current controller. Passing `None`
allows an archive-only or not-yet-ready application. App shutdown joins the service
and its provider resources; closing a browser or requesting a view does not stop it.
The existing `create_app` application and its public inspection URLs are unchanged.
The packaged `/runtime` browser page uses this application. The public `serve`
command below owns its local HTTP lifetime.

Create `AdminSession.issue(origin="http://127.0.0.1:8000")` for the actual listening
origin. Configured origins are credential-free loopback HTTP(S), canonicalized to
lowercase with default ports removed; incoming `Origin` must match exactly. Token
and independent CSRF nonce live only in memory. Keep them out of URLs, cookies,
logs, archives, browser storage, and command bodies. Every protected operator request needs
`Authorization: Bearer <token>`. GET may omit `Origin`; a present foreign origin is
forbidden. POST also requires exact `Origin` and `X-CSRF-Token`. Authenticated status
returns that nonce in its `X-CSRF-Token` response header for an in-memory client.
All responses use `Cache-Control: no-store`; no CORS permissions are installed.

| Route | Result |
| --- | --- |
| `GET /runtime/status` | `live: null`, or one immutable last-durable status plus cached nonsecret mode, scenario, model name/digest and configuration error |
| `POST /runtime/commands` | Exact `command_id`, `action`, `expected_state_version` envelope submitted through the service |
| `GET /runtime/commands/{command_id}` | Current-attempt durable receipt, including opaque IDs containing slashes |
| `GET /archives` | Catalog summaries including unsuccessful, interrupted, setup-only, and corrupt discoveries |
| `GET /archives/{attempt_id}` | Summary, configuration/source, latest recorded outcome, total journal count and last 50 typed entries |
| `GET /archives/{attempt_id}/checkpoints` | Ascending complete revision/tick metadata; valid attempts without worlds return an empty list |
| `GET /archives/{attempt_id}/checkpoints/{revision}/world...` | Existing world DTO routes pinned to that exact retained revision |
| `GET /live/checkpoints/{revision}/world...` | Same pinned DTO routes for the current service attempt |

Command actions are `pause`, `resume`, `step`, `stop`, and explicit `retry`.
`expected_state_version` is an operational state version, not a checkpoint revision.
Admission is awaited asynchronously: queued receipts return 202, applied receipts
200, and rejected receipts 409. A queued Pause/Step receipt acknowledges durable
admission; only a later applied receipt acknowledges the effect and its checkpoint.
The same envelope and stable command ID safely rediscover its durable receipt;
reusing an ID for a different envelope returns `command_conflict`. Provider errors
require explicit Retry. No HTTP start/resume-from-archive/fork construction endpoint
exists. After client cancellation, discover the receipt or resubmit the same envelope.

Known valid attempts without worlds expose requested setup configuration or retained
reservation configuration without inventing a checkpoint or successful preflight.
Configuration-source labels are `archive`, `requested`, or `reservation`. Outcomes
are the latest `attempt_finished` value, which may be null; they are not inferred
success flags. Physical corruption returns 409 `archive_invalid` while list discovery
retains the row. Unknown identities/revisions return 404 `not_found`. Authentication
failures use fixed 401 `unauthorized` or 403 `forbidden`; malformed command bodies
use 422 `invalid_command`. No protected archive reconstruction occurs before auth.

Pinned history uses the shared readonly revision source, reloads exact evicted
revisions from the archive, and neither advances the world nor invokes a model.
These privileged operator records must never become NPC context. Initial metadata
and archive scans run off the event loop. This bounded initial API favors correctness
over optimizing long archive histories.


## Local runtime page

`GET /runtime` is a public, secret-free login page. Public
`GET /runtime/assets/runtime.css` and `runtime.js` serve only these two allowlisted
packaged assets. Page/resource reads run outside the event loop and retain no-store
headers. A GET never constructs or starts a world.

The page keeps the token, validated status-header CSRF nonce and command envelopes
only in closure memory. Disconnect/page exit clears them, cancels requests and
removes the child inspector; admitted server work may still complete. Status polls
run serially, one second after the previous cycle. Failed status refresh leaves the
last complete data visibly stale and disables mutation. Authentication failures or
invalid nonces clear the session. Neither browser storage nor query parameters
carry credentials.

Commands use the reported operational state version. Queued receipts acknowledge
admission only; receipt GETs discover durable applied/rejected results. An uncertain
POST keeps the exact original envelope. Only explicit **Retry delivery** resends it,
with the same ID/version/action; no automatic POST retry occurs. **Retry model** is a
separate explicit runtime action. Duplicate action clicks are suppressed while that
action is outstanding, while a permitted Pause remains available during Step.

The archive list fetches actual detail outcomes through one shared two-request
limit across background loading, selection, refresh and reconnect. Current-generation
requests/cache are shared by attempt; obsolete queued work is canceled, while active
reads retain capacity until they settle. Catalog order and unavailable/corrupt rows
are retained. Each row shows start time,
parent attempt/checkpoint and last committed tick without requiring selection.
Lifecycle never substitutes for outcome. Detail views show configuration source,
latest 50 typed entries and total journal size. Archive-only and no-world attempts
remain inspectable without fabricated checkpoints. History selects a fixed complete
checkpoint and hides live mutation controls. All archive activity is authenticated
GET-only. The existing service/API/child protocols and NPC boundary are unchanged.


## Public local serving

Install the optional `living-world-simulator[server]` extra, then launch:

```console
living-world serve --founders success --admin-token-file /existing/private/session-token --port 0
living-world serve --preset founders --driver ollama --model MODEL --admin-token-file /existing/private/session-token
living-world serve --resume-attempt UUID --admin-token-file /existing/private/session-token
living-world serve --fork-attempt UUID --checkpoint 1 --admin-token-file /existing/private/session-token
```

The server binds only `127.0.0.1`; `--port 0` selects an available port. Open the
printed `runtime_url` and enter the token from the selected file into the local
page. The file contains the token plus a newline, is exclusively created with
permissions `0600`, and requires existing parent directories. Existing files and
symlink components are rejected. Keep the destination outside the archive catalog
and any `--database` compatibility mirror; ancestors of either are also rejected.
The command removes its file on exit only while the original identity, ownership,
permissions, link count and contents still match. Modified or replaced files are
preserved. The final identity check followed by unlink is best effort against a
concurrent process running as the same user; it is not an atomic inode unlink.

Without `--admin-token-file`, both output streams must be interactive terminals;
the token then appears once on local stderr. Redirecting either stream requires
the explicit file. A supplied file suppresses terminal token output. Never put
the token in a URL or process argument. The CSRF nonce remains in memory and the
existing authenticated response header. Neither credential belongs in archives,
configuration, logs or browser storage.

HTTP readiness precedes world launch, so a slow provider preflight can show
`live: null` while saved archives remain available. The printed URL indicates HTTP
readiness; an attempt announcement indicates allocation. Only durable runtime
status indicates world readiness. Fresh worlds start paused at their initial
checkpoint. `--start-running` opts into automatic progression. Finite completion,
Stop, provider error pause and failed setup leave the browser/catalog available
until SIGINT/SIGTERM or the injected stop control. Provider error pause keeps the
existing explicit Retry action; browser refresh, reads and Disconnect never Stop.

For an intentional partial recorded tape use, for example:

```console
living-world serve --founders success --max-ticks 1 --checkpoint-only --start-running --admin-token-file /existing/private/session-token
```

`--checkpoint-only` is accepted only for a fresh recorded `--founders` target. It
retains unfinished tape entries for restart and persists `finalize_proposals=false`;
resume/fork inherit their source configuration. Without this flag, full tape
finalization retains its existing unused-entry validation. It is not a way to
change a live provider's behavior.

Serving uses separate non-daemon HTTP and launch threads; RuntimeService remains
the only world mutation/lease owner. The main thread owns signal handling and
cooperative shutdown. It first joins the service while HTTP is available, then
requests HTTP shutdown and separately joins HTTP (12 seconds) and launch (6
seconds). Cleanup failure is an error, and an uncooperative surviving non-daemon
thread can keep the process alive; there is no forced termination guarantee.
Final archive/mirror failure overrides apparently successful world completion.
All normal attempts, including setup failures, are retained.

Serving accepts the existing target/provider/budget flags, plus the credentials,
port and initial-running options described above. It has no arbitrary scenario,
proposal tape, replay, host, reload, workers, remote binding or HTTP world-launch
option. `--database` remains a compatibility mirror. Credential failures use
`credential_file_failed` (exit 4); optional server absence uses `server_unavailable`
(exit 2); HTTP failures use `server_failed` (exit 5), and cleanup/control failures
use `service_failed` (exit 5). Existing runtime failures retain their closed error
mapping. `run` and read-only `inspect` retain their existing behavior.
