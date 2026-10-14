# World Inspector

Open `/inspector` on the read-only FastAPI inspection application. The packaged
page uses same-origin GET requests and contains no simulation controls. Refresh
fetches new reported snapshots and never advances the engine. Each endpoint is
an independent snapshot; a view assembled from several endpoints is not atomic.
The header labels the summary's tick as **Reported tick**.

The module-level `living_world.api.server:app` owns a new empty world. To inspect
a composed simulation, serve `create_app(engine)` with that same supplied engine.
A separately loaded database is a snapshot and will not follow another process.
Task 23 owns the convenient saved-world inspection CLI composition.

## Views

| View | Reported sources |
| --- | --- |
| Overview | World counts, run metadata (404 means unbound), replay binding/cursor |
| Entities | Names, definitions, lifecycle, attributes and exact matching references |
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

## Spatial extension entry points

`inspector.js` separates `fetchSnapshot`/validators, DOM helpers (`renderValue`,
`renderRecords`) and the `views` registry. Task 15c can register Spatial with a
closed route key, validator, source list and renderer. `openEntityDetail(id)` is
the existing drill-down entry point. Preserve the `show` generation guard,
focus/status behavior and literal text rendering when adding a view.

Inspector data is privileged operator output. It does not flow into NPC context,
retrieval, cognition, perception or action resolution. Use the API's existing
loopback/access-control guidance when serving the application.
