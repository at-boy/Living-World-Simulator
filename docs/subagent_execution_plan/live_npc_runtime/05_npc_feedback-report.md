# LN05 report — qualitative founder feedback

Status: independent SPEC/QUALITY PASS; root task gates passed. Delivery and merged
evidence follow below. Worker statements below are historical stage evidence;
no live-provider success is claimed. The earlier partial checkpoint is superseded by
the October21 authorized live-validation amendment and resumed evidence below.
Work remains an uncommitted task diff in `.worktrees/live-npc-ln05`.

## Scope and resulting behavior

- Shared `prepare_founders_world` preserves recorded setup statement order and
  replay installation/finalization. Explicit `prepare_live_founders_world`, live
  domain system and live offer provider share the same manager/offer implementation
  while selecting live validation. Recorded callers remain strict.
- Named setup manager live methods use strict atomic fresh initialization, preserve
  canonical static records as required subsets, and run existing full spatial,
  work, need, goal, stage and consequence validation. Extra valid need/goal/objective
  records are accepted; missing/altered canonical records and malformed extras fail.
  Canonical camp/valley placements and liveness remain protected. Bound founders may
  move, become unplaced or be destroyed; structural identity/creation/destruction
  corruption fails closed. Historical fixed-roster shelter attachments remain
  unchanged when a founder is destroyed before or after composition.
- `FoundersLiveComposition` needs no tape, validates retained scenario/definition
  hashes, restores detached worlds byte-exactly, uses scenario-ordered terminal
  callbacks with exact bool validation, and finalizes without replay/domain writes.
- `FoundersFeedback.initialize` communicates initial qualitative observations and
  holder-owned memories. `prepare` works only on matching detached candidates and
  selects living, actually local scenario founders in label order. The allowlisted
  mandate, camp needs and local camp work use typed projections and exact templates;
  private goals, thresholds, target arithmetic, speech and unseen events stay out.
- Closed cursors retain sorted holder/source fingerprints and pending own results.
  Real holder observation/memory provenance, latest-source correspondence and
  temporal checks prevent reset/rewind/replay. After-tick results require staged
  candidate continuity, the exact scheduled roster/base revision/source tick and
  event references from the just-completed tick. Only an eligible actor's own result
  becomes observation on its next decision; absent actors retain pending results.
- Frozen/slotted DecisionInput keeps actor IDs and ordinary gateway handlers
  engine-only. Context assembly injects a local memory-only retriever without
  changing cognition APIs. At most eight current perceptions and eight distinct
  holder memories total include the required core mandate. Optional entries prune
  deterministically oldest first against the injected complete HTTP-body size
  function; invalid size values and required-content overflow fail with safe codes.
- Fingerprints bind exact serialized context/options, base snapshot and semantic
  cursors while excluding checkpoint revision renumbering. Root resolved the driver
  cursor as opaque semantic JSON here: **LN06 must define its closed semantic cursor
  and exclude attempt/request UUIDs, wall time and operational revisions/counts**.
- Safe preparation errors expose fixed codes without unsafe exception messages or
  causes. Candidate cognition is discardable; no world/archive/provider IO occurs
  here. Weak-key caches hold primitive staging/scenario data without retaining engines.

Changed worker paths: new `runtime/founders.py`, `runtime/feedback.py`,
`tests/test_runtime_founders_feedback.py`; existing `founders/runtime.py`,
`founders/setup.py`, `founders/__init__.py`, `docs/npc_information_boundary.md`, and
this report. Root-owned task/prompt amendments were preserved. No cognition,
runtime exports, archive schema, provider, driver, CLI, browser or dependency edits.

## Validation evidence

All pytest commands used `PYTHONPATH=src` and
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
Successful command output is intentionally not reproduced.

Historical checkpoint evidence:

- Unchanged baseline: `-m pytest tests/test_runtime_recorded.py tests/test_npc_context.py tests/test_npc_cognition_client.py -q`: **67 passed**, 5.56s.
- Initial RED: `-m pytest tests/test_runtime_founders_feedback.py -q`: **2 failed**,
  genuinely absent required runtime modules. Intermediate fixture errors (unknown
  archive mode, omitted explicit tape argument, guessed seed) were corrected to real
  retained `ollama` inputs with loader-derived scenario identity and `tape_path=None`.
- Initial GREEN: **2 passed**; checkpoint feedback+recorded suites: **11 passed**.
- Historical scoped Ruff failed eight findings; all are now resolved.

