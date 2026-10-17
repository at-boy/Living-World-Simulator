# Whole-v0.6 independent review — initial checkpoint and completed continuation

Reviewed implementation baseline: milestone `58b6ba7`, against `main` `12f2f17`.
Read-only review; no source/VCS changes, agents, or full-suite runs. This report
is the sole requested output mutation. Task24 final metadata/docs were outside
this review. Root requested immediate checkpoint before full coverage completed.

## Findings

### P1 — Public assignment can overwrite reservation history after execution

**Paths/symbols:** `src/living_world/work/execution.py`,
`WorkExecutionSystem.step/_execute`; `src/living_world/work/manager.py:249`,
`WorkManager.assign_and_reserve`, and `:1021`, `_candidate_reservation_id`.

The engine's long-lived WorkManager initializes `_next_reservation_id` from the
world once. Automatic execution creates another WorkManager against a shadow,
allocates reservations there, and commits WorldState fields without updating
the live manager's counter. The latter's candidate method merely formats its
cached counter; `assign_and_reserve` then assigns into `work_reservations[rid]`
without a collision check. Consequently a later public assignment can replace
an earlier reservation, destroying durable history. The public volunteer action
uses that same long-lived manager. This is a normal supported composition of
automatic execution and public manager/gateway operations, not raw-state mutation.

Deterministic example from code: fresh engine counter=1; automatic work execution
creates and releases `work_reservation_000001`; a subsequent ready work assignment
through `engine.work` chooses `work_reservation_000001` again. The first completed
work then has no matching terminal release. `validate_loaded_state` rejects it;
the repository does not validate work before saving, so a checkpoint can become
unloadable. A resumed engine instead initializes its counter from saved history,
also making subsequent assignment diverge from uninterrupted execution.

**Evidence level:** confirmed allocation/commit/write path by code inspection;
runtime reproduction was not run because root requested the immediate checkpoint.
Suggested focused reproduction: create two one-labor work orders, complete the
first with `engine.step()`, mark the blocked second ready, assign it through the
public manager or volunteer gateway, and verify both histories plus round-trip.
Repair must preserve pure preflight and failed-phase ID rollback contracts.

### P1 — Goal identifiers and exact thresholds escape the NPC boundary

**Paths/symbols:** `src/living_world/cognition/information_boundary.py`,
`NPCInformationBoundary._internal_identifiers/_authoritative_numbers`;
`src/living_world/goals/manager.py`, `GoalManager._validate_goal/npc_interpretation`.

Goal/objective IDs permit arbitrary nonempty strings, but the NPC boundary omits
the goal/objective collections. Its prefix regex therefore protects only
conventionally named IDs. It also omits criterion numbers from goals/objectives
unless referenced by a settlement-stage program. The goal interpretation
validator only checks conventional ID spellings. An explicitly selected
interpretation can therefore carry actual internal IDs and exact hidden criteria
through the ordinary context assembler, contrary to AGENTS and Task18's contract.

**Executed reproduction:** `PYTHONPATH=src .venv/bin/python - <<'PY' ... PY` using
only public `SimulationEngine`, `Definition`, `GoalManager.create`,
`GoalManager.npc_interpretation`, and `NPCContextAssembler.assemble` APIs.
Created objective ID `secret_target` with `ResourceMinimumCriterion("water",987)`
and goal ID `private_mandate`, with interpretation:
`Follow private_mandate toward secret_target and collect 987 water.`
Then supplied the returned interpretation via `capability_descriptions`.
Result: exit0; context.self_knowledge contained that exact string unchanged.
No raw WorldState mutation or custom boundary was used. The fresh owner's
attributes were empty, so the criterion was the authoritative source of987.

Add regressions for arbitrary actual goal/objective IDs and completion/failure
criterion numbers outside stage programs, exercising the public assembler and
replay-visible text paths. Preserve safe qualitative prose and the narrow existing
dispatch-action-key exception.

## Coverage and limits

Read AGENTS, milestone/completion acceptance and constraints, Task23 plan/prompt
and report excerpts, Task18 contract, relevant Task20b contract sections, the
whole-milestone file-change summary, and root rulings. Inspected scheduler ordering
and failed-tick poisoning; runner terminal/checkpoint behavior; replay binding,
cursor/event bijection, preparation and gateway routing; scenario binding;
work execution/reservations/lifecycle; consequences and maintenance destruction;
goal evaluation and accumulating-history rule; stage mutation/evaluation;
repository save/load and schema-dependent domain assembly; entity lifecycle;
NPC context and prose filtering; canonical preparation/offers/terminal predicates;
GET-only API routes and snapshot conversion structure.

This was targeted cross-system review, not line-by-line coverage of the entire
1.74MB diff. Remaining unchecked areas include complete founders setup validation,
all schema migration branches and deserializers, complete spatial algorithms and
perception, browser JavaScript behavior, all prior task reports, public-export
completeness, and independent installed-wheel/assets verification. Existing root
validation and per-task reports are supporting evidence, not independently rerun
proof here. No comprehensive clean-audit or release-readiness claim is made.

**Disposition:** substantive findings require root evaluation and bounded
correction/review. No processes remain running.

## Resumed remaining-coverage review — October17,2026

Primary `7d75b20` retains reviewed implementation `58b6ba7`; reviewed only the
previously uncovered areas. The initial findings remain pending Task24a; this
section does not review their fixes or Task24 final metadata/docs. Two further
substantive findings follow. Both were promptly sent to root for disposition
before expansion of the bounded correction wave.

### P1 — Maintenance destruction produces an unloadable spatial checkpoint

