# LN08c — Authenticated pinned inspector integration

Status: independently reviewed and root task-validated; feature integration follows.
Base25fb5a7; exact contractdeefc57; approved LN08 bounded inspector stage.
**Goal:** embed the existing inspector against authenticated immutable checkpoints,
preserving standalone behavior and navigation across live revision updates.
**Architecture:** operator app serves validated protected inspector HTML and public
allowlisted existing assets. Trusted same-origin parent supplies a memory-only Bearer
token through a strict postMessage protocol; every refresh captures one fixed prefix.
**Tech Stack:** existing Python/FastAPI, vanilla JS/HTML, Playwright/actual Chrome.
**Spec:** docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md operator section;
original approved LN08 in live runtime master plan. No new product design scope.

## Constraints and exact worker boundary

Python>=3.11; no dependencies, schema, domain, provider, runtime-owner or CLI changes.
Preserve managers/systems/events and all NPC boundaries. Privileged DTOs are never
NPC contexts; LLM text remains untrusted. No real model calls, installs or downloads.
Existing standalone create_app, /inspector and default /world routes remain compatible.
Exactly six worker paths:
- src/living_world/api/operator.py
- src/living_world/api/static/inspector.html
- src/living_world/api/static/inspector.js
- tests/test_runtime_inspector_browser.py (new; API + actual loopback/Chrome cases)
- docs/world_inspector_ui.md
- docs/subagent_execution_plan/live_npc_runtime/08c_authenticated_inspector-report.md
Root owns task/prompt/common docs. No CSS/package/runtime page/control UI/serve changes.
No source expansion without root task+prompt amendment before code. Worker no VCS,
subagents, fullmake/examples, other-checkout writes. Unit temporary archives allowed;
every normal manual simulation retains its archive.

## Protected HTML and packaged assets

Add GET /live/checkpoints/{revision}/inspector and
GET /archives/{attempt_id}/checkpoints/{revision}/inspector to create_operator_app.
Use existing read authorization dependency BEFORE any archive access. Reuse the
app's existing resolve(Request) to validate and open that exact source off eventloop;
no second RevisionSource/cache/runner. Existing safe404/409 behavior, strict UUID and
nonnegative decimal revision applies. Render existing packaged inspector.html with
only validated canonical server-generated prefix and source-kind bootstrap attributes.
Canonicalize parsed revision via int ->str; source-kind live/historical. Never insert
scenario/model/NPC prose, credentials, raw path/query/exception in HTML. Source data
attributes: data-inspection-prefix and data-inspection-kind on html, absent in default
standalone template. Use an exact static template insertion point; fail safely if
missing. GET with arbitrary query parameters never configures prefix or credentials.

Add public GET /inspector/assets/{asset_name} allowlisting ONLY inspector.js and
inspector.css, existing package resources/media types, unknown404. No world, secrets
or new assets. Synchronous handlers dispatch reads offloop. Existing app middleware
no-store covers HTML/assets/errors. No unauthenticated inspector HTML/world route.
Normal browser cannot add Bearer to iframe navigation; future runtime parent must
authenticated-fetch HTML then assign iframe.srcdoc. Tests use a small trusted test
parent served by a test-only wrapper, never add a product placeholder runtime page.

## Strict parent/child protocol

Standalone template has no bootstrap attributes: preserve original immediate default
fetches, no token/messages/config from URL, normal focus/nav/errors. Reject partial
or malformed bootstrap fail closed (no data requests). Embedded requires BOTH valid
attributes, window.parent!==window, same-origin http(s) inherited effective window.origin (not location.origin).
Validate closed prefix grammar: live /live/checkpoints/<canonical nonnegative safe
integer>; historical /archives/<canonical UUID4 hex>/checkpoints/<canonical revision>.
UUID4 is existing archives.model.identifier format: exactly32 lowercase hex digits,
version nibble4 and RFC variant nibble8/9/a/b, no hyphens (parsed.hex must equal input).
No URL, percent escape, query, fragment, protocol-relative or trailing slash forms.
Historical pins remain fixed forever; live updates accept live prefixes only.

Embedded JS stores credentials/config in its closure only. Before connection no
world fetches, show Waiting for operator connection, navigation cannot trigger GET.
Child sends {type:'living-world-inspector-ready'} once on script initialization to
window.parent with exact window.origin targetOrigin (never '*').
Only accept event.source===window.parent AND event.origin===window.origin,
non-array plain message object with EXACT keys/schema for:
- {type:'living-world-inspector-connect',token:str}: once only, token matches locally
  issued token_urlsafe(32) 43-character [A-Za-z0-9_-] grammar. Start initial refresh.
- {type:'living-world-inspector-pin',prefix:str}: only connected/live mode; validated
  live prefix, changed only. Same prefix does nothing. Retain current selection.
- {type:'living-world-inspector-clear'}: terminate connection, abort/invalidate work,
  clear token/config/data/names/history filter/DOM, stop all data fetches; subsequent
  connect/pin ignored for this frame lifetime. Future parent destroys frame on logout.
