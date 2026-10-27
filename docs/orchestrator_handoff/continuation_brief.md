# Continuation brief — LN09f1 corrected task validated, usage pause

## Current state and next task

Feature source remains af7b4af on codex/live-npc-runtime; this handoff-only checkpoint
extends it. Only owner master-plan edit remains uncommitted there.
Task checkout .worktrees/live-npc-ln09f1 / codex/live-npc-ln09f1-trace-reader,
Corrected delivery9c65f3b committed/pushed; taskcheckout clean. Exact task/prombt amended before each fix.
Initial independent review found two P1s: WAL sidecar source writes and oversized
DESC-PK identity prefetch. Fixround1 resolved both. Root then reproduced unbounded
schema-name/type prefetch (R3); fixround2 scalar queries left a shadow-table bypass.
Original worker fixround3 explicitly invokes PRAGMA functions and returns intrinsic
scalar flags; original independent astra spec/quality review PASS, cumulative three
findings addressed, zero open. Focused104PASS, reviewer targeted14PASS.
Four allowed worker paths preserved; full runtime validator/schema/writers unchanged.

Current reviewed source/tests/pyproject SHA256:
7eeb0344e913514b49b596dcc532ab5bbfcff7cc0bdd4cd77f335d7c4d716989.
Fresh task gates session10879 COMPLETE, prefix ln09f1-fix3-task:
make2651passed/10existing deliberate skips481.84s, actualChrome/39examples;
separateexamples39, whitespace and reviewedsource equality PASS. Exactcanonical26/
read-only unchanged/priorhashes/CLI7/sourceServe4/wheel11+actualServe4 PASS,
41normalattempts retained. Reader9savednativearchives/30localcalls includingreused
PASS exactbodySHA/length/stablepages and recursive sourcebytes+mtimes unchanged.
No new inference/world in native reader checks. All gate subprocesses exited0.
Earlier task2641/10 480.14s and aborted merged2641/10 479.27s belong to PRIOR source;
those are historical, superseded for final approval. Old pending merge safely
aborted; feature source remains af7b4af, no merge in progress, owner bytes/patch unchanged.
Task delivery e2a5e6f is preserved historical commit; correction delivery follows it.

USAGE PAUSE: corrected taskdelivery9c65f3b pushed/preserved; stop with headroom
(last18%five-hour remaining), no resets/automaticresume. No active agents,
model servers or fullgates. Featureintegration NOT complete. NEXT after ownerresume/
currentusage+Gitcheck: merge latest task into feature with no-ff/no-commit, repeat
full current-tree gates, then integrationcommit/push. Do not rerun completed task
gates if reviewed source remains exact. Preserve all branches/worktrees/archive data.
Root helper run_reader_gates.py retains commands/exits/sourcehash in unique prefix
*-gate-status.json. Use fresh ln09f1-fix3-merged prefix for future repeatedgates.

LN09f1 is domain reader ONLY, not authenticated API/UI/export. Narrow integrity tags
never certify world/checkpoint/lineage/unselected body validity. Normal product
rollback journals supported; externally converted WAL rejected before SQLite connect.
No immutable/migration/copy/permission workaround. Python allocation budgets cover
schema/metadata/body transfer; not SQLite native parsing memory or constant-time scans.
Next LN09f2 draft W/09f2_trace_api-draft.md is NOT active: bounded catalog discovery,
shared authenticated API and inert offline factory, then CLI/UI and forensic/portable
export. W denotes ignored .superpowers/sdd/2026-10-19-live-npc-runtime in FEATURE.
Llama argument compatibility and full LN09 acceptance remain incomplete.

LN09e delivery62ea35c/integration90ef1e2 andnativeevidence0fc88f9 completed/pushed,
2547/10existing skips task+merged allcompatibilitygates PASS. Do notredispatchthem.
9f1 domainreader isnot authenticatedAPI/UI/export. Narrowintegrity tags nevercertify
world/checkpoint/lineage/unselectedbody validity. Externallyconverted WAL is rejected
beforeSQLiteconnect toavoid sourcewrites; no immutable/migration/copy/permissionshack.
Normalrollbackwriterconcurrency tested. Later9f domainforensic/export, authenticated
API/offlineCLI, UI exactcontracts stillneeded; rootnotes trace-analysis-next-contract-notes.md
andtrace-export-seams.md retained. Llamaargumentcompatibility andfullLN09acceptance remain.

New archived live cognition for BOTHproviders saves atomic exactrequest/BLOB before
network and responseevidence/outcome beforestaging, ackafterimport; sealedtracecopy and
eagerofflinereplay retain originalbytes/times, legacyomissions stayomitted. Hardcrash
unimported source spools remain separate uncommitted forensic, never recoveredproposals.

Native probes COMPLETE, do not rerun: ignorednative_trace_probe.py outputs ln09e-native-
llama (4calls), ollama(4calls), llama-3ticks(12calls). Twentyrealcalls/ninearchives, both
backendexactbytes/status/timing, coldinitialworld/cursors and provider-offline replay
PASS; sourcefiles unchanged. Allownedservers exited0/PIDsabsent/portsfree. Ollama1accepted
work; llama12nonnullproposals rejected because nonemptyarguments (duplicatedtargetlabel).
Longerunchanged6tickworld reproduced; gatewaycorrectlyrejects. NO outputcoercion/fix.
Committed report docs/orchestrator_handoff/live_npc_native_trace_probe_2026_10_27.md has
exactIDs/limits. Not fullLN09acceptance. Any proposalcontract change needs isolatedtask,
TDD/review and explicit oldrequest/fingerprint/replay compatibility, no globaldescription
change breakingrecordedtapes. No exactfixcontractyet.


