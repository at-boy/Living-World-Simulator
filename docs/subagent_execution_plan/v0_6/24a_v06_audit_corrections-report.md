# Task 24a implementation report

Status: bounded four-finding implementation ready for independent review after
focused verification below. Root owns final disposition, full source/merged
validation, canonical matrix, integration, release gates and paused Task 24 resume.
No VCS operations, agents, full `make`, examples or wheel runs were performed by
this worker. The paused `.worktrees/task24` was untouched.

## Scope and decisions

Read AGENTS, the exact Task 24a plan/prompt, committed October 17 audit report,
development rules and directly relevant runtime/tests/docs. C/D source edits
waited for root's independent amendment-review approval. Runtime edits are only
`cognition/information_boundary.py`, `work/manager.py`, `spatial/manager.py`.
Tests and documentation stay inside the final amended allowlist. No schema,
model, public signature, canonical rule, scheduler, entity destruction ownership,
replay vocabulary or gateway redesign.

## Executed reproductions and corrections

A: Public entity creation and GoalManager.create accept non-stage goal
`private_mandate` and objective `secret_target`. GoalManager.npc_interpretation
supplies selected text to NPCContextAssembler. Separately tested both IDs,
objective completion/failure thresholds 987/988, goal completion/failure
thresholds 989/991 and deadlines 997/998. Each token crossed both assembled
context and direct visible-conversation validation before the fix. No stage,
need or entity attribute supplied these numbers. The final boundary now includes
all four goal/objective definition/state maps in identifier checks and the
existing recursive typed numeric walker. State evidence numbers are also
covered. Safe selected qualitative prose passes; validation leaves state intact.
No goal restrictions or automatic cognitive exposure were introduced.

B: Public work creation with a prerequisite creates two orders. One ordinary
engine.step completes the first and releases reservation 000001; public
mark_ready readies its successor. Both public manager assignment and the normal
volunteer gateway then overwrote the first reservation before the fix. No raw
WorldState mutations are used in this reproduction. Candidate selection now
purely takes the maximum of the local cache and authoritative numeric highwater;
success advances the cache from the allocated suffix. Tests preserve terminal
history, allocate 000002 then 000003, validate loaded work, round-trip SQLite and
compare complete live/resumed worlds for equivalent successful operations.
Failure injection after reservation insertion, at either event recording call,
restores world/history/events and the stale local cache; retry selects 000002
with valid unique events and equivalent semantic payloads.

C: Public maintenance on an ordinarily placed capability with unavailable upkeep
resources destroys it at tick 0 during engine.step and preserves placement.
Saving succeeds but loading rejected the destroyed subject before the fix.
Both a lone destroyed capability and one retaining a live child reproduced it.
Loaded validation now permits existing destroyed subjects/parents through a
private validation mode while retaining every structural check. Place/replace
continue to reject destroyed subjects or containers atomically. Tests reject
missing subjects/parents, invalid geometry, out-of-bounds children, sibling
overlap, invalid area/structure containment and cycles; a 24-level historical
hierarchy round-trips without mutation. History and complete world state are
preserved across maintenance save/reload.

D: Save a manager-created root/child/leaf hierarchy, corrupt snapshot JSON so the
first leaf leads to Child -> Root -> Child, then load in a child process. Before
the fix the load hit the three-second timeout; subprocess.run killed and reaped
the child. Self and candidate cycles already rejected. The ancestor walk now
tracks visited ancestors and uses the existing cycle error on repetition.
All three corrupt cases promptly produce RepositoryLoadError after the fix;
normal ordering, pure traversal and schema compatibility are unchanged.

## Validation evidence

All commands ran from `.worktrees/task24a`, using dependency-only `.venv`,
Python 3.13.5 and source imports. Existing project support remains Python >=3.11.
Successful output is summarized, not copied.

