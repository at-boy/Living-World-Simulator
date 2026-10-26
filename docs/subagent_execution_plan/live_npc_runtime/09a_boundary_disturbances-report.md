# LN09a worker report — completed-boundary disturbances

Status: **COMPLETE — deliveryee11870 reviewed and task/merged validated.**

The initial producer limitation below is historical and resolved by the format-two
amendment and final worker evidence later in this report. Original LN09 real-provider
acceptance remains separate.

## Historical production prerequisite — resolved by format two

Canonical live work interruption cannot currently apply at the authorized completed
boundary. `FoundersRules.required_progress` is 1 (`founders/model.py`);
`FoundersOfferProvider.offers` uses that value (`founders/runtime.py`).
`WorkExecutionSystem` marks ready, reserves, activates, progresses and completes
available work in the same step; unavailable work becomes BLOCKED
(`work/execution.py`). `FoundersPolicy.from_scenario` compares the retained manifest
with `canonical_policy().to_manifest()` and rejects changing required progress.

The canonical fake-provider RuntimeService and exact replay tests therefore assert
`no_eligible_work`, without retry or fabricated work. Applied work tests use a public
WorkActionHandler custom multi-tick domain fixture and a manager-created reservation
fixture. They prove helper/manager behavior only, **not production applied-work
acceptance**. Root explicitly amended the contract to retain this limitation OPEN.
No phase, canonical policy or domain behavior was changed. A separately authorized
bounded prerequisite is still needed before original LN09 acceptance/task completion.

## Actual scope and authority

Changed only the nine authorized worker paths:

- `src/living_world/archives/model.py`: frozen keyword-only version-one schedule,
  strict closed parser/config grammar and closed immutable boundary audit payload.
- `src/living_world/archives/catalog.py`: narrow pre-reservation same-mode live
  active-policy equality guard; existing live-to-replay omission remains legal.
- `src/living_world/runtime/disturbances.py`: fixed tick-2 helper, centralized
  terminal predicates, canonical camp/config binding, copied strict resources,
  all-timber removal through EntityManager/EventManager, deterministic WorkManager
  selection/blocking and ordered generated event references.
- `src/living_world/runtime/entrypoints.py`: typed keyword validation before
  effects, fresh policy configuration, exact source inheritance/match guard.
- `src/living_world/runtime/ollama_driver.py`: conditional active-policy effective
  fingerprint and completed-candidate finish_tick effect before cursors/commit.
- `src/living_world/runtime/journal_replay.py`: sealed source policy at the same
  phase, exact semantic audit/source predecessor checks, local base normalization,
  rejection of independently appended/initial/same-tick boundary audit rows.
- `tests/test_runtime_disturbances.py`: focused policy, live service, replay,
  compatibility, failure, source protection, gateway and information-boundary tests.
- `docs/npc_information_boundary.md`: new pathway only, documented before code.
- This report.

RuntimeService remains sole writer. Managers own changes and immutable events.
The helper does not create work, invoke private resource systems or directly mutate
state dictionaries. No player API, CLI flag, feedback/controller/provider replacement,
new retained file, migration, version/dependency or runtime export was added.

## Persistence, failure and replay evidence

The schedule remains immutable AttemptConfig input. Absent policies and legacy
scalar labels preserve the exact old effective hash; fresh None/none configurations
and initial checkpoint records compare identically. New active policies separate
request/cursor/source fingerprints. The factory and direct catalog guards prevent
policy enable/clear/change on existing live sources, before reservation/source writes.

Boundary rows accompany advancing snapshot commits. Staging/pause before boundary 2
produces no effect; cold drivers reuse already validated responses without duplicate
request charges. Before/after-boundary children inherit the schedule, retain exact
source snapshots, and apply only when their absolute advancing world tick reaches 2.
Injected entity-manager failure and event failure after entity mutation leave the
service publication and archive at the previous complete checkpoint. This proves
candidate discard, not general in-memory rollback or physical repair.

