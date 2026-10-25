# LN08c implementation report

Status: independently reviewed; task and merged root validation PASS. Deliveryc3a5b69
is integrated by the feature merge containing this report. Work performed in the assigned
`live-npc-ln08c` checkout against the authorized LN08c contract and saved prompt.

## Delivered behavior and boundary

- `operator.py`: authenticated live/historical inspector HTML reuses the existing
  resolver and its sole RevisionSource. Authorization runs before source access;
  synchronous handlers perform source/resource work off the event loop. Only
  canonical validated prefix/kind attributes are inserted at the exact template
  marker. Missing marker returns safe conflict. Two existing packaged assets are
  publicly allowlisted; existing no-store middleware covers responses.
- Existing HTML/JS: standalone template remains unconfigured and retains its
  default routes. Embedded bootstrap validates canonical safe-integer revisions
  and existing 32-character lowercase UUID4 hex identities, inherited effective
  `window.origin`, and parent relationship. A frozen bootstrap copy and closure
  hold connection state. Strict source/origin/plain-object/exact-key messages
  implement ready, one-time connect, live-only pin and terminal clear. Credentials
  remain memory-only and are supplied solely as Bearer headers to closed GET routes.
- Refresh captures prefix/header/signal once, aborts prior work, and retains the
  generation guard for DOM, errors and busy state. Background pins preserve view,
  entity/event selection, return target, History text, and semantic focus/caret
  when focus has not moved. Labels/spatial guidance distinguish pinned snapshots.
- New tests use a test-only parent and actual uvicorn/Chrome authenticated
  HTML fetch/srcdoc handshake and checkpoint DTO routes. No route.fulfill or
  fabricated acceptance DTOs are used. The controlled delay wraps real responses.
- Inspector documentation describes endpoints, parent responsibilities, exact
  protocol, memory-only credentials, fixed history and refresh behavior.

Only the six worker-allowed paths were created/edited. Root-owned contract/prompt
clarifications visible in this checkout were supplied by root. No CSS, parent
runtime page, CLI, owner, domain, provider, schema or dependency changes. No VCS
mutation, normal manual simulation, real-model use, installs or downloads. Test
fixtures use permitted temporary archives. Existing manager/system/event and NPC
information boundaries are unchanged; these remain privileged operator DTOs.

## Tests and development evidence

`TASK_PY` denotes
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
Browser commands ran with approved escalation for actual loopback/Chrome access.

- RED: `PYTHONPATH=src TASK_PY -m pytest tests/test_runtime_inspector_browser.py -q`
  initially failed 1 test: protected HTML returned missing-route 404 instead of
  authorization 401. After route implementation: 1 passed.
- RED: named `test_embedded_waits_for_exact_parent_schema_and_clears` failed 1:
  original inspector fetched default world routes instead of waiting for its
  operator connection. After protocol implementation: 1 passed.
- Additional browser checks initially reported 3 failures/4 passes because the
  test parent connected before deferred script initialization. The harness now
  waits for initialized child status; the same cases then passed, 7 total.
- Self-review RED: named `test_connection_uses_initial_validated_source_kind`
  failed 1: mutating the bootstrap DOM changed subsequent pin acceptance. Capturing
  a frozen initial bootstrap copy fixed it; named case passed 1.
- Final exact focused command:
  `PYTHONPATH=src TASK_PY -m pytest tests/test_runtime_inspector_browser.py tests/test_runtime_operator_api.py tests/test_inspection_api.py tests/test_world_inspector_ui.py tests/test_world_inspector_browser.py -q`
  **120 passed**, 71.60 seconds; no warnings/skips. This includes 10 new cases
  and unchanged standalone/API assertions. An earlier focused run before the
  bootstrap regression addition passed 119 tests.
- `TASK_PY -m ruff check src/living_world/api/operator.py tests/test_runtime_inspector_browser.py`:
  passed, 2 paths. Initial scoped lint found unused imports/binding and import
  ordering; corrected before the clean check.
- `TASK_PY -m black --check src/living_world/api/operator.py tests/test_runtime_inspector_browser.py`:
  passed, 2 paths unchanged after formatting.
