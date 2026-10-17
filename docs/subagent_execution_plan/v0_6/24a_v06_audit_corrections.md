# 24a — v0.6 release-audit boundary and reservation corrections

## Authority and scope

The approved full completion sequence and Task24 contract require isolated
corrections for concrete implementation findings. This task repairs existing
behavior, no new domain capability. From current milestone7d75b20, branch
task/24a-v06-audit-corrections. Task24 metadata/docs remain paused and preserved
uncommitted in .worktrees/task24. Owner0.6.0rc1/main/tag boundaries unchanged.
Read committed docs/orchestrator_handoff/v0_6_release_audit_2026_10_17.md as exact
finding evidence. Root retains architecture/scope/disposition/gates/integration.

## A — complete existing NPC information boundary

The public GoalManager interpretation -> NPCContextAssembler path currently
passes actual non-prefix IDs private_mandate/secret_target and exact hidden
ResourceMinimumCriterion threshold987. No stage program participates. Preserve
arbitrary valid goal/objective IDs and manager/domain architecture; fix the final
existing NPCInformationBoundary rather than introducing new ID restrictions,
manager-to-cognition dependencies or raw-state access into NPC context.

Extend _internal_identifiers to include all goal_definitions,goal_states,
objective_definitions,objective_states keys. Extend _authoritative_numbers using
the existing typed dataclass numeric walker over those four collections, covering
completion/failure criteria, deadlines and state/evidence numeric metadata.
Preserve existing filters/provenance and fixed safe error text; do not weaken
context/label/prose/argument checks or the exact existing public structured
DISPATCH_ACTION_KEY exception. No direct numeric policy appears in accepted NPC
context. Qualitative prose still passes. No persistence/model/schema changes.

Tests must reproduce through public GoalManager and NPCContextAssembler before
fixing. Test each actual custom goal/objective ID and goal/objective completion/
failure numeric threshold separately so one rejected token cannot mask another;
cover non-stage goals, selected qualitative interpretation and direct replay-
visible prose boundary. Assert validation is read-only. Use distinct thresholds
absent from entities/needs/stages to prove the newly protected source.

## B — reservation IDs after authoritative shadow commit

Runtime-reproduce the code-traced collision before changing allocation. Normal
WorkExecutionSystem creates/releases reservation1 through its shadow WorkManager,
but engine.work retains counter1. A subsequent public assign_and_reserve or
volunteer must preserve existing immutable reservation history instead of reuse.
No raw-state mutation may be required for the core reproduction. Use normal
manager lifecycle to ready/assign the next work order as necessary.

Make reservation candidate allocation pure and authoritative: choose numeric
max(local _next_reservation_id, existing _next("work_reservation",state map)),
format existing work_reservation_ six-digit convention. On successful assignment
set local counter to allocated numeric suffix+1. Existing snapshot/restore owns
failure rollback, including cache/history/events; no selection/preflight mutation.
Preserve _candidate_work_id, schema/events, public signatures, scheduler/shadow
commit and domain mutation ownership. No wholesale manager/cache rewrite.

Regressions: automatic completion followed by public assignment/volunteer cannot
overwrite prior record; repeated assignment monotonically allocates; manager
validate_loaded_state and repository round-trip succeed; uninterrupted and reloaded
engine allocate identical IDs/full payload for equivalent operations; failure
injected after choosing a skipped/highwater candidate preserves state/history and
retry ID/event behavior. Existing focused work lifecycle/rollback tests remain.

## Allowed files exactly

src/living_world/cognition/information_boundary.py;src/living_world/work/manager.py;
tests/test_npc_information_boundary.py,tests/test_npc_context.py,
tests/test_work_orders.py,tests/test_work_execution.py,tests/test_work_action_gateway.py;
docs/npc_information_boundary.md,docs/technical_debt.md,CHANGELOG.md,
docs/project_journal.md,docs/backlog.md;thisplan/matching-prombt.md/required-report.md.
No other runtime/DDL/model/API/UI/asset/goalmanager/replay files. Amend plan+prompt
before necessary expansion, do not hide unrelated changes or retune canonicalrules.