Offline replay tests forbid transport, compare every advancing complete snapshot,
driver and feedback cursor, preserve gateway outcome checks, and import normalized
boundary audit payloads without request charges. An unchanged extra source checkpoint
makes source/local revisions differ, exercising base_revision normalization. Missing,
extra, wrong-base, altered quantity, event reference and schedule/kind audit records
fail closed without the next target commit. An independently appended boundary audit
also fails closed. Source seal/cursor/request/feedback validation was not weakened.

Next feedback removes now-unavailable shelter/storage offers after timber loss.
Repeated/cold preparation retains the same serialized safe context and owner record
identities. Serialized context excludes schedule/audit fields, quantities, manager
IDs, event references, checkpoint details and raw runtime objects. Stale resource
creation and ready-work volunteer proposals validate as rejected after the manager
change without further mutation; these are defensive unit proofs, not model output.

## RED/GREEN and verification

Interpreter for every test/style command:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
All commands ran in `.worktrees/live-npc-ln09a` with `PYTHONPATH=src`.

- Initial new-test availability run failed collection with 1 error because
  BoundaryDisturbance did not exist. This is an availability check, not a claim of
  a behavioral RED result.
- Behavioral RED: `-m pytest tests/test_runtime_disturbances.py -q -k catalog_cannot`
  failed all 3 cases because direct catalog fork accepted enable/clear/change.
  After root's scope amendment and the narrow guard, all 3 passed.
- Behavioral RED: `-m pytest tests/test_runtime_disturbances.py -q -k appended_outside`
  failed 1 case because replay ignored an extra uncommitted boundary row.
  Captured-source validation corrected this; the regression passed.
- Development exposed the canonical applied-work impossibility: the test expected
  applied and observed no_eligible_work. Root investigated and explicitly amended
  that expectation; it was not hidden or fixed by manufacturing eligible work.
- Intermediate test-only mistakes (missing provider model, treating published()
  as a wrapper, comparing handler object identity, assuming apply() returns a stale
  rejection instead of validating first) were corrected. The final checks below
  are the authoritative focused results.

Final authoritative focused/style results:

- `-m pytest tests/test_runtime_disturbances.py tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py tests/test_runtime_founders_feedback.py tests/test_runtime_launch_request.py tests/test_run_archive_store.py -q`
  — PASS, 292 tests, 0 failures/skips, 71.47 seconds; no warnings. Includes 55
  disturbance cases and the five required adjacent regression modules.
- `-m ruff check src/living_world/runtime/disturbances.py src/living_world/archives/model.py src/living_world/archives/catalog.py src/living_world/runtime/entrypoints.py src/living_world/runtime/ollama_driver.py src/living_world/runtime/journal_replay.py tests/test_runtime_disturbances.py`
  — PASS, all seven Python paths, no warnings.
- `-m black --check src/living_world/runtime/disturbances.py src/living_world/archives/model.py src/living_world/archives/catalog.py src/living_world/runtime/entrypoints.py src/living_world/runtime/ollama_driver.py src/living_world/runtime/journal_replay.py tests/test_runtime_disturbances.py`
  — PASS, seven files unchanged. The preceding scoped Black formatting command and
  Ruff import corrections were applied only to these authorized Python paths.

Full make, examples, canonical/CLI/source/public-serve/wheel gates, independent review,
root whitespace/VCS inspection and integration were deliberately not run by this
worker. Root owns those gates and has instructed no full gates/approval/commit while
the production applied-work prerequisite remains open. No VCS/index/commit operations,
subagents, installs, downloads, real-model requests or other-checkout writes occurred.

## Resumed execution-phase amendment — supersedes initial viability stop above

The preceding report records the reviewed format-one foundation and historical stop.
Root subsequently amended the exact task and saved prompt before implementation,
authorizing exactly twelve paths and a typed one-step intervention inside the
existing atomic WorkExecutionSystem. The old nine-path/no-domain restriction and
production-viability stop are superseded only by that amendment. Final task approval,
renewed independent review and root gates are still pending.

Three additional paths: `src/living_world/work/interruption.py`,
`src/living_world/work/execution.py`, and
`src/living_world/simulation/simulation_engine.py`. All new regression cases remain
in `tests/test_runtime_disturbances.py`; `tests/test_work_execution.py` was read/run
as the required adjacent regression input and was not edited.

