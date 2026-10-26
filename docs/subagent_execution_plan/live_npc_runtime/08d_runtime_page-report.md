# LN08d implementation report

Status: complete; independently reviewed, root task/merged validated and integrated
by the merge containing this report. Root retains completion authority. Work is in the assigned `live-npc-ln08d` checkout. No commits,
index operations, branch/worktree changes, subagents or other-checkout writes were
performed by the worker.

## Delivered scope

The public packaged `/runtime` page authenticates with the existing operator API,
shows operational state and the last durable world separately, submits existing
service commands, follows durable receipts and browses saved attempts/checkpoints.
The only Python adapter additions are synchronous page/allowlisted asset routes.
Package data retains the original eight resources and adds three runtime resources.
No API/auth/child protocol, schema, provider, CLI, domain owner or dependency changed.

Credentials, request state and immutable command envelopes remain closure memory.
Session generations cancel obsolete requests; selection/frame epochs reject obsolete
source fetches and readiness. Authentication failures and invalid CSRF nonce grammar
clear credentials/data. Serial status polling retains visibly stale last-complete data
and its last-refresh label on failure. Stable control/receipt nodes preserve keyboard
focus through polling. Server outcomes, versions and checkpoint ticks are displayed
without inferred success or optimistic advancement.

Commands retain their UUID/action/operational-version envelope through uncertain
network delivery. Only explicit Retry delivery resends it. Durable GET receipts
resolve queued commands; duplicate action gates do not block an independently allowed
Pause during pending Step. A late applied receipt cannot release a newer command's
same-action gate. Retry model remains a separate explicit runtime action.

Archive rows retain catalog order and show start, parent/checkpoint, last tick,
mode/scenario, lifecycle and actual outcome. Two detail workers populate outcomes,
keeping unavailable/corrupt rows. Detail cache belongs to an explicit archive-refresh
and session generation. Details show configuration/source, actual outcome and typed
latest-50 journal/total. No-world attempts expose no fabricated checkpoint. Historical
selection hides live controls and embeds one fixed authenticated checkpoint. All
archive activity is GET-only; the existing pinned child protocol is reused unchanged.
All untrusted prose is rendered as text. The connected 390px table scrolls within its
container, and explicit navigation/login alone changes focus.

## Test-first and correction evidence

Named RED checks were observed for the absent `/runtime` resource (404), missing
historical mode/parent source label, malformed-nonce session cleanup, missing archive
row start/parent/tick fields, a late applied receipt releasing a newer command gate,
polling replacing a focused control, missing contained narrow-table overflow and a
stale label losing the last-refresh time. Each has a passing targeted regression.
The first resource test also requires exact package data and secret-free assets.

Browser integration uses actual loopback uvicorn, installed Chrome and real runtime
services/archives. It covers login/wrong token/logout, 403 and malformed status/nonce,
safe integer/prefix/version validation, double-click one-effect Step, real stale
operational-version rejection, Resume/terminal, delayed fake-provider responsiveness,
pending Pause versus durable acknowledgement, explicit model Retry and Stop.
Loss tests abort before admission or after real admission and verify explicit identical
envelope retry plus at-most-one effect. A delayed actual applied duplicate receipt
exercises replacement-command identity. Other tests cover delayed logout/reconnect
and source results, exact origin/source/schema and old-frame denial, same-frame live
pin/filter/focus/caret preservation, fixed history during live advancement, archive
bytes/mtime stability on historical refresh, literal malicious configuration/journal,
setup/corrupt rows, actual outcome and latest 50 of 53 journal entries, keyboard Enter
login and connected narrow-viewport overflow.

Early fixture-only failures were corrected to match existing contracts: Retry after
a pending Pause returns to paused tick zero until another explicit Step; AttemptConfig
rejects unknown settings; journal fixtures must use registered typed entry kinds.
No production semantics were changed for those fixtures. One early shell invocation
used an unavailable `python` alias; subsequent work used the assigned interpreter or
available `python3`. All fixtures use authorized temporary archives; there were no
normal manual simulations or real model calls.

## Validation

`TASK_PY` is
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.

- Initial resource RED: `PYTHONPATH=src $TASK_PY -m pytest
  tests/test_runtime_browser.py::test_public_runtime_resources_and_packaging -q`:
  1 failed, expected missing route; subsequent GREEN: 1 passed.