**Paths:** `src/living_world/needs/consequence.py:337`,
`ConsequenceManager._maintain`; `src/living_world/spatial/manager.py:117`,
`validate_loaded_state`, and `:198`, `_live_entity`;
`src/living_world/repositories/sqlite_repository.py:1114`.

Maintenance can legitimately destroy a placed capability through
`EntityManager.mark_destroyed`. Its placement remains, as Task19a expressly
requires preserving placement/history. A completed tick and repository save
succeed, but loading invokes spatial validation that rejects every destroyed
placement subject. Thus ordinary domain evolution can replace a valid checkpoint
with one that cannot resume. Work-built capabilities are placed, so this is a
cross-domain lifecycle defect rather than an unsupported hand-built snapshot.

**Executed reproduction:** `PYTHONPATH=src:tests .venv/bin/python - <<'PY' ... PY`;
used existing `test_consumption_maintenance._world()` manager-created fixture,
`engine.spatial.place(entity_id=capability, geometry=Point(1,1))`, and a maintenance
policy requiring missing stone, initial condition1, deterioration1. Called
`engine.step()`, then public `SQLiteRepository.save_world/load_world` in a
temporary directory. Tick completed at1; capability destroyed at0; placement
retained. Save succeeded; reload raised `RepositoryLoadError` caused by
`Destroyed entity 'entity_000002' cannot be placed.` Exit0 with the expected
exception captured; no raw-state edits. Root must reconcile historical-placement
validation and live placement mutations without silently deleting history or
prohibiting the intended deterioration of work-built capabilities.

### P1 — Spatial cycle validation can hang on a descendant of the cycle

**Path:** `src/living_world/spatial/manager.py:190`, `_reject_cycle`.

The ancestor traversal stops only when it reaches the candidate entity. For
`Leaf -> Child -> Root -> Child`, validating Leaf never reaches Leaf and loops
forever. Repository loading validates placements in their payload order, so a
malformed snapshot with Leaf first hangs instead of raising `RepositoryLoadError`.
The existing cyclic-parent protection is insufficient for this corrupt-state
case, violating Task15b's explicit cycle-rejection load contract. The same helper
is used for live spatial validation against existing ancestor state.

**Executed reproduction:** `PYTHONPATH=src .venv/bin/python - <<'PY' ... PY`;
created and saved a valid three-level bounded world through public entity/spatial
managers. Edited only the temporary SQLite JSON to make Root's parent Child and
order placements Leaf/Root/Child. Invoked public `load_world()` in a child process
with `subprocess.run(timeout=2)`. Result: timeout reproduced; Python killed and
reaped the child. No processes remain. Add repeated-ancestor detection and a
bounded malformed-load regression with a descendant preceding cycle members.

### Remaining coverage completed and evidence limits

Inspected complete founders setup/model/materialization code against Task23's
fixed manifest, shadow commit, initial/resume distinctions, immutable definitions,
setup marker, dynamic attachment cardinality and timing rules. Cross-checked
the corrected23 report and corruption tests; no additional founders finding.

Reviewed schema-dependent collection gates and milestone deserializer variants:
placements, external references/dispatches, goals/objectives/evidence, needs,
consequences, work targets/states/reservations, stages, and replay records. Read
the existing migration/corruption tests covering legacy defaults, schema9 unpaid
work, stage ordering and schema12 cursor/binding constraints. The two spatial
findings above are the newly identified load failures.

Read spatial geometry/manager/perception implementations and relevant15b/15d
reports: half-open bounds, containment/overlap, deterministic ordering, doubled
centers, direct-road selection and prose boundary enforcement. The findings
concern lifecycle/load behavior, not a proposed change to geometric conventions.

Reviewed complete packaged inspector JavaScript: fixed same-origin GET routes,
encoded entity references, literal text/SVG labels, shape/numeric validation,
generation guards, refresh/error handling, accessible list fallback and navigation.
Read actual Chrome harness and all-outcome snapshot test plus15/15c/23 acceptance
reports. Source behavior supports the GET-only/state-preservation claims; no
additional browser finding. Dense-label overlap is documented with list fallback.

Checked declared root/founders exports, explicit eight asset package-data entries,
portable five-file temporary materialization, console-entry configuration and
root's actual installed CLI/wheel/loopback evidence in23report. No redundant build,
full suite, or browser matrix was run. Installed-artifact execution remains root
evidence, not independently repeated evidence. Version0.5.0 is intentionally
unchanged in this source baseline pending Task24's separately reviewed0.6.0rc1.

The previously listed coverage gaps are now addressed by targeted source,
contract/test and report review. This is not an exhaustive line-by-line proof of
every historical diff. Overall audit has four substantive findings; a clean final
disposition requires scoped independent review of Task24a corrections and the
separate final metadata/documentation diff, followed by root validation.


## Root final code-audit disposition

Allfour findings were reproduced and repaired in isolated Task24a deliverycfa50b6.
Independent scoped code review judged all4ADDRESSED, spec/qualityPASS, NO
SUBSTANTIVE FINDINGS. Task and merged make1416passed/10existing skips,76Chrome,
examples001–039; separateexamples/whitespace and canonicalfresh/resume matrices
passed. Allthree canonical full-payloadhashes unchanged. Targetedremainingaudit
coverage above completed; no additional substantive source findings remain.
Finalrelease metadata/docs review and actual0.6.0rc1installed/minimumPython/root
releasegates remain Task24 responsibilities; this is code-audit disposition.
See [Task24a report](../subagent_execution_plan/v0_6/24a_v06_audit_corrections-report.md).