`WorkInterruptionRequest` and `WorkInterruptionResult` are frozen keyword-only closed
engine records with strict identities/ticks/outcomes and ordered unique event refs.
The existing work shadow phase retains its ordinary deadline, prerequisite, permanent
target, readiness and availability checks. It interrupts the first executable target
settlement order before charge/progress and before consuming phase labor/tool locks.
READY work is blocked before allocating a reservation; valid reserved work releases
through WorkManager. Other work continues normally. No-result exceptions retain the
atomic phase's old state. Results become visible only after successful shadow-state
publication. None cleanup clears transient references even on a failed engine,
while preserving the failed-tick guard and prohibiting further steps/new requests.

New factory `work_blockage` uses format 2; `resource_loss` remains format 1. Existing
format-one work retains completed-phase no-eligible behavior and its original hashes.
The archive payload keys and world snapshot schema remain unchanged. The full versioned
record binds effective fingerprints and audit fingerprints, distinguishing phases.

Live/replay install now prepares a frozen engine-only token before ordinary step.
Completed boundary 2 translates only the matching phase result into the usual atomic
journal commit. Work events retain execution tick 1. Prepared terminal bases install
no request and audit terminal. An applied effect remains applied if ordinary later
consequences/goal authority make the checkpoint terminal. Event validation checks
existence/tick/kind/subject/settlement binding and manager reason/release evidence;
it does not require a final BLOCKED status after legitimate later authority changes.
Close clears transient request/result/token without serializing them or masking a
failed tick. No scheduler rebuild/replacement, policy constant change, new world
schema, cursor field, external API or CLI flag was added.

### Canonical production-path proof and compatibility

A fake inference broker proposes only the ordinary offered canonical modest-shelter
action. Through the real RuntimeService, proposal gateway and unchanged canonical
composition, format-two work is BLOCKED at completed tick 2 with progress 0, no input
charge and all timber retained. The audit references the ordinary block event at
execution tick 1. Cold resumed children prepare ordinary filtered blocked-work prose,
then normal work retry completes at tick 3 without a repeated disturbance. This
resolves the earlier producer-phase viability gap using production interfaces; custom
multi-tick fixtures are no longer the substitute for that proof. Real-model disturbed
acceptance and the later LN09b manual harness remain outside this prerequisite.

The extended pause/reuse/fork/offline test retains format-one resource and work cases
and adds format-two canonical work. It checks response reuse/no duplicate charges,
before/after-boundary child inheritance, exact world/events/cursors, semantic audit
and differing source/local revision normalization. Sealed replay faults now cover
format-two missing/extra/wrong-base/wrong-target/event/version evidence as well as
format-one faults. Missing or inconsistent prepared policy/request/result and false
event references reject before commit. Terminal-before and later-terminal cases retain
simulation authority.

Atomic phase tests exercise deterministic multiple orders, reservation release,
reuse of the selected laborer and tool by another ordinary order, no selected input
charge/progress, zero work and unavailable work, and ordinary retry. Injected manager
and blocked-event failures publish no result; real service injection additionally
leaves archive/publication at the predecessor with no boundary audit. None cleanup
still leaves failed engine.step/new request prohibited. NPC documentation was appended
before the new phase code; schedule, execution tick, token/result and event references
remain absent from the next serialized NPC request.

### Amendment RED/GREEN and final focused validation

Behavioral RED before new phase code:
`-m pytest tests/test_runtime_disturbances.py -q -k service_factory` — 1 failure,
1 pass, 53 deselected. The canonical work case expected applied but received the
old completed-phase no_eligible_work outcome. After the typed atomic phase and
format-two factory change, the same production-path test passed. A subsequent test
mistake inspected the immutable source after cold resume instead of its new child;
inspection showed the child correctly completed normal retry at tick 3. The test now
checks both retained source and resumed child explicitly.

Intermediate `-m pytest tests/test_runtime_disturbances.py tests/test_work_execution.py -q`
— PASS, 115 tests in 42.77 seconds, no warnings. This includes 81 disturbance cases
and 34 unchanged work-execution regression cases.

