# 15c — Spatial Inspector view

## Status and scope

Execute only after reviewed Task15 integration on task/15c-spatial-inspector-view.
Extend the packaged operator inspector with Spatial, consuming existing detached
GET /world/placements and /world/entities. Python>=3.11, strict new annotations.
No domain/persistence/cognition changes, admin controls, road inference, new
routes, browser write requests or new build/runtime dependencies.

## Data and ordering

Each placement DTO has entity_id, geometry, containing_entity_id, bounds_kind,
overlap_policy. Geometry is null, {kind:"point",x,y} or
{kind:"bounds",x,y,width,height}. BoundsKind is "area"|"structure" and
OverlapPolicy is "reject"|"allow_sibling_overlap".
Use existing exact DTO shape/discriminants. Coordinates integer; dimensions
positive integers. Validate all core fields and known discriminants before
rendering; duplicate entity placements or unknown referenced entity is malformed.
Validate corresponding combinations: null has no container/bounds kind and
reject overlap; point has null bounds kind and reject overlap; bounds require
area/structure bounds kind. Display container and policy as directly reported,
without navigation/path claims.

Preserve backend canonical order for draw/list/labels. Use a dedicated Spatial
renderer; generic renderRecords applies ID sorting and must not reorder placements. If sorting is necessary,
implement identical placement_order_key: uncontained first, then container ID,
placed before null, x,y, rank(point0,area1,structure2),width,height,entity ID.
Do not substitute global entity-ID sorting or inferred layer order. Bounds may
use translucent styling so overlaps remain interpretable. A complete accessible
list and entity-detail links keep every record reachable despite visual overlap.

Null-geometry placements and entities with no placement form a deterministic
unplaced list: explicit null records retain backend placement order, then
entities with no placement record follow in entity-ID order. Visibly distinguish
"Unplaced" from "No placement record". Never synthesize origin markers or
containment geometry.
Destroyed entity lifecycle remains directly reported. Names fallback to ID only
where the existing entity view permits; never invent a name/type/placement.

## Deterministic projection

+x right/east and +y up/north. SVG point=(x,-y); bounds top=-(y+height).
Project coordinates individually so labels remain upright. Extent includes
point coordinates and both endpoints of bounds. For nonempty geometry:

- spanX=max(maxX-minX,1), spanY=max(maxY-minY,1);
- centerX=(minX+maxX)/2, centerY=(minY+maxY)/2;
- padding=max(spanX,spanY)/10;
- viewBox=(centerX-spanX/2-padding,-centerY-spanY/2-padding,
  spanX+2*padding,spanY+2*padding);
- preserveAspectRatio="xMidYMid meet".

One or co-located points use the explicit minimum spans. Empty/all-unplaced
world displays an empty map state plus any unplaced list, with no arbitrary map
coordinates. Resize changes physical scale only, never geometry/viewBox/order.
SVG marker and label sizes derive deterministically from the same extents, with
legible styling; document chosen formula in report and test actual layout.

Require Number.isSafeInteger coordinates/dimensions, endpoint sums, extent
differences and center numerator sums before projection. Unsupported numeric
range has a distinct fixed state; no rounded asserted world coordinates. Padding
and physical SVG scale are presentation, not claimed engine geometry. Coordinate
text remains literal reported integers. Non-integer/malformed input is a fixed
malformed response. No partial invented map on validation failure.

## Interaction and errors

Add Spatial through Task15 documented view registry/renderer seam; reuse its
closed route fetch, generation cancellation, loading/error handling and entity
entry function. Only add the placements closed route. Refresh obeys snapshot
semantics; no atomic cross-endpoint consistency claim.

SVG marks/list entries are keyboard accessible with clear names and entity
activation. Extend openEntityDetail(id, returnView="Entities") compatibly so
Spatial activation uses returnView="Spatial" and detail/404/Refresh preserve
that return target and aria-current reflects the originating view; Back to
Spatial reopens Spatial. Existing entity/history
entry points retain Back to Entities. No new routing library needed.
Use text nodes for labels and structured attribute details, no executable HTML.
Show reported containment, bounds kind and overlap policy alongside geometry.
Small screens use responsive SVG and usable list; do not hide records for layout.
Unavailable/404/non-JSON/malformed/empty states remain distinct. No editing,
placement generation, inferred roads or arbitrary URLs.

## Verification

Typed focused API/browser tests against real packaged inspector. Fixtures cover
area/settlement bounds, structures, positive/negative point coordinates, null and
missing placements, destroyed history and permitted overlapping records.
Independent literal expected viewBox/point/bounds projections protect arithmetic;
cover empty, single/co-located point, negative extrema, resize with unchanged
viewBox/order, unsafe integers/overflow, malformed DTO and unavailable responses.
Real Chrome/Playwright tests cover Spatial navigation, mouse and keyboard entity
activation, Back, literal HTML-shaped labels, loading/race/error states, narrow
viewport and all records reachable when marks overlap. Capture requests GET only
and compare complete engine state/events unchanged after interactions.

Root visually inspects screenshot/actual DOM on wide/narrow viewport. Optional
browser absence may skip explicitly for portability; current root acceptance
requires actual browser pass, with no unexplained new skips. Worker focused
checks/report only. Independent review then root make, separate examples,
whitespace, actual browser and installed-wheel asset gates; repeat required
merged gates before next task. Do not repeat full gates during worker/reviewer.

## Exact allowed files

- src/living_world/api/static/inspector.html,inspector.css,inspector.js
- tests/test_world_inspector_ui.py and tests/test_world_inspector_browser.py
- docs/world_inspector_ui.md and docs/http_inspection_api.md
- CHANGELOG.md, docs/project_journal.md, docs/backlog.md
- this plan, matching15c_spatial_inspector_view-prombt.md and required-report.md

No server/DTO/packaging change is expected: existing assets include new view and
existing API serves placements. Amend plan/prompt first for a concrete necessary
expansion. Report exact draw order/projection, unplaced/overlap semantics,
read-only/browser/visual/package evidence, review corrections and limitations.
