# Continuation brief — November 1 usage pause

## Current state

The owner resumed approved live-NPC-runtime execution. This session completed and
pushed three task integrations on `codex/live-npc-runtime`:

| Task | Delivery | Feature integration | State |
| --- | --- | --- | --- |
| LN09f1 bounded trace reader | 9c65f3b | 03bced6 | Complete |
| LN09f2 protected trace API / offline factory | ac09081 | f6a0493 | Complete |
| LN09f3 offline analyze command | 78d7a56 | b823f2f | Complete |

All task branches and worktrees are preserved and clean. The active feature
worktree is `.worktrees/live-npc-runtime`; the primary checkout remains on main.
The final handoff-only checkpoint follows b823f2f. No merge is pending.
Only the owner edit listed below remains uncommitted. Do not redispatch completed
implementation or repeat completed gates without a change or concrete concern.

Current reviewed source/tests/pyproject SHA256 (295 files):
`51e885acc211fec3de69ef5aaf6e9456ed7ab7d1eb8870d11a9598d5719e93ba`.

## Completed behavior and validation

The reader provides stable sealed-prefix call pages and verified selected body
bytes without loading worlds or all BLOBs. It supports normal rollback journals;
WAL/SHM and unsafe paths reject before SQLite opens. Genuine scalar PRAGMA queries
avoid oversized/shadowed schema transfers. Full runtime validation is unchanged.
Integrity labels cover local trace metadata and selected bytes, never complete
worlds, checkpoints, parent seals or unselected body content.

The same authenticated router mounts in the live operator and an inert offline
FastAPI factory. Bounded shallow catalog discovery retains invalid/missing rows.
Malformed projected Unicode invalidates only its row; full JSON response encoding
is inside sanitized error handling. Exact binary downloads, bounded text previews,
Origin checks and no-store apply. No routes expose raw traces to ordinary inspection
or NPC contexts. LN09f2 had one P2 resolved in two original-worker/reviewer rounds.

`living-world analyze --archive-root PATH --admin-token-file PATH --port 0` serves
this read-only API on loopback without a simulation owner, world, preflight, lease,
provider or new attempt. It currently announces an authenticated JSON status URL;
there is no new trace browser page yet. Existing run/serve/inspect behavior remains.
Credential custody was extracted exactly, with legacy aliases; independent AST
comparison confirmed equivalence and unchanged run_served lifecycle.
See [usage](../trace_analysis.md) and the reviewed
[LN09f3 report](../subagent_execution_plan/live_npc_runtime/09f3_offline_analysis_cli-report.md).

Final task make: 2,736 passed / 10 existing deliberate skips, 485.37 seconds.
Final merged make: 2,736 passed / 10 existing deliberate skips, 482.99 seconds.
Both include actual Chrome and 39 examples; separate examples39 and whitespace pass.
Both exact canonical26/read-only/prior-hash, CLI7, sourceServe4, wheel11+Serve4,
41 normal attempts and saved-native reader9archives/30localcalls checks pass.
Both installed-wheel offline API8requests and analyze CLI16requests/two processes,
real SIGINT/SIGTERM exit0, credential removal and unchanged source bytes/mtimes pass.
No new model calls. Reviewed source remained identical. All gate jobs exited0.
LN09f3 review: spec PASS, quality PASS, no findings; focused114, no warnings.
Earlier LN09f2 task/merged2691 and LN09f1 task/merged2651 gates also passed.

Evidence is in W (defined below): `ln09f3-task-*` / session7042 and
`ln09f3-merged-*` / session99190. These sessions are complete. Reviewed task reports,
merge commits and this brief are compressed history; do not reconstruct old tasks.

## Remaining goals and next resume

Pause now with about22% of the five-hour allowance remaining, leaving review and
validation headroom before the owner's10% floor. No reset was used. Resume only
on the owner's request; no automatic continuation. No task9f4 is active.

Next root checks current usage/Git/owner patch, then writes exact task and saved
prompt before new implementation. Remaining work:

1. Browser trace UI shared by live/offline analysis: calls, backend/model, exact
   request/response previews/downloads, original timings, pending/legacy/incomplete/
   reused distinctions, stable paging and safe text rendering. W/trace-analysis-browser-seams.md
   contains concrete field names and browser/package test requirements.
2. Explicit historical world inspection inside the inert analysis instance, using
   existing RevisionSource/inspection routes. Existing inspect--attempt and live
   historical views already work. Never load or certify worlds as a trace-list side effect.
3. Forensic/portable export, including truthful incomplete-attempt evidence and sealed
   ancestry. W/trace-export-seams.md and trace-analysis-next-contract-notes.md retain
   earlier investigations. No export implementation or final contract is active.
4. Isolated versioned llama.cpp argument-contract fix and full both-provider acceptance.
   W/llama-argument-compatibility-seams.md proposes provider-selector vs driver-format
   alternatives; root has not selected or activated one. Preserve old request bytes,
   fingerprints and sealed source-selected replay. Never coerce output or weaken gateways.

## Native evidence and authority

LN09e delivery62ea35c / integration90ef1e2 and native evidence0fc88f9 remain complete.
The [native probe report](live_npc_native_trace_probe_2026_10_27.md) records20 actual
calls,9 archives and8 compared replay points across Ollama and llama.cpp. Exact
traces, cold initial world/cursors and provider-offline replay passed. Ollama had
one accepted work proposal; all12 non-null llama proposals had nonempty arguments
and were correctly rejected. These diagnostics are not full LN09 acceptance.
No new native calls this session; previous owned model servers were stopped.
Future GPU/model/backend/context profiles remain backlog only.

Managers mutate, systems own behavior, events are immutable. RuntimeService is the
sole world writer; filtered LLM outputs remain proposals through action gateways.
Simulation owns truth, goals and stages. Raw state/IDs/hidden cognition and privileged
trace bodies never enter NPC context. Offline analysis has no runtime owner.

## Recovery and preserved work

W = `.superpowers/sdd/2026-10-19-live-npc-runtime` in the feature worktree.
`progress.md` is the recovery ledger; reviews, snapshots, hashes, native archives,
helper outputs and `2026-11-01-final-checkpoint.json` are retained there.
`run_reader_gates.py --analysis-api --analysis-cli` runs current root gates with
unique output prefixes; separate examples run only after make exits.
Use `.worktrees/task24/.venv` (Python3.13.5), support Python>=3.11. Actual Chrome/
loopback gates require escalation. SSH workaround:
`GIT_SSH_COMMAND='ssh -F /dev/null -o BatchMode=yes'`.

Never stage, restore or fix the owner edit in
`docs/superpowers/plans/2026-10-19-live-npc-runtime.md`
(`observasmall, clearly specified tasksble`). Patch SHA256:
`294b20313ae2de248301fa20bbb4f9c312d51efa4851a434466f98a588dd93e6`.
All branches, worktrees and archives remain preserved. No main/milestone/tag work
is authorized now. Remote refs verified unchanged at checkpoint:
main d8ea51797b5ca3bfefa37cd5f7bafc95cbee5899;
milestone/v0.6 6bf4c63637584584a8dfce009d2d1d79987be570;
v0.6.0rc1 tag1040fd2e3e4068d3f7dba77be37179299273aa41,
peeled092715c11ed00b98255ae611fcef1bcfb8f1de9d.