Resumed focused RED/GREEN evidence:

- `-m pytest tests/test_runtime_founders_feedback.py -k live_dynamic -q --tb=short`:
  **4 failed** at strict restore after corrected manager-owned fixtures; live
  relocation/unplacement/destruction then passed. Malformed identity exposed existing
  ScheduleSystem rejection; root explicitly corrected the task to structural failure
  closed. Separate corruption coverage now verifies that ruling.
- `-k 'actor_result or cursor_requires or old_event'`: **5 failed, 2 passed**.
  Three were overly broad handler-object equality assertions, corrected to compare
  context/fingerprints; two genuine missing checks were future pending results and
  historical event references. Relevant focused corrections reached **12 passed**.
- `-k 'cannot_drop or local_need_a or historical_shelter'`: **3 failed, 1 passed**.
  Genuine missing cursor-drop rejection was fixed. Shelter fixture was corrected to
  create through managers in the post-composition phase, matching ordinary lifecycle
  ordering; before/after destruction cases then passed.
- `-k invalid_founder_destruction`: **3 failed** for boolean, negative and future
  ticks; live-only structural validation correction yielded **3 passed**.
- Broader selected suites progressed through **377 passed**, then **380 passed**.
  A final explicit real-provider offer regression verifies cancellation/replacement
  refreshes target labels rather than merely asserting nonempty offers.
- Final current-tree command:
  `-m pytest tests/test_runtime_founders_feedback.py tests/test_npc_context.py tests/test_npc_cognition_client.py tests/test_npc_information_boundary.py tests/test_npc_perception_boundary.py tests/test_canonical_founders.py tests/test_recorded_proposal_tapes.py tests/test_runtime_recorded.py tests/test_runtime_controller.py -q`:
  **381 passed**, 30.82s; no skips or warnings. This includes **63 new LN05 cases**,
  unchanged recorded exact digest/payload/event pins and existing replay/controller
  behavior. Existing assertions were not weakened.
- Scoped `-m ruff check` on all six changed Python files: **passed**.
- Scoped `-m black --check` on those files: **passed**, six unchanged.
- Explicit changed-file whitespace/EOF scan: **passed**, eight worker files.

Full pytest, `make`, `make examples`, VCS diff checks, independent review and
integration were deliberately left to root under the worker contract.

## Self-review and limits

Reviewed the shared strict/live manager path for mutation ownership and recorded
order, required canonical subsets, protected camp/valley facts, actual containment,
identity/lifecycle checks and fixed historical attachment semantics. Reviewed source
selection, exact prose, salience/provenance, current/history separation, pending
result isolation/consumption, cursor corruption checks, candidate continuity, budget
selection and actor/handler serialization boundaries. Tests cover reconstruction,
revision-renumbered child identity, A->B->A changes, source disappearance, corruption,
private/unseen information, complete-body size injection, work replacement, context
bounds and discarded-candidate collection.

No unresolved worker architectural question remains. Root's independent review may
identify corrections; this report does not approve itself. LN06 still owns actual
provider encoding/enforcement, broker isolation, semantic driver cursor production,
proposal installation and atomic DriverCommit integration. No live model inference
or successful autonomous strategy has been exercised by LN05.

## Root independent review and task validation

Independent /root/ln05_review returned **SPEC PASS / QUALITY PASS**,
**NO SUBSTANTIVE FINDINGS**. Named outside-diff checks covered setup shadow copies,
historical attachments, shared offers, assembler/retriever injection, journal type
validation and detached restoration. No review fix round or parked finding. Root
accepted the task contract, scope and review disposition.

Final task tree, dependency-only Python3.13.5 with PYTHONPATH=src:

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: **1652 passed / 10 existing deliberate skips**, actual Chrome, lint/format and **39 examples**; no new warnings.
- Public CLI canonical matrix: all three pinned schema12 payload hashes, two fresh
  runs per outcome, full row equality on resume1/3/4 and success/failure terminal
  zero-step passed. Outcomes remain success10/stall5/failure13.

Evidence ln05-review-1.diff, ln05-review-final.md, ln05-task-make.log and
ln05-task-matrix/results.json in ignored current-plan SDD evidence. Separate
examples/whitespace and delivery/merged gates follow below. LN05 does not implement
provider calls or public control entrypoints; those remain later approved tasks.

Separate task `make examples`: **39 passed**. Final staged/unstaged whitespace
passed. Evidence ln05-task-examples.log.
