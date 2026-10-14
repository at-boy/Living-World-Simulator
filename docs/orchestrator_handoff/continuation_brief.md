# Continuation brief — October 14, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Reviewed task branches merge only into `milestone/v0.6`; never change `main`.

At this checkpoint:

- current branch `milestone/v0.6`; Task15 delivery `dea51cb`, merge `91e33bf`;
- Task15 reviewed after four bounded corrections; task and merged gates1229
  passed/10 existing skips,31 Chrome cases,examples001–038; installed assets and
  actual wide/narrow layouts passed;
- Task22 delivery `02b35fe`, merge `7806f29` remains complete;
- Task22 independent spec/quality PASS after Unicode and work-phase compatibility
  corrections; task and merged gates1194 passed/10 existing skips, examples001–038;
- Task21 delivery `c821efe`, merge `1ab288b`, checkpoint `b055619` remains complete;
- live remote tips verified: milestone `91e33bf`, Task15 `dea51cb`, unchanged
  main `12f2f17`;
- user-owned `.codex/config.toml` edit is preserved unstaged;
- writable isolated checkouts are `.worktrees/task21` and `.worktrees/task22`;
  native read-only alternative was archived; no task implementation was lost;
- owner approved remaining execution and chose `0.6.0rc1`; no main integration/tag;
- owner resumed after the historical usage pause; **stop before the five-hour
  allowance falls below10% remaining**, checking at task boundaries and saving a
  durable checkpoint with enough buffer to interrupt workers;
- Task15c is next. Its consolidated geometric/ordering/numeric and final UI
  seam contract has independent CONTRACT READY review; transfer reviewed plan
  and prompt into isolated task branch before implementation.

The historical first pause is retained in `v0_6_usage_pause_2026_10_14.md`; its
Task22 pending state is superseded by this checkpoint and the final task report.
No automatic resume or usage-reset action is configured.

The approved delivery plan is `docs/subagent_execution_plan/v0_6_completion_plan.md`.
Current root scratch recovery ledger and replay draft are under
`.superpowers/sdd/v0_6_completion_plan/`; binding committed task documents remain
canonical. Never depend solely on ignored scratch surviving cleanup.

Always recheck status, current branches, history and live remote tips before
acting. SSH currently requires the scoped invocation
`GIT_SSH_COMMAND='ssh -F /dev/null -o BatchMode=yes'` because a system SSH Include
has invalid ownership; normal host-key checking is retained.

## Completed v0.6 sequence

The following tasks were implemented on pushed task branches, independently
reviewed, corrected where necessary, validated, committed, merged with
`--no-ff`, and pushed to `milestone/v0.6`:

| Task | Result | Milestone merge |
| --- | --- | --- |
| 16 | Versioned YAML scenario/run identity and deterministic initial graph | `808bdde` |
| 16a | Bounded/continuous runner, checkpoints, resume, and CLI | `ca5b75c` |
| 15a | Canonical two-dimensional spatial ADR | `a6d77a9` |
| 15b | Spatial domain, schema-v3 persistence, and inspection | `2e43ada` |
| 17 | Partial external-world references and schema-v4 persistence | `c909d8a` |
| 17a | Deterministic dispatch lifecycle, gateway, and schema-v5 persistence | `9c006fc` |
| 18 | Engine-owned goals/objectives, schema-v6 persistence, inspection, and filtered interpretations | `0fe099d` |
| 18a | Deterministic criterion evaluation, lifecycle transitions, and evidence | `033ed60` |
| 15d | NPC-safe qualitative spatial and direct-road perception | `43405ee` |
| 19 | Settlement needs, sustained pressure evaluation, schema-v7 persistence, inspection, and filtered interpretations | `a3f4bc5` |
| 19a | Consumption, storage/spoilage, maintenance consequences, and schema-v8 persistence | `bba7549` |
| 20 | Authoritative work orders, aggregate reservations, schema-v9 persistence, inspection, and filtered interpretations | `bb9fa53` |
| 20a | Actor-bound proposal-to-work gateway, authoritative preflights, and self-volunteering | `0b6760f` |
| 20b | Deterministic work execution, atomic work-phase rollback, and schema-v10 charge evidence | `5489b73` |
| 21 | Objective-backed adjacent stages, population/maintenance criteria, schema-v11 persistence, inspection, and NPC filtering | `1ab288b` |
| 22 | Recorded proposal tapes, durable cursor/labels, schema12, checkpoint recovery and detached replay inspection | `7806f29` |
| 15 | Packaged GET-only inspector, ten views, real browser/error/navigation/read-only and installed asset checks | `91e33bf` |

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0025 capture the scenario, spatial, partial-world, dispatch, goal, need,
work-order, proposal-gateway, and deterministic work execution contracts.