- `git diff --check`: passed. An initial editing command used unavailable `python`;
  rerun with installed `python3`, with no source change from the failed invocation.

New checks exercise auth-before-source and safe corruption failures, canonical
HTML/query nonconfiguration/no-store/assets, exact parent/origin/schema rejection,
foreign sibling rejection, zero preconnection GETs, repeated-connect/malformed-pin
rejection, authenticated GET-only requests, credential absence from DOM/storage,
pending-clear termination, partial/invalid bootstrap, fixed historical pin and
byte/mtime inventory invariance, multipanel prefix coherence, stale pin/navigation
races, History filter/caret, entity/return focus, user-chosen focus preservation,
literal malicious entity names, narrow viewport/keyboard operation, recovery, and
immutable initial bootstrap. Existing standalone tests additionally retain their
original event/history, stale response, missing entity, spatial and focus checks.

## Self-review and remaining gates

Reviewed source bootstrap insertion/allowlist, shared resolver ownership, exact
message and prefix grammar, fixed refresh configuration, cancellation/generation,
focus key comparisons without interpolated selectors, literal text rendering,
standalone compatibility, test-only parent/delay scope, and allowed-file boundary.
No outstanding implementation concern identified by worker self-review.

Independent SPEC/QUALITY review and any corrections/re-review remain root-owned.
Root must run full task and merged-tree `make`, separate examples, whitespace and
retained canonical/new CLI acceptance as required by the broader authorization
before implementation commit/integration. Worker did not repeat those gates, per
explicit task contract. Parent runtime/control UI, CLI serving, installed-wheel
acceptance and actual Ollama acceptance remain their separately authorized stages.

## Root independent review and task gates

Reviewer/root/ln08c_review (gpt-6.1-sol high): SPEC PASS, QUALITY PASS, NO SUBSTANTIVE
FINDINGS. No correction loop required. Stable ln08c-review-1.diff and final findings
ln08c-review-final.md retained in ignored feature plan workspace. Root separate actual
Chrome probe confirmed parent-control focus survives a delayed child pin response.

Root make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv:
PASS2115tests/10existing deliberate skips,237.21s; actual Chrome and39examples.
Separate make examples with sameVENV after make closed: PASS39. git diff --check and
--cached --check PASS; git diff --exit-code --src tests relative reviewed staged tree
PASS, no source/test change after review/gates. Canonical recorded_matrix.py PASS
exact prior schema12 hashes/fresh/resume1,3,4/terminal zero-step;26retained CLIattempts
latest checkpoints opened readonly. archived_cli_acceptance.py PASS7retained cases
including2expected failed-uninitialized, exact worlds/cursors and unchanged source.
Logs/every archive: ln08c-task-make.log,ln08c-task-examples.log,ln08c-task-matrix and
ln08c-task-cli under .superpowers/sdd/2026-10-19-live-npc-runtime in feature checkout.
Root approves focused task delivery; integration/repeated merged gates pending.
All branches/checkouts/ownerpatch/protectedrefs preserved. Parent controls/CLIserve/
real-model acceptance are not completed by this delivery.

## Root feature integration — October26,2026

Deliveryc3a5b69 cleanly merged; reviewed source/tests exactly match delivery. Root
duplicated contract clarifications were backed up and verified present in delivery
before restoring only those two root-owned files; owner masterplan edit untouched.
Repeated merged make PASS2115tests/10existing deliberate skips,237.15s, actual Chrome
and39examples; separatemakeexamples aftercompletion PASS39. Whitespace/stagedwhitespace
PASS; git diffc3a5b69 --exit-code --src tests PASS. Canonical matrix exactly matches
taskresults;26archives latestcompletecheckpoint opened readonly. NewCLI7retainedcases
including2expected failed-uninitialized PASS, exactchildworld/cursors and sourcebytes
unchanged. Evidence ln08c-merged-make/examples.log, -matrix and -cli in sameworkspace.
Allbranches/worktrees preserved. Next9path parent runtimepage contract, then CLIserve;
actual installedOllama acceptance remains LN09, not claimed by this delivery.
