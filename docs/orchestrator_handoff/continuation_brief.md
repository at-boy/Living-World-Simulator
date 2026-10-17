# Continuation brief — v0.6.0rc1 ready, October 17, 2026

## Current completion and authority

Task 24 delivery `a5c275f`, integrated as `badd5f9`, completes the reviewed `0.6.0rc1`
candidate on `milestone/v0.6`. Root task and merged gates each passed 1,416 tests / 10
existing deliberate skips, 76 Chrome cases and examples 001–039. Separate examples and
whitespace checks passed. Source and installed Python 3.13.5 / 3.11.2 canonical runs
preserve identical complete schema-12 payloads across fresh runs and resume ticks 1, 3
and 4. Wheel, exports, eight assets, health, read-only APIs, actual console/loopback
inspection and all-outcome browser checks passed.

All 21 authorized tasks, including correction Task 24a and closeout Task 24,
are reviewed, validated and integrated. The milestone and delivery branches are
pushed; root verifies live refs after the final documentation checkpoint.
Main remains `12f2f173796500f73f003c520c0ac848b9e1e9c8`.
No merge to main, tag, publication, v0.7 or live infrastructure is authorized.
The only primary local edit is the user-owned `.codex/config.toml`; preserve it.
Owner's next action is separate review/integration/release authorization.
There is no remaining authorized implementation task to redispatch.

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