- A/B RED: `PYTHONPATH=src .venv/bin/pytest -q tests/test_npc_information_boundary.py tests/test_work_execution.py -k 'nonstage or live_assignment_after_shadow or highwater_assignment_failure' --tb=short` — 19 failed, 1 passed, 38 deselected. Failures were 16 independently tested leaked tokens/pathways, overwritten reservation history through both manager and volunteer, and stale retry reservation ID. Qualitative selection passed. Earlier fixture-development runs exposed missing authorized-action categories and inability to deepcopy immutable event mapping proxies; fixtures were corrected before this behavioral RED run.
- Same A/B selection after source fixes — 20 passed, 38 deselected.
- A/B plus existing NPC/work/replay/canonical tests: `PYTHONPATH=src .venv/bin/pytest -q tests/test_npc_information_boundary.py tests/test_npc_context.py tests/test_work_orders.py tests/test_work_execution.py tests/test_work_action_gateway.py tests/test_recorded_proposal_tapes.py tests/test_canonical_founders.py` — 379 passed, 10 existing skips.
- C/D RED: `PYTHONPATH=src .venv/bin/pytest -q tests/test_consumption_maintenance.py tests/test_spatial_domain.py -k 'maintenance_destroyed_placement or containment_cycles_without' --tb=short` — 3 failed, 2 passed, 50 deselected; failures were the two maintenance reloads and bounded ancestor-cycle timeout.
- Same C/D selection after source fixes — 5 passed, 50 deselected.
- C/D with additional mutation/integrity/deep-history coverage: `PYTHONPATH=src .venv/bin/pytest -q tests/test_spatial_domain.py tests/test_consumption_maintenance.py --tb=short` — 67 passed.
- Changed runtime/test files only: `.venv/bin/ruff check --fix src/living_world/cognition/information_boundary.py src/living_world/work/manager.py src/living_world/spatial/manager.py tests/test_npc_information_boundary.py tests/test_work_execution.py tests/test_consumption_maintenance.py tests/test_spatial_domain.py` — passed after one import-order correction; final invocation no fixes needed.
- Same seven files: `.venv/bin/black ...` — formatting applied; final read-only format check recorded below.

- Final combined focused command: `PYTHONPATH=src .venv/bin/pytest -q tests/test_npc_information_boundary.py tests/test_npc_context.py tests/test_work_orders.py tests/test_work_execution.py tests/test_work_action_gateway.py tests/test_recorded_proposal_tapes.py tests/test_canonical_founders.py tests/test_spatial_domain.py tests/test_consumption_maintenance.py tests/test_sqlite_repository.py` — 535 passed, 10 existing skips in 18.37s, including the later second-event rollback parameter.
- Final `.venv/bin/ruff check` on the same seven changed runtime/test files — passed, no findings.
- Final `.venv/bin/black --check` on those seven files — passed; 7 files unchanged.
- Python whitespace scan of all 14 worker-edited files — passed: no trailing whitespace and exactly one final newline. Root owns `git diff --check`; worker performed no VCS commands.

## Limits and handoff

The separate EventManager private allocator may retain gaps after exceptional
recording calls; this is existing accepted behavior, not a new rewind API or a
claim of gapless retry IDs. After failure, tests compare event semantics and
unique IDs; successful uninterrupted/resumed operations compare full worlds.
Historical-load allowance does not authorize new placements on destroyed
subjects/containers. Existing model constructors/deserializers continue to own
typed-record construction; legacy schema field gates remain unchanged.

These repairs are evidence for the four scoped findings, not a comprehensive
release-readiness claim. Independent review and root current task full gates passed as recorded below;
merged gates and Task24 release closeout remain required. No main/tag/publication/v0.7 actions were performed.


## Root authoritative task gates

Independent code review: all4findings ADDRESSED, spec/qualityPASS, NO SUBSTANTIVE
FINDINGS. Root make: PASS1416tests/10existing deliberate skips,76Chrome cases,
examples001–039. Separate make examples and git diff --check: PASS. Blackleft207
files unchanged. Root public canonical CLI matrix: success10/stall5/failure13,
twofresh/resume1/3/4 exactschema12payloads and terminalzero-step resumes; allthree
hashes equal reviewed Task23 candidates. No rules/assets/schema changes.
Wholeaudit targetedremainingcoverage completed withnoadditionalfindings; all4
sourcefindings now scopedreviewPASS. Root mergedgates/metadatareadiness remain
separate. No main/tag/publication. Task24metadata preserved in exactownedstash
and filebackup pending correctionintegration; no changesdiscarded.


## Root merged-tree gates

Deliverycfa50b6 merged without conflicts. Merged make1416passed/10existing skips,
76Chrome and examples001–039; separateexamples/whitespace and publiccanonical
fresh/resume matrix passed. Mergedsource/tests identicalrevieweddelivery; no
schema/assets/rule changes. All4auditfindings resolved; wholeauditremaining
coverage completed. Task24metadata/docs must now be restored onto this corrected
base, reviewed and given finalrelease/installed/minimumPythongates. No main/tag.
