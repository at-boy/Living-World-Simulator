# World Inspector

Release candidate `0.6.0rc1`: see [release notes](releases/v0_6_0rc1.md)
and [current closeout evidence](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).

Open `/inspector` on the read-only FastAPI inspection application. The packaged
page uses same-origin GET requests and contains no simulation controls. Refresh
fetches new reported snapshots and never advances the engine. Each endpoint is
an independent snapshot; a view assembled from several endpoints is not atomic.
The header labels the summary's tick as **Reported tick**.

The module-level `living_world.api.server:app` owns a new empty world. To inspect
a composed simulation, serve `create_app(engine)` with that same supplied engine.
A separately loaded database is a snapshot and will not follow another process.
Task 23 delivers the saved-world inspection CLI composition described below.

## Views

| View | Reported sources |
| --- | --- |
| Overview | World counts, run metadata (404 means unbound), replay binding/cursor |
| Entities | Names, definitions, lifecycle, attributes and exact matching references |
| Spatial | Existing placements and entity snapshots, projected map, complete placement/lifecycle list |
| Relationships | Direct kind/source/target/lifecycle, known entity names and ID fallback |
| Resources | Resource definitions and explicit entity `attributes.resources` quantities |
| Needs | Definitions, nullable current assessments/history, consequence policies/state |
| Goals | Definition/state, objectives, dependencies, criteria and evidence event links |
| Work | Definition/state/reservations, progress, assignments, prerequisites and reasons |
| External connections | Reference policies and dispatch lifecycles |
| Stages | Managed stage state, program requirements and transition fields |
| History | Events sorted by (tick, ID), text filter and referenced-event selection |

No completion, stock, reservation subtraction, stage promotion or run success is
calculated in the browser. Absent stock quantities are not zero. Raw field names
and nested details preserve the API's exact records, including null and empty
collections. Entity detail fetches the existing GET collections and selects
records containing exact entity-reference fields, without creating an aggregate
inspection API. Evidence buttons open History with the referenced event selected;
Show all history clears that selection. A missing event gives a no-match state.

Navigation and Refresh work with keyboard controls. View changes focus the view
heading. Loading uses `aria-busy` and a live status region. Narrow screens wrap
navigation and keep field tables in horizontally scrollable containers. The
page distinguishes loading, empty, missing, unavailable and malformed snapshots.
Unsupported numeric ranges display the malformed/unsupported state instead of
asserting rounded quantities. Failure prose never includes provider payloads.

## Packaging and development verification

HTML, CSS and JavaScript ship as explicit `living_world.api` package data. There
is no Node project, framework, CDN or browser-side runtime dependency. Routes are
`GET /inspector` and the two fixed `/inspector/assets/inspector.{css,js}` files.
Unknown assets return 404; mutating methods return 405.

Install the optional `browser-tests` extra to run typed Python Playwright tests.
They launch installed `/usr/bin/google-chrome` headless in an isolated context;
`LIVING_WORLD_BROWSER_EXECUTABLE` selects another installed supported executable.
Tooling or browser absence has an explicit portability skip. Approval requires
an actual supported-browser run. The tests serve real `create_app` responses to
Chrome through an ASGI transport and exercise actual DOM behavior, request
methods and before/after engine state. The root orchestrator separately checks
an installed wheel's asset contents and full repository gates.

## Spatial view

Spatial consumes only `GET /world/placements`, `GET /world/entities` and the
usual world summary. These remain independent snapshots; an entity reference
missing from the fetched entities is a malformed response. Refresh can retry
if the world changed between requests. The browser never generates placements.

The map displays +x east/right and +y north/up. Point `(x,y)` becomes SVG
`(x,-y)`; bounds begin at `(x,-(y+height))`. The view box includes all reported
geometry endpoints, minimum spans of one unit, and padding of one tenth of the
larger span. Marker radius is that larger span divided by 100; upright label
font size is the same span divided by 20. Padding, marker size and physical
scale describe presentation, not engine geometry. Resizing preserves the view
box, geometry and ordering. Unsafe integer coordinates, dimensions, endpoints,
extent differences or center numerator sums show **Unsupported spatial numeric
range.** No partial map or rounded coordinate details are shown on failure. Unknown
extra fields must also pass recursive numeric safety checks; safe extras display
literally, while unsafe or nonfinite extra quantities are malformed.

The dedicated renderer preserves backend placement order for marks, labels and
placed records. Translucent area/structure bounds can overlap. Every mark is a
keyboard button (Enter or Space); the complete list gives each entity a regular
button regardless of overlap. Reported containment, bounds kind, overlap policy,
coordinates and lifecycle remain visible in structured details. Explicit null
geometry is **Unplaced**, in backend order; entities without any placement record
follow in entity-ID order as **No placement record**. Neither receives a map
marker. Empty/all-unplaced geometry has an empty map message.

Spatial entity activation returns through **Back to Spatial**; detail Refresh,
missing-entity errors and the current-navigation marker preserve that origin.
Existing entity entry points retain **Back to Entities**. Names and details are
literal text, including HTML-shaped names. The map and list are operator output
and never supply NPC perception or cognition.

`inspector.js` separates closed-route `fetchSnapshot`/validators, DOM helpers,
the `views` registry, and the dedicated `renderSpatial` renderer. Generic
`renderRecords` sorts IDs and must not be used for placement order.
`openEntityDetail(id, returnView="Entities")` is the compatible drill-down entry
point. Extensions preserve the `show` generation guard and focus/status handling.

Inspector data is privileged operator output. It does not flow into NPC context,
retrieval, cognition, perception or action resolution. Use the API's existing
loopback/access-control guidance when serving the application.

## Saved canonical snapshots

`living-world inspect --founders --database outcome.sqlite3` loads a validated
existing canonical snapshot through a read-only SQLite repository and serves it
at loopback. The optional `server` extra supplies uvicorn. The snapshot does not
advance or refresh automatically from another running process; all inspector
routes continue to be GET-only. See [canonical founders](canonical_founders.md).
