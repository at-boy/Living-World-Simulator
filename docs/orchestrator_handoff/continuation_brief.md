# Continuation brief — October 13, 2026

## Current repository state

The v0.6 autonomous founding-settlement milestone is authorized and active.
Work uses a pushed milestone branch plus one pushed branch per isolated task.
Reviewed task branches are merged only into `milestone/v0.6`; `main` must not
be changed.

At this handoff checkpoint:

- current branch: `milestone/v0.6`;
- last implementation merge: `1ab288b` (Task 21 settlement development stages);
- Task 21 delivery: `c821efe`, independently reviewed and corrected for strict
  test annotations, root-validated, committed, merged, and pushed;
- live remote tips verified before this documentation checkpoint:
  `milestone/v0.6` at `1ab288b`, Task 21 at `c821efe`, and unchanged `main` at
  `12f2f17`;
- the user-owned `.codex/config.toml` edit remains unstaged and preserved;
- Task 21 recovered into the durable ignored `.worktrees/task21` checkout;
  its missing `/tmp` registration was removed, and the unused read-only native
  alternative was archived through the app;
- the owner approved the completion plan on October 13 and chose `0.6.0rc1`
  for release closeout; no main integration or tagging is authorized;
- Task 22 is next. Expand its plan/prompt using the resolved replay integration
  decisions before code delegation.

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

Task reports under `docs/subagent_execution_plan/v0_6/` contain exact files,
interfaces, review corrections, and validation evidence. ADR-0015 through
ADR-0024 capture the scenario, spatial, partial-world, dispatch, goal, need,
work-order, proposal-gateway, and deterministic work execution contracts.

SQLite snapshot support now spans schema versions 1 through 11. The v0.6
progression is run identity in schema 2, spatial placements in schema 3,
external references in schema 4, external dispatches in schema 5, goals and
objectives in schema 6, settlement needs in schema 7, and consequences in
schema 8, followed by work definitions, states, and reservations in schema 9,
exact-once work input charge evidence in schema 10, and objective-backed
settlement stage programs/state plus population/maintenance criteria in schema 11. Legacy versions load
newer fields and collections with compatible defaults and write forward.

## Current validation baseline

Task 21 passed independent spec/quality review after one typing correction.
Root validation passed on both the task tree and merged milestone:

| Command | Result |
| --- | --- |
| `make` | Ruff/Black passed; 1086 tests passed, 10 existing deliberate skips; examples 001–037 passed |
| Separate `make examples` | Examples 001–037 passed |
| `git diff --check` | Passed |

The primary checkout's old environment lacked Black. Merged validation used
`make VENV=.worktrees/task21/.venv` and the same override for examples; its
fresh environment is Python 3.13.5. These results are checkpoint evidence,
not a substitute for future task validation.

## Next task: Task 22

Task 22 follows the reviewed and pushed Task 21 merge. Its binding artifacts:

- `docs/subagent_execution_plan/v0_6/22_recorded_proposal_tapes.md`
- `docs/subagent_execution_plan/v0_6/22_recorded_proposal_tapes-prombt.md`

Before delegation, consolidate the root's reviewed replay design: persisted
scenario-label bindings; immutable tape identity plus manager-owned durable
cursor in schema 12; one entry per tick after ordinary systems and before work;
filtered context and ordinary action gateways; read-only offer composition;
failed-tick advance/save refusal with checkpoint reload; preparation,
finalization and intermediate-checkpoint CLI semantics. No live model or
canonical founders content belongs in Task 22. Task 23 owns canonical domain
setup and goal/stage-based terminal outcome integration.

## Remaining approved sequence

Continue one reviewed task at a time in this order:

1. Task 22 — deterministic recorded proposal tapes.
2. Tasks 15 and 15c — FastAPI-hosted inspector and spatial view.
3. Task 23 — canonical success, stall, and failure founders scenarios.
4. Task 24 — milestone release-readiness closeout at `0.6.0rc1`.

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
