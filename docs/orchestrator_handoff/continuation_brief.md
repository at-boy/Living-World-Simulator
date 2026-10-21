# Continuation brief — live runtime resumed at LN03, October 21, 2026

## Current design scope and authority

Owner approved the written live NPC runtime design and explicitly requested its
commit/push followed by the implementation plan. Design96262fa is pushed to origin.
Active branch codex/live-npc-runtime is isolated in .worktrees/live-npc-runtime,
based on main d8ea517. Read the
[approved design](../superpowers/specs/2026-10-19-live-npc-runtime-design.md) and
[implementation plan](../superpowers/plans/2026-10-19-live-npc-runtime.md).

Owner approved the plan and execution. LN01 shared world codec has independent
SPEC/QUALITY PASS and root task gates1452passed/10existing skips,39examples.
Delivery5f64056 is pushed; merged gates repeat the same results and exact
recorded CLI hashes. The integration commit containing the LN01 report completes it.
LN01 integration is b105d57. LN02 delivery099da9a is pushed and integrated by the
merge containing this checkpoint. Independent SPEC/QUALITY PASS after two corrected
findings; task and merged make each1503/10,39examples, separate examples/whitespace
and exact recorded CLI matrices passed. See
[LN02 report](../subagent_execution_plan/live_npc_runtime/02_archive_store-report.md).

Owner resumed October21 with99%five-hourremaining. Feature0d04c1b and preserved
main/milestone/tag verified live. LN03 deliverye3d9faf is pushed and integrated by the merge containing its report.
Independent review and task/merged gates1551/10,39examples, separateexamples/
whitespace andexact recorded CLI checks passed. Consult03report for evidence.
LN03 integration5544fdb is complete. LN04 safe-controller contract is prepared;
implementation/review/gates pending. Read04contract/prompt for explicit producer/
protocol amendments. LN05–LN09 remain authorized and unstarted. Read current03contract for archive layout, inputs, lease,
parent continuity and explicit mirror source context. Do not repeat LN01/LN02.
Preserve all branches/checkouts and current-plan ignored SDD ledger/evidence under
.worktrees/live-npc-runtime/.superpowers/sdd/2026-10-19-live-npc-runtime. Owner-local
master-plan edit matches saved owner-plan-local-edit.patch and stays uncommitted.
Stop with buffer BEFORE five-hourremaining drops below10%; no resets authorized.

Recommended method: bounded sequential workers, independent per-task reviews,
root-owned integration and final whole-branch review. LN01–LN09 specify exact
interfaces/files/tests; materialize task plan/saved-prompt/report before dispatch.
Explicit owner clarification: pause durably, shut down, restart later and continue
the same world including NPC memories/work/driver progress. New process invocation
gets a linked archive attempt; it must not restart simulation state or advance time
while off. Recorded modes remain supported and archives retain unsuccessful runs.

Current scope: local Ollama decisions, player-disruption readiness, browser controls
and all normal-run archives. No demographic/governance milestone, player interface,
main integration/tag movement or remote admin deployment. Main d8ea517,
milestone/v0.6 6bf4c63 and v0.6.0rc1 092715c remain unchanged. The prior release
handoff below is historical context; live functionality is not already implemented.

## Completed release context

Task 24 delivery `a5c275f`, integrated as `badd5f9`, completes the reviewed `0.6.0rc1`
candidate on `milestone/v0.6`. Root task and merged gates each passed 1,416 tests / 10
existing deliberate skips, 76 Chrome cases and examples 001–039. Separate examples and
whitespace checks passed. Source and installed Python 3.13.5 / 3.11.2 canonical runs
preserve identical complete schema-12 payloads across fresh runs and resume ticks 1, 3
and 4. Wheel, exports, eight assets, health, read-only APIs, actual console/loopback
inspection and all-outcome browser checks passed.