## Validation, review and completion

One bounded worker implements both findings as one final-review correction wave,
TDD RED/GREEN and strict annotations Python>=3.11. Worker focused relevant tests
and formatting/whitespace only, no VCS/agents/fullmake/examples/wheel. Report exact
commands/counts, actual reproduction, fixes/compatibility/limits. Independent
read-only scoped review judges both findings plus new breakage; root resolves
findings and re-reviews. Root then make,separateexamples,whitespace,canonical
source fresh/resume full-payload matrix, required merged gates. No claimcomplete
until source+mergedcurrentgates/review/pushedrefs verified. Update currentbrief
and restore Task24 work dependency-order without overwriting its dirtycheckpoint.

Whole-milestone review coverage remains incomplete beyond these fixes. Complete
remaining targeted audit and final Task24diffreview/release gates before readiness.
Stop/checkpoint before ownerfivehour10%floor. No main/tag/publication/v0.7.


## Root clarification — assignment failure scope

Failed public assignment restores the existing WorkManager snapshot surface:
world work/reservation/event mappings and work/reservation counters. Its retry
reservation ID remains authoritative and deterministic. The existing EventManager
private allocator can retain gaps after an event-record failure; this correction
does not rewind that separate allocator, add EventManager snapshot APIs, or claim
gapless event IDs/full-payload equivalence after injected exceptional calls.
Successful uninterrupted vs saved/reloaded equivalent operations still require
full payload/ID equality. Failure tests prove no event/history/state from the
failed call remains and subsequent valid events are unique, not gapless.

## C — historical placements must reload after capability destruction

Additional public runtime repro: ordinary maintenance destroys an ordinarily
placed capability, preserves its placement as Task19a requires, completes/saves,
but reload fails because spatial loaded-state validation requires every subject
live. Retain Task19a lifecycle history; never cascade-delete spatial records or
change entity/maintenance ownership. Schema/model/data representation unchanged.

Allow destroyed existing entities ONLY during SpatialManager.validate_loaded_state
record validation, for both placement subject and containing parent. Still require
all referenced entities exist and validate typed geometry, parent bounds/containment,
acyclicity, area/structure restrictions, mutual sibling overlap and children.
Mutation place/replace stays live-only for subject AND containing parent; no new
placement into a destroyed container. Existing explicit leaf-first unplace/remove
behavior is unchanged. This is a narrow internal validation-mode distinction,
not a new public placement API or permission to create destroyed placements.

TDD public maintenance destruction ->save/reload exactworld/history/placement
preservation; live child in retained destroyed container also reloads; place/replace
on destroyed subjects or into destroyed parents still reject/read-only; missing
entities/invalid geometry/containment/overlap/cycles still reject. Legacy schema
field gates/compatibility unchanged. Clarify ADR0016 historical-load versus live
mutation semantics consistent with Task19a, don't rewrite historical task reports.

## D — reject an existing ancestor cycle without hanging

Corrupt snapshot Leaf->Child->Root->Child causes _reject_cycle to loop forever
when validating Leaf first. Extend its pure ancestor traversal with a visited set:
reject if ancestor is candidateentity OR alreadyvisited; otherwise add ancestor
before following its containing parent. Keep safe existing cycle error and all
normal placement ordering/semantics. No traversal mutation/cascade/schema changes.

Regression: save manager-created 3level hierarchy, corrupt parent linkage/roworder,
reload in a bounded child process (always timeout/kill/reap on RED) and assert
prompt RepositoryLoadError after fix, not timeout. Test valid deep ancestry and
self/candidate cycles as well. Missing references remain their existing errors.

Expand exact allowed files BEFORE edits solely to src/living_world/spatial/manager.py,
tests/test_spatial_domain.py,tests/test_consumption_maintenance.py,
tests/test_sqlite_repository.py,docs/adr/ADR-0016-canonical-two-dimensional-spatial-contract.md.
These join existing A/B wave; no separate workers or overlapping writers. Root
independent amendment review precedes C/D source edits. No other lifecycle/domain
changes; all4findings require independent code review and current rootgates.
