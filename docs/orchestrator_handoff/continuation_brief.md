# Continuation brief — October 14, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Reviewed task branches merge only into `milestone/v0.6`; never change `main`.

At this checkpoint:

- current branch `milestone/v0.6`; Task22 delivery `02b35fe`, merge `7806f29`;
- Task22 independent spec/quality PASS after Unicode and work-phase compatibility
  corrections; task and merged gates1194 passed/10 existing skips, examples001–038;
- Task21 delivery `c821efe`, merge `1ab288b`, checkpoint `b055619` remains complete;
- live remote tips verified: milestone `7806f29`, Task22 `02b35fe`, unchanged
  main `12f2f17`;
- user-owned `.codex/config.toml` edit is preserved unstaged;
- writable isolated checkouts are `.worktrees/task21` and `.worktrees/task22`;
  native read-only alternative was archived; no task implementation was lost;
- owner approved remaining execution and chose `0.6.0rc1`; no main integration/tag;
- owner resumed after the historical usage pause; **stop before the five-hour
  allowance falls below10% remaining**, checking at task boundaries and saving a
  durable checkpoint with enough buffer to interrupt workers;
- Task15 is next. Its consolidated contract has independent CONTRACT READY
  review; transfer the reviewed draft and saved prompt into its new task branch
  before implementation. Task15c follows its reviewed merge.

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

Task22 independent spec/quality review passed after two scoped corrections.
Root task and merged milestone validation:

| Command | Result |
| --- | --- |
| `make` | Ruff/Black PASS;1194 tests passed,10 existing deliberate skips; examples001–038 passed |
| Separate `make examples` | Examples001–038 passed |
| `git diff --check` | PASS |

Merged gates use `VENV=.worktrees/task22/.venv`, Python3.13.5, dependencies-only
with make's PYTHONPATH=src. The old primary venv lacks Black. These results are
checkpoint evidence, not future-task verification. Schema12 adds immutable
replay binding/cursor and persisted initial label mappings; complete-boundary
cursor/resolution-event bijection is validated. Legacy1–11 defaults remain
compatible; missing legacy label bindings are never guessed for replay.

## Next task: Task15

Copy independently reviewed `.superpowers/sdd/v0_6_completion_plan/`
`task15-final-plan-draft.md` and `task15-prompt-draft.md` into binding Task15
artifacts on `task/15-world-inspector-ui` from this reviewed milestone head.
Review decision-completeness if drafts are unavailable; never reconstruct
implementation from historical chats. Exact UI scope is packaged same-origin
GET-only inspector views, strict response/error/race handling, accessible
navigation and actual Chrome/Playwright tests. No spatial view in15, no Node
build, no inspector DTO/domain/cognition changes. Root owns full/browsers/wheel
gates; worker focused checks and reviewer independent diff inspection.

Task23 owns canonical domain setup, deterministic engine-owned goal/stage
terminal policy and saved-world inspection CLI. Narrow probe confirms existing
production/work paths suffice; ordinary registered composition accepts explicit
housing delay rather than adding a new scheduler phase. Formal23contract still
requires exact decisions before dispatch. No Task23 implementation is ready.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Tasks 15 and 15c — FastAPI-hosted inspector and spatial view.
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