All 21 authorized tasks, including correction Task 24a and closeout Task 24,
are reviewed, validated and integrated. The milestone and delivery branches are
pushed; October17 closeout refs were verified, and October19 release refs are
recorded below.
Owner separately authorized main integration/tagging on October19 and explicitly
approved pushing main/tag to origin. Merge092715c contains the exact reviewed
milestone tree; annotated v0.6.0rc1 points to it and both were pushed atomically.
Milestone/v0.6 remains6bf4c63637584584a8dfce009d2d1d79987be570 locally/remotely.
Fresh merged gates passed1416tests/10existing skips,76Chrome/examples001–039;
separate examples/whitespace and all three exact fresh/resume matrices passed.
No package publication, hosted release or v0.7 implementation was requested.

Owner also authorized cleanup of the local agent configuration edit. Main's
focused followup uses agents/name.toml relative to .codex/config.toml; this keeps
the exact role files selected by the owner's previous ../.codex workaround.
The exact original edit is backed up in ignored SDD evidence before primary
checkout transition to corrected main. Preserve milestone/task branches and
worktrees. See the [maintenance report](../subagent_execution_plan/maintenance/agent_config_paths-report.md)
for final validation and cleanup evidence. No remaining authorized release-cleanup work.

## Canonical evidence

- [Task 24 closeout report](../subagent_execution_plan/v0_6/24_v06_release_closeout-report.md): final requirement mapping, review, root gates and limitations.
- [Release notes](../releases/v0_6_0rc1.md): supported commands and delivered behavior.
- [Milestone artifact index](../subagent_execution_plan/README.md#v06-authorized-milestone): all plans, saved prompts and reports.
- [Whole-milestone audit](v0_6_release_audit_2026_10_17.md) and [Task 24a report](../subagent_execution_plan/v0_6/24a_v06_audit_corrections-report.md): all four code findings corrected, independently reviewed and validated; remaining targeted coverage found no additional substantive findings.

Task 23 delivery `87af71a` / merge `58b6ba7` established canonical acceptance.
Task 24a delivery `cfa50b6` / merge `c1d93cd` protects actual non-stage goal
secrets, authoritative reservation allocation, destroyed historical placements
on reload, and termination when corrupt ancestor cycles are loaded.
Task 24 candidate prerequisites were merged as `e60262d`.

## Limits and architecture

Managers mutate state, systems own behavior and events remain immutable.
NPCs receive filtered cognition and submit untrusted action proposals. Inspector
DTOs and raw world state never become NPC context. Schema 12 writes and schemas
1–12 load remain supported. Recorded tapes prove deterministic unattended engine
execution, not successful live-model strategy selection. The founders recipe is
fixed; generic authoring, legacy replay without labels, stage templates/demotion
and automatic stage perception remain deferred. Inspector is a privileged GET-only
fixed snapshot; a separate running simulation does not refresh it. Dense spatial
labels retain an accessible complete-list fallback. Existing exceptional event-ID
gaps remain accepted; no gapless retry guarantee is claimed.

## Preserved workspace and resumption rules

Durable task worktrees and ignored `.superpowers/sdd/v0_6_completion_plan` review
artifacts, helpers and backups are preserved. Task 24's old owned stash
`29d9f3cf7811a9c8fd53f16f3dda4add5e84e0e1` is a historical backup already applied
and incorporated into delivery `a5c275f`; do not apply it again. Its independent
file backup/SHA manifest remains under `task24-preserved-before-corrections`.
Temporary `/tmp` logs/installations may disappear; committed reports are canonical.
The dependency environment is `.worktrees/task24/.venv`; primary validation uses
`make VENV=.worktrees/task24/.venv`. Git network operations use the scoped
`GIT_SSH_COMMAND='ssh -F /dev/null -o BatchMode=yes'` to bypass the broken system
SSH include without changing user configuration or host verification.

For any later authorized work, inspect current Git state and live refs first.
Stop BEFORE five-hour remaining usage drops below 10%, with a durable checkpoint
and stopped agents. Historical usage pauses do not authorize new scope or resets.