SQLite snapshot support now spans schema versions 1 through 12. The v0.6
progression is run identity in schema 2, spatial placements in schema 3,
external references in schema 4, external dispatches in schema 5, goals and
objectives in schema 6, settlement needs in schema 7, and consequences in
schema 8, followed by work definitions, states, and reservations in schema 9,
exact-once work input charge evidence in schema 10, and objective-backed
settlement stage programs/state plus population/maintenance criteria in schema 11. Legacy versions load
newer fields and collections with compatible defaults and write forward.

## Current validation baseline

Task15 independent spec/quality PASS after reservation/criterion validation,
maintenance references and narrow-table corrections. Root task and merged gates:

| Gate | Result |
| --- | --- |
| `make VENV=.worktrees/task15/.venv` (merged) | Ruff/Black PASS;1229 passed,10 existing deliberate skips;examples001–038 |
| Separate examples | PASS;001–038 |
| Actual Chrome browser cases in full suite |31 passed,no skips |
| Whitespace | PASS |
| Isolated wheel/install/resource/route check | PASS;3 byte-identical assets,3 routes,404/405/health,state unchanged |
| Actual wide/narrow visual inspection | PASS after reviewed correction |

Wheel smoke's optional TestClient/httpx emitted a Starlette deprecation warning;
project tests use dependency-free ASGI transport and had no warnings. Current
version remains0.5.0 until0.6.0rc1 Task24. Dependencies-only Python3.13.5 venv
requires PYTHONPATH=src for direct project imports; make already sets it.

## Next task: Task15c

Reviewed drafts in `.superpowers/sdd/v0_6_completion_plan/`:
`task15c-final-plan-draft.md` and `task15c-prompt-draft.md`. Transfer them to
binding task artifacts on task/15c-spatial-inspector-view from this milestone
checkpoint before dispatch. Independent final contract/seam verdict CONTRACT READY.
Exact projection, safe integer range, backend order, unplaced categories and
compatible Back-to-Spatial behavior are explicit. Dedicated renderer preserves
placement order; generic renderRecords sorts by ID and is unsuitable for maps.
No domain/DTO/server/persistence/cognition changes or write requests.

Task23 preparation is documented separately in
`v0_6_canonical_preparation_2026_10_14.md`. It is a non-binding design checkpoint,
not worker authorization or a completed contract. Formal23plan/prompt must still
resolve exact interfaces/fixtures/validation before implementation.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Task15c — spatial inspector view.
2. Task 23 — canonical success, stall, and failure founders scenarios.
3. Task 24 — milestone release-readiness closeout at `0.6.0rc1`.

Task 24 leaves `milestone/v0.6` ready for owner integration. It does not merge
or push anything to `main`.

## Branch, review, and delivery rules

- Start each task from the current reviewed milestone head and push the task
  branch immediately.
- Execute or delegate only one documented task at a time.
- Every implementation task requires its existing plan and `-prombt.md`, plus a
  truthful `-report.md` before approval.
- Independently inspect every delivery. Require corrections for behavior,
  strict typing, tests, report accuracy, file-boundary compliance, persistence,
  or NPC-boundary defects.
- Run focused tests while correcting, then `make`, separate `make examples`,
  and `git diff --check` before approval.
- Commit and push only reviewed work, merge with a descriptive `--no-ff` commit
  into `milestone/v0.6`, and push that branch.
- Never commit, merge, or push to `main` during this milestone workflow.

## Non-negotiable architecture

Preserve this authority and information flow:

`WorldState -> perception -> immutable cognitive records -> filtered NPC
context -> cognition proposal -> action gateway -> world event/state change`

NPC-facing input must never contain raw `WorldState`, internal record/entity
IDs, privileged inspection DTOs, unrestricted attributes, another NPC's hidden
cognition, exact hidden criteria/policy, or arbitrary runtime objects. Model
output remains an untrusted proposal until the gateway and domain manager
validate and apply it.

Recent concrete boundaries to preserve:

- exact spatial coordinates and containment are privileged engine truth;
- external references are deliberately partial, not simulated remote places;
- dispatch IDs, costs, delays, reliability, seed calculation, reservations,
  and outcomes are engine-only;
- NPC dispatch proposals choose only engine-authored qualitative labels;
- filtered goal interpretations in Task 18 must hide internal IDs, exact
  criteria, evidence, and authoritative status unless legitimately perceived.
- need definitions, owners, thresholds, quantities, pressure, windows, and
  history are privileged; NPCs receive only selected qualitative need prose;
- Task 19 assessment runs after ordinary systems and before goal evaluation;
  Task 19a consequences must run before assessment and must use manager-owned
  authoritative mutation and immutable events.
- Task 20 reservations are engine-owned aggregate locks, not resource
  deductions or item identities; Task 20 adds no scheduler or execution path.

## Historical context

The v0.5 release and Tasks 01–14/14a/14b are complete and archived under
`docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/`. The prior council and
local-model decisions remain documented in their reports and ADRs; do not
reconstruct them from chat history. The cross-milestone index is
`docs/subagent_execution_plan/README.md`, and the approved v0.6 objective and
sequence are in `docs/subagent_execution_plan/v0_6.md`.
