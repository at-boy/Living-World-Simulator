# Task15c — Spatial Inspector implementation report

## Status and boundary

Independent spec/quality review and root task-tree acceptance are complete;
milestone integration follows.
Work is uncommitted on `task/15c-spatial-inspector-view` from `e6e9870`, in the
assigned `.worktrees/task15c` checkout. Only allowed assets, focused existing
UI/browser tests, operator docs, changelog, journal, backlog and this report
changed. No server/DTO/domain/persistence/cognition/build/dependency changes,
staging, commits, branch changes, merges, pushes or delegated agents.

## Delivered behavior

`Spatial` uses the existing view registry and generation-guarded GET fetches for
placements, entities and summary. Endpoints remain independent snapshots. Core
placement fields/discriminants/combinations are validated before rendering;
duplicate placements and unknown subject/container references are malformed.
A distinct fixed numeric-range state rejects unsafe integer coordinates,
dimensions, endpoint sums, extent differences and center numerator sums before
projection. Noninteger/type/shape errors remain malformed. Errors clear all
records and map, with no partial coordinate claims.

The dedicated renderer preserves backend placement order, without generic
`renderRecords` ID sorting. Marks, labels and placed-record details use that
order. Explicit null placements retain backend order in the unplaced section;
entities without any placement follow by entity ID. They visibly say `Unplaced`
and `No placement record`, respectively; neither gets an invented marker.
Structured details show reported geometry, container, bounds kind, overlap
policy and creation/destruction ticks. Destroyed records remain inspectable.

Projection is point `(x,-y)`, bounds `(x,-(y+height))`. Extents include bounds
endpoints and point coordinates. Spans have a one-unit minimum, center is the
endpoint average, and padding is one tenth the larger span. The viewBox is
`(centerX-spanX/2-padding, -centerY-spanY/2-padding,
spanX+2*padding, spanY+2*padding)` with `xMidYMid meet`. No group flip is used;
labels stay upright. Marker radius is the larger span /100; label font size is
that span /20, with one-percent-span position offsets and a white text stroke.
These are presentation sizes, not engine geometry. Chrome verifies literal
viewBoxes `-12 -12 24 19`, `-23 -13 36 26`, and minimum-span single/co-located
point values. Resize preserves viewBox; actual narrow-screen label height must
be at least12px. Root visual acceptance remains pending.

Area/structure bounds are translucent. Every mark is named and keyboard
activatable with Enter/Space; every entity has a native list button, preserving
access when marks overlap. Labels use literal text nodes. Compatible
`openEntityDetail(id, returnView="Entities")` preserves Spatial origin through
Refresh, entity404, aria-current and Back to Spatial. Existing entry points
retain Back to Entities. No browser write requests or simulation changes occur.

## Test-first and correction evidence

- Preserved initial RED run:
  `PYTHONPATH=src .venv/bin/pytest tests/test_world_inspector_browser.py -k spatial -x -q`:
  1 failed /31 deselected, missing Spatial button. An initial edit attempt failed
  because `python` is absent and made no asset changes; subsequent old RED run
  was interrupted (exit130, no final summary). Resume used `.venv/bin/python`.
- Initial Spatial GREEN: same focused browser file with `-k spatial -q`,
  9passed /31deselected, actual installed Chrome, no skips.
- Narrow-label RED: `-k spatial_overlap -q`, 1failed /47deselected,
  measured9px label height. Increased font formula from larger-span/40 to /20.
- Expanded17-case run initially had 16passed /1failed /31deselected: test clicked
  the entire SVG group's bounding rectangle, including empty/clipped label
  space, rather than its visible mark. Corrected the real mouse test to click
  the point circle. No forced clicks or synthetic activation bypasses.
- Final Spatial-focused run: `-k spatial -q`, 39passed /31deselected.
- Initial focused Ruff found one unsorted local import; fixed and rechecked.

## Initial worker focused verification (before review)

Commands run with `PYTHONPATH=src` where needed:

- `.venv/bin/pytest tests/test_world_inspector_ui.py tests/test_world_inspector_browser.py -q`:
  **74passed**, including **70actual Chrome browser cases**, no skips/warnings.
- `.venv/bin/ruff check tests/test_world_inspector_browser.py tests/test_world_inspector_ui.py`:
  passed after the one import correction.