- Intermediate runtime-browser sweep: `PYTHONPATH=src $TASK_PY -m pytest
  tests/test_runtime_browser.py -q`: 15 passed before added regressions.
- Intermediate five-file focused sweeps: 125 passed, then 126 passed as the final
  focus regression was added. Subsequent source corrections each passed the named
  affected regression before the final sweep.
- Final focused command: `PYTHONPATH=src $TASK_PY -m pytest
  tests/test_runtime_browser.py tests/test_runtime_inspector_browser.py
  tests/test_runtime_operator_api.py tests/test_world_inspector_ui.py
  tests/test_world_inspector_browser.py -q`: 126 passed in 123.31 seconds; no warnings or skips. This final run includes
  all 19 runtime-page cases and the four unchanged API/inspector regression files.
- `$TASK_PY -m ruff check src/living_world/api/operator.py
  tests/test_runtime_browser.py`: passed, no findings.
- `$TASK_PY -m black --check src/living_world/api/operator.py
  tests/test_runtime_browser.py`: passed, 2 files unchanged.
- Scoped whitespace scan (trailing whitespace and final newline): all nine worker
  deliverables checked. Root performs authoritative `git diff --check` because the
  worker contract forbids VCS operations.

Self-review checked route/resource allowlists, original package entries, field/ID/
number validation, per-session and selection guards after awaits, command identity
and admission-versus-effect handling, no automatic POST/provider retry, text-only
rendering, same-origin exact-source child connection and read-only historical paths.
Existing API and inspector test files were not modified.

Root-owned remaining gates: independent specification/quality review and corrections,
full task and merged-tree `make`, separate `make examples`, VCS whitespace/boundary
review, retained canonical/new CLI checks, and actual wheel eleven-resource checks.
This report does not claim those gates, a CLI launcher, real-model acceptance or final
milestone completion.

## Independent review correction round 1

The root-authorized correction amendment addresses three confirmed P2 findings:
primitive runtime-state validation, required integer receipt revisions and one shared
archive-detail concurrency bound. No CSS or API/owner changes were made in this round.

State membership now first requires a primitive string, so `["paused"]` cannot
coerce into a known state and enable controls. Receipt revisions now require safe
nonnegative integers, matching `CommandReceipt`; null applied/rejected receipts cannot
release the action gate. Malformed POST or GET receipts retain the original immutable
envelope as uncertain until a valid durable receipt or explicit identical delivery.

A single FIFO archive-detail scheduler shares current-generation promises/cache
between outcome rows and selection. Its two active slots persist across refresh,
logout and reconnect until each actual request's finally. Refresh/logout reject
obsolete queued awaiters safely; completed obsolete reads cannot cache or paint data.
Selection checks archive generation before starting checkpoint reads and before any
success/error rendering. No polling loop or metadata side path was added.

Correction regressions use controlled actual uvicorn/Chrome responses. The six cases
cover array state; null applied/rejected POST receipt; null applied GET receipt; and
two held detail GETs with uncached selection or explicit refresh. The latter verify
maximum two outstanding reads, one request per selected attempt/current generation,
cache reuse, obsolete queued cancellation and no unhandled browser errors. The delay
harness initially needed request identities/active slots reserved before yielding to
`route.fetch`, and a complete held-response drain; those fixture issues were fixed.
An intermediate reconstruction of the old detail-loading paths then reproduced
selection opening a third and refresh overlapping old reads. The final exact-baseline
RED proof uses the root-exported original review asset, with no concurrent tests and
the corrected source restored immediately afterward.

Correction validation uses the same assigned interpreter and focused command above:

- Six targeted correction cases on corrected source: 6 passed in 14.57 seconds.
- Same six against the root-exported exact original review asset: 6 failed in
  26.91 seconds, all six expected contract failures. Corrected JS restored afterward.
- Final five-file focused command on restored corrected source: 132 passed in
  137.29 seconds, no warnings or skips (25 runtime-page cases plus 107 unchanged
  API/inspector cases). No source/test edits occurred after launch.
- Scoped Ruff and Black --check: passed, 2 Python files unchanged; nine-file
  trailing-whitespace/final-newline scan passed. No unresolved style findings.

