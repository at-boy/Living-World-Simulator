# LN08d — Local runtime control and archive page

Status: complete, independently reviewed and task/merged validated; deliveryfdfeecf
is integrated by the merge containing this task. Base0b81d97; contractef0209d.
**Goal:** let a local administrator authenticate, observe/control the current world
and browse saved checkpoints without losing command or inspection consistency.
**Architecture:** public packaged login page keeps session credentials only in JS
memory, consumes reviewed operator APIs and embeds the reviewed pinned inspector.
RuntimeService remains sole mutation owner. CLI serving/token delivery follows8e.
**Tech Stack:** existing FastAPI, vanilla HTML/CSS/JS, actual uvicorn/Chrome.
**Spec:** approved live runtime design operator section and original LN08.

## Scope and constraints

Python>=3.11, no dependencies/schema/domain/owner/provider/CLI changes. No new world
start/fork/resume HTTP API. Existing standalone inspector and NPC trust boundaries
unchanged. Exactly nine worker paths:
- src/living_world/api/operator.py (static page/assets routes only)
- src/living_world/api/static/runtime.html (new)
- src/living_world/api/static/runtime.css (new)
- src/living_world/api/static/runtime.js (new)
- pyproject.toml (three runtime package-data entries only)
- tests/test_runtime_browser.py (new, API/packaging/browser)
- docs/http_inspection_api.md
- docs/world_inspector_ui.md
- docs/subagent_execution_plan/live_npc_runtime/08d_runtime_page-report.md
Root owns task/prompt/common docs. No inspector/auth/API semantics changes. Important
producer gap ->root task/prompt amendment before code. No VCS/index/subagents/fullmake/
examples/installs/downloads/realmodel/othercheckout writes by worker. Unittemp archives
allowed; normal manual simulations always archived persistently.

## Public packaged page

GET/runtime returns packaged runtime.html. GET/runtime/assets/{asset_name} allowlists
ONLY runtime.js and runtime.css/media types, unknown404; synchronous resource reads
off eventloop. Existing no-store middleware covers page/assets/errors. No publicworld
route, inline credentials/bootstrap or CORS. Packaging retains all original8resources
and adds exactly static/runtime.html/css/js to living_world.api package-data. No
export/version/dependency change. No module-level service creation or start on GET.

Page has meaningful labels, login password field, Connect/Disconnect, live metadata
and controls, archive refresh/list, details/config/outcome/journal, checkpoint chooser
and an iframe titled World Inspector. Minimal readable style consistent with existing
inspector, keyboard operation, loading/error live regions, wrapping controls/table
overflow at390px. Focus only for explicit navigation/login outcomes, never polling.
No implementation jargon in ordinary UI; label operational version/revision as needed
to explain last committed world. No data visible before login. No UI-derived goals/
success/resource arithmetic; server remains authoritative.

## Session, polling and safe data

Login token exact43[A-Za-z0-9_-] characters, input cleared immediately on submit.
Token, nonce, requests/pending envelopes remain closure memory only, never global/
dataset/DOM/log/URL/cookie/localStorage/sessionStorage. Password autocomplete off and
spellcheck false. GET/runtime/status with Bearer, accept X-CSRF-Token only if same
43charactergrammar; expose no nonce in JSON or UI. Invalid login/nonce fixed safe
message, clear credentials/data. Any authenticated request401/403 disconnects.
Disconnect, pagehide and reconnect invalidate a monotonically increasing session
generation, abort in-flight requests, cancel polling, clear all data/credentials/
pending envelopes and clear/remove child. Server already-admitted commands may still
complete; do not claim disconnect stops simulation. No GET/close issues Stop.

Serial status polling every1000ms AFTER previous poll finishes (no overlap), only
while connected; capture generation before await and recheck before DOM/state work.
Network/malformed failure labels last data stale, disables mutation until successful
status, keeps previous last-complete data visibly stale. Poll retry is GET only.
No arbitrary wallclock freshness calculation or optimistic state advancement.

Validate DTOs against reviewed8b shapes. Operational state must be known exact
RuntimeState string; state_version/revision/tick safe nonnegative integers with
revision/tick null together. UUID IDs canonical32lowercase UUID4hex. Prefix exactly
/live/checkpoints/<canonical safe revision> and matches reported revision. Metadata
strings/null, model object name/digest strings/null; recursive JSON finite/safe
numbers for display. Reject malformed data with fixed safe prose; never display raw
exception/header/token response text. All scenario/model/NPC/journal/config strings
render with textContent, never HTML, style, dynamic selector or JS.

