# Task 15 — World Inspector implementation report

## Delivery and boundary

Uncommitted delivery on `task/15-world-inspector-ui`, based on `02d0802`.
Independent review and root task-tree acceptance are complete; milestone
integration gates follow.
No staging, commits, branch changes, merges or pushes were performed.

Added packaged `GET /inspector` and fixed CSS/JS assets; unknown assets are 404
and mutating methods are 405. Explicit setuptools package data and the optional
`browser-tests` Playwright extra are the only packaging changes. Installed-wheel
resource verification passed the root installed-wheel gate described below.

Ten views: Overview, Entities, Relationships, Resources, Needs, Goals, Work,
External connections, Stages and History. They retain reported definitions,
lifecycle/state, policy, criteria, history and evidence. Entity detail filters
exact references from existing GET snapshots. Evidence selects the referenced
History event. Resource stocks come only from explicit entity attributes, with
no missing-value zero, unit invention or reservation arithmetic.

Closed GET fetching, core-shape/JSON/numeric-range checks, literal text DOM
rendering, generation guards, live status/busy feedback, keyboard focus and
responsive scrollable tables are implemented. Task15c registry/detail extension
points and separate endpoint snapshot semantics are documented. No DTO, domain,
persistence, cognition or action-resolution path changed. The only existing
test-helper change adds typed response headers for dependency-free ASGI checks.

## Focused evidence

- TDD red: initial route/state tests failed four times on missing inspector 404;
  actual Chrome navigation failed on the missing Overview DOM. Nested missing
  need/work core shapes failed two browser assertions before validator fixes;
  an empty goal criterion failed one assertion before criterion-shape validation.
  Header verification failed before adding headers to the existing ASGI helper.
- Harness corrections: corrected the event subject field, immutable-state
  snapshot copying, event-loop bridging, required goal authorization and actual
  dispatch direction enum. These were setup defects, not accepted product red.
- `PYTHONPATH=src .venv/bin/pytest -q tests/test_world_inspector_ui.py
  tests/test_world_inspector_browser.py tests/test_inspection_api.py`: **47 passed**,
  no skips or warnings. Includes **31 real Chrome browser tests** using
  `/usr/bin/google-chrome`, isolated profile/context and actual `create_app`
  responses through the standard-library ASGI test client.
- Focused `ruff check` on server plus three relevant test files: passed.
- Focused `black --check` on the same four files: passed.
- `git diff --check`: passed.

Browser checks cover all navigation, populated domain views, literal HTML-shaped
text, entity/back and goal-event links, exact run/replay fields, filtered history,
loading/empty/404/non-JSON/malformed/unavailable states, unsupported integers,
network failure/Refresh recovery, obsolete response race, narrow viewport and
keyboard controls. Actual requests are GET-only. Before/after detached snapshots
of the entire engine state (including events) compare equal after UI interaction.
ASGI checks also prove read results are detached and known/unknown ID behavior.

## Review, remaining gates and limitations

Round 1 independent review identified four P2 findings; the worker corrected all
four within the existing boundary. Root scoped re-review passed:

1. Reservation tools/resources now share the typed string/safe-integer
   requirement validators used by work definitions. Browser cases reject absent
   keys, string quantities and fractional quantities, while valid requirements
   retain unrelated literal-text extras.
2. Criterion validation checks each selected known variant's full shape before
   population fallback; malformed `resource` or `minimum_condition` fields cannot
   pass a less specific shape. Browser regressions cover malformed known fields
   and valid population/resource/constructed/maintained variants with extras.
3. Exact entity-reference filtering includes `capability_id`. Real-engine Well
   detail now includes its maintenance policy and attribute-only capability event,
   excludes another Well's policy, and preserves complete engine state/events.
4. Nested field tables have a minimum usable width and unbroken heading labels.
   At 390px, actual text ranges prove population/resources/food/water/timber are
   single-line; each label can scroll into the viewport. The container scrolls
   horizontally and with keyboard ArrowRight without widening the page.

Correction TDD red command: the focused browser selection for reservation,
criterion fallback, capability references and nested layout produced **10 failed**
assertions before changes, including `population` wrapping into nine lines.
Fresh root-provided visual script run regenerated
`/tmp/living-world-inspector-wide.png` and `/tmp/living-world-inspector-narrow.png`;
the worker inspected the corrected narrow screenshot. Nested values remain
available by horizontal scrolling, with readable labels.

Root must run final
`make`, separate `make examples`, browser and actual installed-wheel resource
checks, then the required milestone integration gates. Worker did not run full
repository/example/build gates, as required by the binding task contract.

Each endpoint is an independent GET snapshot; views are not atomic multi-endpoint
snapshots. Module-level server owns an empty engine; `create_app(engine)` reads
that engine, and a separately loaded database remains a snapshot. No convenient
saved-world CLI, spatial renderer, administration or simulation control was
introduced; those remain separately owned scope.


## Root acceptance — 2026-10-14

Independent spec/quality PASS, NO SUBSTANTIVE FINDINGS after all four corrections.
Reviewer independently ran 16 correction-focused Chrome cases without warnings
or skips. Root inspected correction code and the actual wide/narrow screenshots.
The narrow labels are readable and nested values remain horizontally accessible;
browser geometry/keyboard tests protect this behavior. Root accepts Task15.

| Root command/gate | Result |
| --- | --- |
| `make` | PASS; Ruff/Black passed,1229 tests passed,10 existing deliberate skips,examples001–038 |
| Separate `make examples` | PASS; examples001–038 |
| Actual Chrome browser suite within make | PASS;31 cases, no browser skips |
| `git diff --check` and staged whitespace | PASS |
| `python -m build --wheel --no-isolation` on isolated current pyproject/src copy | PASS; no working-tree egg-info regeneration |
| Fresh venv install of wheel and installed resource/route smoke | PASS;3 assets byte-identical to source,3 routes,404/405/health checks,state unchanged |
| Real app visual check at1280px and390px | PASS after narrow-table correction |

The isolated wheel smoke used optional FastAPI TestClient/httpx and emitted
Starlette's deprecation warning recommending httpx2. This is a smoke-tool adapter
warning; repository API/browser tests use the dependency-free ASGI helper and
reported no warnings. No runtime dependency or product behavior was changed for
that warning. Wheel retains current0.5.0 metadata until owner-selected0.6.0rc1
Task24 closeout. No unexplained new skips.