The previous 126-test result remains historical pre-correction evidence. Root
independent re-review/full task/merged-tree gates remain required before integration.

## Root review, task validation and usage checkpoint

Independent review found three P2s, all corrected in round1. Scoped re-review:
primitive string state ADDRESSED; mandatory integer receipt/uncertain envelope
ADDRESSED; shared two-slot detail scheduler ADDRESSED. SPEC/QUALITY PASS, no open
substantive findings. Root visual desktop/mobile captures show usable layout; minor
archive header word wrapping remains recorded for final whole-branch triage.

Root authoritative task commands/results:
- make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv:
  PASS 2140 tests / 10 existing deliberate skips,303.65 seconds; actual Chrome and
  all39examples. Separate make examples with sameVENV after make closed: PASS39.
- git diff --check and --cached --check: PASS. git diff --exit-code --src tests
  pyproject.toml relative reviewed staged tree: PASS; gates did not alter source.
- recorded_matrix.py: PASS exact prior schema12 hashes, fresh/resume1,3,4 and terminal
  zero-step;26normal CLIarchives retained, latest complete checkpoints opened readonly.
- archived_cli_acceptance.py: PASS7retained cases including2expected failed-uninitialized,
  exact child worlds/cursors, resume/fork equality and unchanged source bytes.
- wheel_runtime_check.py: PASS isolated offline build/extraction/import, exact11
  resource bytes, runtime/inspector public asset routes, protected status and CLIhelp.
  No environment installs/downloads or normal simulations. Initial root helper failed
  because this VENV has no pip; installed build backend was used instead. A subsequent
  compressed-wheel import probe failed for namespace packages; isolated extracted-wheel
  import is the valid corrected check. These failed artifacts remain retained; no
  product source correction was needed. Building from isolated source copy preserved
  tracked generated metadata in the task checkout.

Evidence: feature .superpowers/sdd/2026-10-19-live-npc-runtime/ln08d-review-1.diff,
ln08d-fix-1.diff,ln08d-reviewed-final.diff,ln08d-review-initial/final.md;
ln08d-task-make.log,ln08d-task-examples.log,ln08d-task-matrix,ln08d-task-cli,
ln08d-task-wheel-final/results.json (earlier wheel failures also preserved), and
ln08d-runtime-desktop/mobile.png unit-fixture visual captures.

Usage checkpoint: save/push this reviewed task delivery, then pause before10%remaining.
Feature SOURCE NOT MERGED; resume with this delivery's integration/repeated merged
gates only, not redispatched implementation/review/task gates. Browser page is tested
against real services; public CLIserve and actual installed-Ollama acceptance remain
uncompleted. Preserve all branches/worktrees and the feature owner's local edit.

Pause checkpoint: task delivery fdfeecf committed and pushed on the preserved
codex/live-npc-ln08d-runtime-page branch. Feature source remains unmerged.

## Root feature integration — October26,2026

Delivery fdfeecf merged without source conflicts; root checkpoint wording conflicts
resolved. Source/tests/pyproject exactly match reviewed delivery after validation.
- make VENV=shared absolutevenv: PASS2140,10existing deliberate skips,302.60s;
  actual Chrome and39examples, no new warnings.
- Separate make examples after make closed: PASS39.
- git diff --check and cached equivalent: PASS.
- recorded_matrix.py: PASS exact historical hashes/outcomes;26retained normalCLI
  attempts, all latest complete checkpoints opened read-only; matches task results.
- archived_cli_acceptance.py: PASS7retained attempts including2expectedfailed-
  uninitialized, exact initialworld/cursors, sourcebytes unchanged, resume/fork parity.
- wheel_runtime_check.py: PASS offline isolated build/extracted import,11resource
  bytes, public runtime/inspector, protected status and CLIhelp;0normal simulations.
Evidence in ignored workspace ln08d-merged-{make,examples,matrix,cli,wheel}.
Task checkout/branch preserved. Owner local-plan diffSHA294b20313ae2de248301fa20bbb4f9c312d51efa4851a434466f98a588dd93e6
unchanged. Protected main/milestone/tag unchanged. Three prior P2s closed; minor
archive-header wrapping remains deferred final broadreview. Public CLIserve and real
installed-Ollama acceptance are still outstanding; this is not full LN07–LN09 completion.
