# Whole-v0.6 independent review — interrupted at usage checkpoint

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