Live panel reports attempt/lineage, mode/scenario/modelname/digest, state/stateversion,
last committed tick/revision, activity/error/configuration_error and last refresh.
Status is operational, world view is last durable complete revision. liveNone means
no live attempt yet/archive inspection available; no fabricated initialization/world.
Unknown/malformed status disables controls. A healthy poll does not force focus.

## Inspector composition and fixed history

Use8c existing protected <prefix>/inspector routes. Parent validates source prefix,
Bearer-fetches server HTML, captures selection/session epoch, then assigns ONLY that
trusted server template to iframe.srcdoc. No arbitrary URL/query-selected base/HTML.
Register listener before assigning srcdoc. Accept exact plain-object
{type:'living-world-inspector-ready'} only with event.origin===window.origin and
event.source===currentExpectedFrame.contentWindow; send documented connect token
to that frame and exact origin. Ignore foreign/old frames/messages/extra keys.
Subsequent live revision update sends documented pin message, preserving child state;
same prefix no reload. Attempt change creates fresh frame. Initial revisionNone or
liveNone shows no committed checkpoint. Clear protocol before removal on logout or
source switch; late fetch/ready cannot connect or replace a newer selection.

GET/archives on login and manual Refresh archives. Render all discovered summaries,
including failed/setup/corrupt. Each archive row MUST include attempt, mode/scenario,
start time, parent attempt/checkpoint (or none), lifecycle/status, actual outcome and
last committed tick (or no checkpoint), matching the approved design list requirement.
These summary fields must be visible in the list without selecting details. Retain
responsive horizontal overflow and text-only values. Rows include actual outcome: summary has no outcome,
so fetch existing detail GETs with at most2 concurrent requests and cache plain DTOs
for this archive-refresh generation. Reuse loaded details on selection; invalidate
on explicit archive refresh/session change. Show Loading/Unavailable/No outcome
recorded distinctly; no guessed success from lifecycle. Preserve catalog order and
label archive refresh time. Corrupt detail failures retain their rows. Do not expand
API/catalog/store merely to optimize this first browser slice. Selecting archive IMMEDIATELY hides live controls,
then GETdetails and checkpoints; selection epoch prevents late results overwriting
new source. Show mode/scenario/start/end/parent/lifecycle/last tick and actual outcome
separately; details latest50typedjournal plus explicittotal, configuration/source label.
No invented success or checkpoint. Valid no-world details remain readable with no
preview; corrupt selection fixed safeerror while row remains listed. User chooses
one complete checkpoint, authenticated HTML opens fixed historical inspector. Show
source/historical/read-only/attempt/time/parent/mode/checkpoint labels via textContent.
Status polling may continue but never retargets historical frame; no active controls
there. Explicit Return to live creates current live frame and restores live controls.
History is GET-only: no runner, provider, lease, step or resume/fork construction.

## Durable commands and uncertainty

Allowed buttons exactly controller._allowed: initializing pause/stop; paused resume/
step/stop; running or awaiting_model pause/stop; stepping pause; provider_error_paused
retry/stop; pause_requested and completed/stopped/failed/interrupted none. Display
Pause requested until server status/receipt confirms pause. Retry model is explicit,
never automatic. Historical selection and stale/unsupported status disable commands.

On explicit click create ONE crypto.randomUUID command_id and exact envelope
{command_id,action,expected_state_version:lastFreshStatus.state_version}. POST only
/runtime/commands, JSON, Bearer and X-CSRF-Token; browser supplies same-origin Origin.
Never use checkpoint revision as expected state_version. Outstanding envelope per
action suppresses duplicate clicks/new IDs until resolved. Allow Pause during pending
Step when fresh state allows, do not globally lock all controls for pending inference.
At most one in-flight delivery per envelope. No automatic POST retry/new intent.

Receipt exact fields command_id/status/state_version/revision/reason; ID matches
submitted envelope; status queued/applied/rejected, safeinteger versions/revision,
reason string/null.202queued is admission only. GET/runtime/commands/{id} each poll
until durable applied/rejected; show receipt status/revision/reason without inventing
paused/tick advancement. Known duplicate preserves original effect. Stale/lifecycle
rejection displays reason and refreshes status, never silently changes envelope.
Network/5xx/malformed response is uncertain delivery: retain original envelope,
readonly receipt polling may discover outcome, explicit Retry delivery resends EXACT
same ID/action/version. GET404 means unknown, not proof no effect; no new ID.
Retry delivery is distinctly labeled from Retry model action.
Fixed admission409detail command_conflict/runtime_unavailable/archive_invalid or
422invalid_command displays local admission failure separately, no synthetic receipt.
Terminal server receipt releases action gate; only subsequent explicit intent uses
new ID. Disconnect drops local pending display but durable server audit survives.