## Completed producer interfaces and evidence

LN09c delivery76911a3/integrationc2d2f87 adds format2 newarchives, immutable content-addressed
opaque inference BLOBs, optional closed request_trace/response_trace metadata in existing
journal records, same journal-boundary algorithm and prefix-restricted BLOB reads. Format1
ordinary read/write remains usable without migration; trace-bearing writes reject. Task/
merged2469/10existing skips and full compatibility gates passed. All branches preserved.
LN09d adds PreparedInference/InferenceObservation/prepare_inference/settle_observation,
Urllib post_bytes observer, durable private bounded self-contained fsynced spool,
DecisionBroker.bind_trace and acknowledge_trace(job,*,result=None). Bound spawned worker
receives primitive bytes+metadataJSON, validates rebuilt payload then sends ORIGINALbytes.
Success/error/invalid/empty/oversize max+1/partial/truncated/timeout evidence retained.
Reap beforeharvest; real success needs complete matching2xx evidence. Ack realjobs requires
cached/reaped settlement, injected overridden-start fakes can supply result. Corrupt or
unimported spools retained; no ack before caller archiveimport. FivePythonstyle/57capture
plus20existing correction tests passed; full root gates above. Exact task/prombt/report
09c_inference_trace_storage* and09d_inference_capture* are compressed reviewed history.

Earlier LN09b deliverybb907a0/integrationed61354 shares legacy live archive mode ollama
with provider.kind ollama/llama_cpp, no second controller. Ollama defaults/fingerprints
unchanged; llama pins actual local GGUF SHA256 and matching /props alias/path, not dummy
/api/tags digest. No product server/GPU launcher. LN09a deliveryee11870/integration6321306
adds deterministic replayable disturbances, including format2 one-step work interruption
inside existing work phase before charge/progress. Their reports remain authoritative.

## Owner requirements and environment

Owner explicitly requires exact per-call body/backend/model/response/timing retention,
including invalid responses, superseding old raw-invalid nonretention. Data privileged,
neverNPC/unsafeHTML; bounded incomplete/unknown evidence, no fabricatedbytes/times.
Ollama /api/generate and llama /v1/chat/completions must both work in persistentworlds.
Native llama /home/at-boy/Projects/codex/llama.cpp/build/bin/llama-server, model
/home/at-boy/Projects/codex/llm-models/gguf/Qwen3.5-4B-Q4_K_M.gguf. Normal acceptance AMD
Vulkan0 perowner; old NVIDIA insufficient for intendedconfig. Prior AMD4.15s/dual8kctx7.74s
standalone probes valid, BOTH ownedservers stopped, logs llama-native-preflight. These
are NOT persistent-world acceptance. User permits modeldownloads in gguf dir ifneeded;
none needed/downloaded. Future GPU/model/backend/context-memory profiles BACKLOG ONLY.
Earlier realOllama preflight logs ln09-baseline-preflight retain3attempts with coldchild
and exact offline2point replay; model hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M pinned
3c4f22130d403283bb961721f2c4f83e4409afcbb7a7cd992f425c62b9304e35. No active servers.

## Recovery and ownership

Ignored .superpowers/sdd/2026-10-19-live-npc-runtime/progress.md is recoveryledger; packages,
reports, helperoutputs and rootnotes retained. Helpers recorded_matrix.py26,
archived_cli_acceptance.py7, served_cli_acceptance.py4, wheel_serving_check.py11+4;
check_gate_results.py verifies results/readonly files. Uniqueoutputdirs, separateexamples
AFTERmake exits. Existing VENV .worktrees/task24/.venv Python3.13.5; support>=3.11.
make needs escalation for actualChrome/localfixtures. SSHnetwork workaround
GIT_SSH_COMMAND='ssh -F /dev/null -o BatchMode=yes'.
Owner-local masterplan edit docs/superpowers/plans/2026-10-19-live-npc-runtime.md
(observasmall, clearly specified tasksble) MUST NOT be staged/restored/fixed.
DiffSHA294b20313ae2de248301fa20bbb4f9c312d51efa4851a434466f98a588dd93e6.
Old root duplicate task/prombt edits were backed up and restored before the aborted
merge; feature now has no duplicates. Preserve every branch/worktree/archive.
Protected refs unchanged: main d8ea51797b5ca3bfefa37cd5f7bafc95cbee5899;
milestone/v0.6 6bf4c63637584584a8dfce009d2d1d79987be570; tag1040fd2e3e4068d3f7dba77be37179299273aa41
peeled092715c11ed00b98255ae611fcef1bcfb8f1de9d. NO main/milestone/tag action now.
Owner authorizes task featureintegration/push. Managers mutate/systems behave/events
immutable; RuntimeService solewriter; filteredLLM proposals throughgateways; simulation
owns truth/goals/stages. Deferred8d desktopParent/Lifecycle headerwrap finalreviewtriage.
Keepfive-hourusage headroom BEFORE10%remaining; no resets orautomaticresume afterpause.