Final authoritative amendment validation (same interpreter/PYTHONPATH/worktree):

- `-m pytest tests/test_runtime_disturbances.py tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py tests/test_runtime_founders_feedback.py tests/test_runtime_launch_request.py tests/test_run_archive_store.py tests/test_work_execution.py -q`
  — PASS, **352 tests**, 0 failures/skips, 86.29 seconds, no warnings. Includes 81
  disturbance cases and 34 unchanged work-execution cases.
- `-m ruff check src/living_world/archives/model.py src/living_world/archives/catalog.py src/living_world/runtime/disturbances.py src/living_world/runtime/entrypoints.py src/living_world/runtime/ollama_driver.py src/living_world/runtime/journal_replay.py src/living_world/work/interruption.py src/living_world/work/execution.py src/living_world/simulation/simulation_engine.py tests/test_runtime_disturbances.py`
  — PASS, ten authorized Python paths, no warnings.
- `-m black --check src/living_world/archives/model.py src/living_world/archives/catalog.py src/living_world/runtime/disturbances.py src/living_world/runtime/entrypoints.py src/living_world/runtime/ollama_driver.py src/living_world/runtime/journal_replay.py src/living_world/work/interruption.py src/living_world/work/execution.py src/living_world/simulation/simulation_engine.py tests/test_runtime_disturbances.py`
  — PASS, ten files unchanged after scoped formatting/import corrections.

Status: **DONE_WITH_CONCERNS for renewed independent review**. The original canonical
producer-phase viability concern is resolved by the authorized format-two mechanism
and canonical fake-provider service evidence. Root retains task completion and full
gate authority; actual real-model/LN09b acceptance is not claimed. No full gates,
VCS/index, commits, subagents, installs, downloads, real-model requests or
other-checkout writes occurred. Worker is frozen after this report.

## Root task validation and disposition

Renewed independent solhigh review of full final package SHA256
4deac4eb6897df24feb7f1705999eb5aa6e9f6682767c0a69a3180d2812d84ef:
spec conforms, quality NO SUBSTANTIVE FINDINGS. Canonical RuntimeService/gateway
production-path applied-work proof verified; initial limitation resolved.

- make VENV=.../task24/.venv: PASS2311tests/10existing deliberate skips,384.50seconds;
  actualChrome and39numbered examples. No new warnings.
- Separate make examples VENV=.../task24/.venv: PASS39examples, after fullmake closed.
- Canonical matrix: PASS26retained attempts, twofresh/resume1,3,4/terminalzero-step;
  exact prior fullpayload hashes and26latestcompletecheckpoints opened read-only.
- Archived CLI: PASS7normalattempts including2expectedfailed-uninitialized; exact
  childworld/cursors, uninterrupted/resume/fork equivalence, sourcebytes unchanged.
- Source publicserve: PASS4normalattempts including1failedsetup; pausedidle/Step,
  INT/TERM, exactcoldrestart/fork, authenticated historicalinspection, no credentialleak.
- Offline wheel: PASS11resources/import/routes/CLI plus4actualwheel-serve attempts
  with same lifecycle/restart/history checks. No installations/network/model calls.
- Whitespace/cached diff checks: PASS. Reviewed source/tests/pyproject unchanged bymake.

Root retained41normalacceptanceattempts including truthful failures. Taskcommit follows
final examples/source check; integration must repeat gates. Both-backend runtime and
exact operator inference traces are newly required prerequisites before original LN09
acceptance. No main/tag actions or model/provider acceptance claimed here.

## Root merged validation

Deliveryee11870 merged cleanly into feature. Repeated make: PASS2311tests/10existing
skips,382.64seconds, actualChrome/39examples. Separate examples PASS39; whitespace
and reviewed source/tests/pyproject equality PASS. Canonical26readonly/exacttaskhashes,
CLI7/sourceServe4/wheel11resources+actualServe4 PASS,41normalattempts retained including
expected failures. Owner-local masterplan diff SHA unchanged; no main/tag refs moved.
No real-model acceptance claim: backend and private trace tasks remain before full LN09.