- `.venv/bin/black --check tests/test_world_inspector_browser.py tests/test_world_inspector_ui.py`:
  passed,2files unchanged.
- `git diff --check`: passed.

Browser fixtures exercise actual packaged assets and real FastAPI engine
responses, with route substitutions only for malformed/unavailable/race cases.
Coverage includes area/structure/permitted overlap, positive/negative points,
null/missing/empty/co-located states, backend order differing from entity-ID
order, destroyed lifecycle, literal HTML-shaped names, actual narrow layout,
mouse/Enter/Space activation, detail404/Refresh/Back, network/HTTP/nonJSON
failures, stale response cancellation and arithmetic/type/discriminant failures.
GET-only capture and full engine state/event snapshots verify interactions are
read-only. UI API read-only coverage now includes `/world/placements`.

## Remaining root-owned acceptance

Round1 independent review identified the extra-field validation regression
documented below; its correction is awaiting scoped re-review. Root owns
full `make`, separate examples, final actual-browser acceptance, wide/narrow
visual inspection, installed-wheel assets, integration and merged gates. These
were deliberately not run by this worker; no full-suite or package/visual
approval is claimed. Map labels may overlap or clip near borders for long names;
the complete literal accessible list remains the authoritative route to every
record. No placement editing, inferred road/path, or atomic snapshot guarantee.


## Round1 accepted P2 correction

Independent review found placements bypassed recursive `safe(value)` while the
record renderer displays unknown nested extra fields. Actual Chrome regression
cases preserved raw JSON numeric tokens to reproduce unsafeinteger
`9007199254740993` and nonfinite exponent `1e500` extras. The RED command
`PYTHONPATH=src .venv/bin/pytest tests/test_world_inspector_browser.py -k spatial_nested_extra -q`
reported **2failed,1passed,70deselected**: both unsafe extras incorrectly loaded;
safe literal extras already passed.

The closed fetch path now validates placement shapes first, preserving distinct
core `spatialRange` errors, then recursively checks the complete placement
payload with `safe(value)`. Unsafe nested extras are malformed and clear both
map and record details; safe nested HTML-shaped text remains literal. This
changes no route, domain state or task boundary. Operator documentation explains
the retained unknown-extra guarantee. No visual behavior changes were requested
by root's initial screenshot inspection; root owns final visual acceptance.

Round1 correction verification:

- `PYTHONPATH=src .venv/bin/pytest tests/test_world_inspector_browser.py -k spatial -q`:
  **42passed,31deselected**, actual Chrome, no skips/warnings; includes all core
  spatial-range cases and the three nested-extra regressions.
- Focused Ruff and Black checks for the two existing inspector test files:
  passed,2files would remain unchanged.
- `git diff --check`: passed after correction and report update.

No full-gate rerun, staging or VCS action. Correction is stable for scoped
independent re-review and root-owned acceptance.


## Root acceptance — 2026-10-15

Independent spec and quality PASS, NO SUBSTANTIVE FINDINGS after the recursive
payload numeric-safety correction. Reviewer independently passed11 correction
Chrome checks. Root inspected actual app wide/narrow screenshots with overlapping
bounds, points and unplaced records; complete state/events were unchanged. Labels
can overlap as documented; the literal accessible list retains every record.

| Root gate | Result |
| --- | --- |
| `make` | PASS; Ruff/Black,1271tests passed,10existing deliberate skips;examples001–038 |
| Separate `make examples` | PASS;001–038 |
| Actual Chrome cases within full suite |73passed,no skips |
| Unstaged/staged whitespace checks | PASS |
| Isolated pyproject/src wheel build and fresh install | PASS |
| Installed resources/routes smoke |3 byte-identical assets,3routes,404/405,placements and complete state preservation PASS |
| Actual wide/narrow visual inspection | PASS with documented overlap/list fallback |

No new warnings or unexplained skips. Installed smoke used dependency-free ASGI
transport, avoiding the previous optional TestClient adapter warning. Wheel
remains0.5.0 until owner-selected0.6.0rc1 release closeout. Main not in scope.

## Milestone integration

Delivery9d9dbf0 merged0a81a11. Root merged make1271passed/10existing skips,73Chrome
cases,examples001–038; separate examples and whitespace passed. Documentation-only
conflicts retained task and pause history; source/tests/package match reviewed
delivery exactly. Installed assets/routes match merged tree. Main unchanged.
