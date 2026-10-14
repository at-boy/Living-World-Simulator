# 15 — FastAPI-hosted read-only World Inspector

## Status and scope

Execute only after reviewed Task22 milestone integration, on
`task/15-world-inspector-ui`. Deliver same-origin packaged HTML/CSS/JavaScript
operator observability. No Node build project/framework/CDN, write route,
WebSocket, admin control, simulation stepping, map or NPC/cognition integration.
Python>=3.11 and strict annotations remain required. Root owns review/gates/VCS.

## Routes and files

GET `/inspector` serves `src/living_world/api/static/inspector.html`.
Fixed assets `/inspector/assets/inspector.css` and `inspector.js` use packaged
resources. Unknown assets404, mutating methods405. Keep existing GET API routes
and domain DTOs unchanged. Use explicit package-data in pyproject.toml for these
assets; optional `browser-tests=["playwright"]` is development verification,
not a runtime/browser-consumer or Node build dependency.

## UI contract

Responsive neutral operator dashboard with semantic navigation, reported tick,
read-only/snapshot note, one Refresh button and one labelled content region.
Views are Overview, Entities, Relationships, Resources, Needs, Goals, Work,
External connections, Stages and History. Implement accessible keyboard
navigation, focus management, aria-current, aria-busy/status messaging and
usable narrow-screen tables. Do not add inactive placeholder features.

A closed fetch helper hardcodes same-origin GET and no body, accepts only known
route keys plus encoded entity ID. Dynamic content uses textContent/text nodes;
no innerHTML/eval interpolation or user-controlled URL. Cancel/ignore obsolete
requests using a generation token so old responses cannot replace a new view.
All views use deterministic ID/key order; History uses (tick,id).

| View | Sources and displayed truth |
| --- | --- |
| Overview | /world counts and reported tick; /world/run scenario/seed/binding (404 means unbound); /world/replay exact binding/cursor details, no inferred run success |
| Entities | /world/entities names, definitions and lifecycle; detail from /world/entities/{encoded ID}, attributes and matching references;404 detail has Back navigation |
| Relationships | /world/relationships kind,source,target,lifecycle; names from known entities with ID fallback, no inferred indirect links |
| Resources | /world/resources definitions PLUS explicit entity.attributes.resources from /world/entities for reported quantities; no missing-value zeros, invented units or reservation subtraction |
| Needs | /world/needs definition/state, nullable current assessment and history; /world/consequences consumption/storage/maintenance policy/state records |
| Goals | /world/goals definition/state and nested objective definition/state, statuses, dependencies,criteria and evidence/source-event links; never recalculate completion |
| Work | /world/work-orders definition/state/reservations, labels,status,progress,assignments,deadlines,prerequisites,reported reasons; no action buttons |
| External connections | /world/external-references and /world/external-dispatches exact policies/lifecycles, no imagined off-map entities or future results |
| Stages | /world/settlement-stages managed current stage, program requirements and transition fields, no client promotion logic |
| History | /world/events filterable fetched history and exact kind/subject/tick/attributes; evidence links select the referenced event |

Entity-detail matching references use client-side filtering of existing GET
snapshots; no aggregate DTO or new inspection method is authorized. Show only
exact references present in those snapshots.

Each view validates JSON envelope and required core record shapes before
rendering. Malformed/non-JSON, empty, missing404 and unavailable/server-error
states are distinct fixed prose. Unknown extra JSON-safe fields may be displayed
as details without deriving semantics. No provider payload/error content becomes
executable markup. Quantities/geometry outside supported browser numeric range
must not silently round into asserted exact facts; display unsupported/malformed
state rather than invented values.

The header says Reported tick. Views are separate GET snapshots, not an atomic
cross-endpoint world snapshot. Refresh never advances the simulation. Explain
in operator docs that module-level server owns an empty world; create_app(engine)
reads that same supplied engine, while a separately loaded database is a snapshot.
Task23 owns the convenient saved-world inspection CLI composition.

Keep view dispatch, fetch/validation and DOM-render helpers separated within the
small static JS module. Document the view registry/entity-detail entry function
for Task15c to add Spatial without rewriting the inspector.

## Required verification

- Typed Python tests on actual create_app: route/assets/content types,404/405,
  detached snapshots, state/events unchanged after reads and known/unknown IDs.
- Python Playwright browser tests using installed Chrome/Chromium (or explicit
  executable environment override) with isolated temporary profile; current host
  /usr/bin/google-chrome passed a root probe. Test navigation across all views,
  entity drill-down/back, evidence/history links, loading/empty/404/malformed/
  non-JSON/unavailable states, stale response race, narrow viewport, keyboard
  controls and literal HTML-shaped entity text. Capture requests and assert GET
  only; compare engine state/events before/after UI interaction. Tests exercise
  real DOM/client behavior, not only source-string inspection.
- Optional tooling/browser absence may skip with explicit reason for core
  portability, but root cannot approve Task15 without actually running browser
  tests on a supported browser. No new unexplained skips in current delivery.
- Wheel/package gate: root builds from isolated copy of current pyproject/src and
  inspects installed resource contents, not a grep-only metadata assertion. Avoid
  regenerated tracked egg-info in the working tree.
- Boundary: inspector imports remain in API/static/operator code; no payload
  path to retrieval, NPCContext, cognition or action resolution is introduced.

Use TDD and focused API/browser checks. Worker reports focused counts and
meaningful failures/warnings; root runs make, separate make examples, whitespace,
actual browser and wheel resource checks after independent review/corrections,
then required merged milestone gates. No repeated worker full gates.

## Allowed files

- src/living_world/api/server.py
- src/living_world/api/static/{inspector.html,inspector.css,inspector.js}
- pyproject.toml: package-data and optional browser-tests extra only
- tests/test_world_inspector_ui.py, tests/test_world_inspector_browser.py
- focused tests/test_inspection_api.py changes if required
- docs/world_inspector_ui.md, docs/http_inspection_api.md
- CHANGELOG.md, docs/project_journal.md, docs/backlog.md
- this task plan, saved15_world_inspector_ui-prombt.md and required
  15_world_inspector_ui-report.md

No domain, persistence, cognition, spatial manager or inspection DTO changes.
Amend plan/prompt first if a concrete prerequisite defect requires expansion.
The report includes routes/assets/views, browser and packaging evidence,
read-only/state-preservation evidence, review corrections and limitations.