Ignore unknown types, extra keys, wrong value types, foreign origin/source. No token
reflection in messages, attributes, errors, logs, local/sessionStorage/cookies/URLs.
No exported mutable globals/callbacks or arbitrary external fetch targets.
Future parent must validate exact origin AND source===expected iframe.contentWindow
before ready; send messages only to that frame with exact origin. Parent/page itself
is LN08d; no product parent implementation in this stage.

## Coherent refresh, navigation and focus

Reuse existing routes/validators/views/renderers. Each show captures immutable prefix,
auth header copy and AbortController signal ONCE for all Promise.all requests.
fetchSnapshot joins fixed existing /world suffixes to that prefix; methodGET,
credentials same-origin, redirect error, cache no-store. Prefix header never read
from mutable config midfanout. Abort previous requests on new navigation/pin/clear;
retain generation guard after every await and before DOM/status/busy mutations.
Stale abort/error/results cannot replace newer UI or clear its busy state. Current
network/auth/source error remains fixed safe prose and Refresh can recover. No cache.

Pin update reuses current view, entityId, eventId, returnView; preserve History filter
string through embedded background refresh, and never steal focus to title. Capture
semantic focus key before refresh and restore only if it still exists and focus has
not moved elsewhere by user choice while fetching. Stable keys for nav/refresh, history
filter, entity buttons, event links, spatial marks and return buttons; compare dataset
strings rather than untrusted CSS-selector interpolation. Preserve history input
selection/caret where applicable. Existing user navigation/title focus and standalone
filter behavior remain compatible. A disappearing entity keeps existing safe notfound
and Back target; a disappearing focus target leaves safe focus without forcing title.

Default standalone warning about independent snapshots stays. Embedded source label
shows Live checkpoint or Historical checkpoint and revision via textContent; spatial
help also describes pinned mode truthfully. No model/player text enters innerHTML,
HTML bootstrap, style or unsafe selectors. Existing textContent/SVG literal behavior
is retained. Child is GET-only, has no live controls and never submits commands.

## Review focus and TDD checks

- [x] RED protected HTML/source bootstrap/asset behavior via ASGIClient, then GREEN:
  auth before source access; malformed/missing/corrupt revisions404/409; safe HTML
  attributes only, query ignored, no credentials in HTML/assets/JSON, no-store.
- [x] Actual uvicorn plus Chrome trusted-parent harness exercises real authenticated
  HTML fetch/srcdoc handshake and real pinned DTO routes (no route.fulfill replacement
  for acceptance). Missing connection causes zero worldGET; only exact parent/origin
  and closed messages accepted; malformed pins never fetch; credentials absent from
  URL/DOM/localStorage/sessionStorage; every dataGET has Bearer. Test foreign sameorigin
  sibling source and foreignorigin messages (synthetic delivery acceptable negative
  probe), invalid bootstrap, repeatedconnect, clear while requests pending.
- [x] Capture actual data URLs for multi-panel view and pin updates; all requests in
  each refresh share one revision. Delayed old-pin response can't change current DOM/
  status/busy; newest data wins. Safe explicit controlled response delay may wrap an
  actual route response; no fabricated DTO acceptance.
- [x] Background pin updates retain active entity/event/return target, History filter
  and keyboard focus/caret; navigation during pending refresh wins. Literal malicious
  scenario/entity/event prose renders without executable nodes. Narrowviewport and
  keyboard access remain functional.
- [x] Historical frame ignores pin updates and is GET-only; bytes/mtime/typedentries
  unchanged before/after browsing and failures; no runner/provider/step calls.
- [x] Existing standalone inspection API/UI/browser tests pass unchanged, including
  original focus/stale/spatial/missingentity behavior. Do not weaken old assertions.
- [x] Focused command: PYTHONPATH=src TASK_PY -m pytest
  tests/test_runtime_inspector_browser.py tests/test_runtime_operator_api.py
  tests/test_inspection_api.py tests/test_world_inspector_ui.py
  tests/test_world_inspector_browser.py -q. Use smallest namedcase during RED/fixes.
  TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python
- [x] Scoped Ruff/Black for2Python paths, whitespace/self-review/truthful ownreport.
  Record command/result/count/warnings, no successful-output dumps. Root independent
  SPEC/QUALITY review then full task/merged make/separateexamples/whitespace/retained
  canonical/newCLI acceptance before implementation commit and integration.

## Root pre-dispatch self-review

This is original approved8 coherent inspector integration, split before parent controls
and CLIserve. Protected HTML shares authenticated source resolver; JS accepts only
trusted parent and fixed source prefixes; one-refresh snapshot pairs prefix/header/
generation. Same assets/default emptybase preserve old app. Historical readonly fixed
source and strict clear guard preserve archive truth and credential lifecycle. Tests
cover each protocol/focus/race producer-consumer pair. No NPC-facing or owner mutation
path changes. Parent token-entry/control/outcome/archive-list UI remains8d; CLIserve
and installed wheel11assets remain subsequent stages, actual Ollama acceptance LN09.

Root actualChrome protocol probe: srcdoc location.origin is literal null while
window.origin is inherited http://127.0.0.1:8000; use effective window.origin for
strict message origin/target checks. Tested installed Chrome before contract final.