## TDD, tests and root gates

- [x] RED absent page/assets/packageentries before source; GREEN exact page routes
  no-store/allowlist and secret-free HTML. Test pyproject resources + original8retained.
- [x] Actual uvicorn/Chrome login/logout and archive-only/live sessions; token/nonce
  absent URLs/storage/rendereddata/archives; wrongtoken and401/403 cleanup, malformed
  data stalecontrols, delayed logout/reconnect/source-selection responses ignored.
- [x] Actual real-service pause/resume/single-step (doubleclickone tick), pendingpause
  vs durableACK, state/version rejection, Stop/terminal and explicit fakeproviderRetry;
  status/control remains responsive during delayedfakeprovider. No real model here.
- [x] LostPOST before/after actual admission; explicit Retrydelivery sameenvelope/ID
  recovers atmostone effect, stable receipts; GETunknown nevernewID; no autoPOSTRetry.
  Controlled response loss/delay may wrap actual routes, no fabricated success DTO.
- [x] Parent handshake exactorigin/source andoldframe denial; all child data GETs use
  one pinned revision withBearer; live updates retain current child view/focus/filter,
  history fixed across live advancement, no controls/no mutations/sourcebytes unchanged.
- [x] Archives all-outcomes/setup-only/corrupt details, latest50journal+total, no-world
  no fakecheckpoint; malicious prose literal, keyboard and390px usable.
- [x] Existing API/inspector tests remain unchanged and pass. Focused: PYTHONPATH=src
  TASK_PY -m pytest tests/test_runtime_browser.py tests/test_runtime_inspector_browser.py
  tests/test_runtime_operator_api.py tests/test_world_inspector_ui.py
  tests/test_world_inspector_browser.py -q. Smallest namedcase while RED/corrections.
  TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python
- [ ] Scoped Ruff/Black twoPythonpaths, whitespace/self-review/report exactcounts/
  warnings. Root independentSPEC/QUALITY thenfulltask/mergedmake,separateexamples,
  whitespace/retainedcanonical/newCLI/wheel11resource checks before sourcecommit.

## Root self-review

Staticpage/resources pair withpackaging; sessiongenerations bindallrequests/frames;
DTOvalidation tiescommands tooperationalversion; receiptpoll/sameenvelope retry prevents
doubleeffects; inspector protocol reusedunchanged; historicalselectiongatescontrols
andpins; tests eachsecurity/race/persistence boundary. No new NPC/world authority path.
OriginalLN08 parentUI only; CLIserve/tokenfile/launcher in8e, realOllama LN09 later.

## Root correction amendment — DTO types and shared archive-detail bound

Independent review confirmed three P2 gaps. Same nine worker paths, no API/owner or
architecture scope expansion. State predicate MUST require primitive string before
known-state membership; arrays/objects never become fresh or enable commands. Receipt
revision MUST be nonnegative safe integer (not null), matching CommandReceipt. Any
malformed terminal receipt leaves the original envelope uncertain/pending, no gate
release/new command ID until a valid durable receipt or identical explicit delivery.

Use ONE shared archive-detail scheduler for the page, maximum2 outstanding detailGETs
across background outcomes, row selection, refresh and reconnect. Each current
(session generation, archive-refresh generation, attemptID) has one shared in-flight
promise/cache; row selection joins that promise or enqueues through the same bound,
never bypasses it. FIFO queued work is sufficient; displayed catalog order unchanged.
On explicit archive refresh discard/cancel not-yet-started obsolete queued jobs and
ignore obsolete results. Already-started detail reads may finish, still occupying
the shared two slots until settled; new generation jobs wait for capacity. Logout
aborts actual requests as before; slot accounting survives old finally callbacks and
new sessions (never reset counters while old requests are unsettled). All canceled
awaiters settle safely, no unhandled rejections, stale results never cache/render.
No new polling loops, API/store changes or unbounded metadata GET side path.

Genuine RED/GREEN regressions in existing new testfile: state:['paused'] rejected
with stale controls; null applied/rejected receipt cannot release gate/replace envelope;
two held real detailGETs plus uncached selection and explicit archive refresh never
start a third outstanding detailGET, selected/cache reuse still works after release.
Use controlled real-response delay/malformed envelope probes, not fake acceptedworld
DTOs. Focus covering tests during fix; final focused/report/style/whitespace once ready.
Root scoped independent re-review then full gates. Minor desktop header wrapping is
recorded separately for finalwholebranchtriage, not part of this correction.
