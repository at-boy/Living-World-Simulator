# Continuation brief — November 14, live shelter restore

Feature checkout `.worktrees/live-npc-runtime`, branch `codex/live-npc-runtime`.
LN09h deliveryde0552e integrated by e454722; taskbranch
`codex/live-npc-ln09h-native-acceptance` pushed and preserved, clean checkout
`.worktrees/live-npc-ln09h`. Original live-runtime design/plan execution remains
authorized. Stop BEFORE five-hour remaining falls below10%, with review/fix
headroom; no resetcredits. Root owns architecture/task transitions/integration.

## Latest task: live shelter restore

Live founders now validate the historical maintenance, housing and
composition records of collapsed shelters. Destroyed shelters remain
excluded from active capacity. The recorded path and live decision
contracts are unchanged. See the [task report](../subagent_execution_plan/live_npc_runtime/09k_shelter_restore-report.md).

The original llama.cpp campaign now restores checkpoint 14 and replays
all 15 checkpoints and 28 retained responses exactly. A fresh llama.cpp
run ended at its tick-16 cap in settlement stage and replayed all 17
checkpoints and 32 responses exactly. Both tick-2 work-interruption
trials still found no eligible work. Full native acceptance remains open,
including a named llama.cpp terminal outcome. All temporary servers are stopped.

Task delivery `e2d20ac` is preserved on `codex/live-npc-ln09k-shelter-restore`.
Task and merged gates each passed 3,080 tests, 10 existing skips, 40 examples
and all 13 validation jobs. The merged suite took 780.17 seconds.

## Prior task: offer-bound founders request contract

LN09j adds the opt-in `founders_offer_bound_v1` contract for canonical live
founders on Ollama and llama.cpp. Each provider receives a response schema
using only the public action and target pairs already offered. The previous
contracts, parser, gateway and native acceptance criteria are unchanged.
The independent review found no substantive issues. The implementation and
native evidence are in the [task report](../subagent_execution_plan/live_npc_runtime/09j_offer_bound_request_contract-report.md).

Task delivery `c22248e` is preserved on
`codex/live-npc-ln09j-offer-bound`. Both the task and merged runs passed
3,073 tests, 10 existing skips, 40 examples, and all 13 validation jobs.
The merged suite ran in 786.31 seconds. Both runs used the same reviewed
358-file source. All 186 wheel entries match between the two builds.

Ollama reached the founding deadline at tick 13 and reproduced the entire
committed run offline. llama.cpp reached settlement stage and validated all
28 responses, then failed after committing tick 14. Both the current code and
the base restore validator reject that checkpoint after the engine destroyed
two shelters while retaining their maintenance records. Explicit checkpoint
13 replay reproduced every world and cursor through that boundary. Both
tick-2 work-interruption attempts found no eligible work. The remaining
native acceptance criteria are open. All four temporary servers are stopped.

## Prior task: live trade vocabulary

LN09i delivery `073f7aa`, integrated by this merge; preserved task branch
`codex/live-npc-ln09i-dispatch` and worktree `.worktrees/live-npc-ln09i`.
The native Ollama tick-4 trade offer exposed an overly broad prose check.
Live option and response validation now recognize only the existing public
trade key in its structured field; ordinary offer checks, gateway, prose
filters and recorded route stay intact. Independent review clean.
Task and merged gates each passed 3041 tests, 10 existing skips,
40 examples and 13 validation jobs. Reviewed 358-file source:
eed875df105f8f4281c56b556a19fc071f06ccdffc88e766aab2241a79e8ef6e.
Current offline-installed Python 3.11.2 wheel and real Chrome saved-world
inspection passed. See the
[native follow-up](live_npc_native_acceptance_followup_2026_11_12.md)
for the actual unattended and work-interruption evidence.
Ollama reaches the engine deadline at tick 13 (founding failure, 26 calls);
exact offline replay. The checksum-pinned additional 7B llama.cpp model reached
settlement stage and inbound food arrival by tick 10, then failed safely on an
unoffered key, with exact offline replay. Work interruption remains unmet on
both at the unchanged fixed tick-2 boundary. All 16 temporary servers from
this resume are stopped; actual host evidence in W/ln09i-final-native-cleanup.json.
Continue original acceptance only under its existing criteria. Whole-branch
review and release closeout remain pending.

## Canonical completion

- LN09g optin founders_empty_arguments_v1 delivery79b7220/integrationcf0cfbb:
  legacy omittedcontract unchanged, strict ordinarygateway. Prior bounded probes
  are compatibility evidence, not full founding/runtime acceptance.
- LN09f5a readonlyrollbackguard deliveryf17dad9/integration694eb00 and LN09f5b
  savedhistoricalworld inspection delivery9de8996/integration58c3611 complete.
- LN09f6a exactsavedtraceZIP delivery14b98c7/integration9b88122 complete after
  independent review/fix and repeated2989/10existing skips/39examples/all13jobs;
  source311/a9695bb3. Exacttrace metadata/bodies, deterministic privateexclusive
  publication; explicitly not portableworld/parentclosure/uncommittedspools.
- README first-run guide597c57f pushed, now links bounded experiment guide/040.
- LN09h boundedmanualhelper/040/40acceptancecases/guide deliveryde0552e COMPLETE.
  No productionpackage changes. Initialreview two P3 contractgaps fixedround1;
  fresh sol/high scoped re-review spec+qualityPASS/no findings. Rootnative report
  +README independently factchecked with no gaps. Taskfull3029/10existing skips
  759.95s; mergedfull3029/10/765.62s, actualChrome/40examples plus separate
  examples40/whitespace/all13canonical-package-browser-exportjobsPASS. Extended
  reviewed358sourcehash includesexamples:
  48215a24be4adaff9ee3fb0ef3a6457ddfcff970be456df4e3e1484c31e93b45.
  Initialtaskfull1failed3028passed10skips800.83s: old0.5secpreflight normalmissing
  got timeout duringnativeworkload. Isolated3PASS2.91s andquietfullPASS without
  any product/testdeadline change. Failed original logs retained, recoveryreused
  onlyfivepreviouslyPASS unchangedsourcejobs. Full merged13jobsfreshPASS.
- Actualcurrentwheel installedoffline onPython3.11.2: import/console/canonical26
  fresh/resume/Serve4+failedsetup/new040/exactexport4PASS (session14564). Existing
  uv used --no-index/--no-deps; copyfallbackwarning only. DefaultPython3.13.5.

## Real native evidence and honest unmet gates

Main sixcases BOTHproviders x baseline/resource_loss/work_blockage:48realcalls.
Bothbaselines/resourcecasesPASS, bothworkcasesUNMET/no_eligible_work. Models chose
largershelterlabor3 vs2founders; ordinarylaborpreflight correctlyblocks it before
format2interruption. Independentread-only investigation confirmedmodest/normal
laborjobs canqualify; no productionbug or permission toinjectdecisions/labor.
LaterOllamajobs completed butcannotrepairfixedtick2gate. Allsixsavedcases still
PASS exactrequest/responsebytes/backend/model/timings, ordinaryacceptedactions,
coldinitialcompleteworld/cursors andofflinereplay allworld/events/cursors/traces,
sourcebytes+mtimesunchanged. Both actualChrome nativecontrols (step/resume/pause,
shutdown/coldchild/step) add8realcalls; providerstopped browserchildreplayPASS,
includingsealedresponse reuse andduplicate shutdowncontrolcheckpoint semantics.
Nine currentinstalledwheel savednativebrowsercasesPASS/sourceinventoryunchanged,
includingfailedexploratory llama invalidresponseattempt. Root visuallycheckedUI.
Native report docs/orchestrator_handoff/live_npc_native_acceptance_2026_11_12.md
and reviewed09h-report.md are canonical evidence. FulloriginalLN09 NOTcomplete.
No modelserver running: actualescalatedhostverified9ownedPIDgone/exit0 andowned
ports18080/11435closed; processcommands/startUID/identity/logs preserved. Native
servers explicitlyauthorized onlywithfinallycleanup; stoponlyownedprocesses.

## Next and constraints

The shelter destruction restore defect is fixed. Remaining native work
acceptance needs a genuinely eligible native choice, never
syntheticreplacement or guaranteedvictory. Portableworld recursiveparentclosure /
uncommittedspool forensic work andfinalwholebranchreview remain pending; no next
implementationtask/branch activated. Before portabletask, reconcile approvedscope:
originaldesign line238 requiresSQLitebackup/closedtransactional export forlegacy
mirror; prior rootpending-export notes are not themselvesnewauthorization. Existing
W/portable-export-snapshot-probe.md is readonlyevidence, not a taskcontract. Do not
silentlydrop prior scope or infer permission fromroadmap; rootmustresolveexactscope.

RuntimeService solewriter; managersmutate/systemsbehavior/eventsimmutable. NPC
contexts filtered; no rawWorldState/internalIDs/otherhiddenrecords/admintraces.
Modeloutput untrusted ordinarygateway; engine owns truth/goals/stages.

## Recovery / preservation

W=feature `.superpowers/sdd/2026-10-19-live-npc-runtime`; progress.md canonicalledger.
Taskreports/commits compress completedhistory; neverredispatch completedtasks.
Allrootgates/helpers/reviews/nativecatalogs preserved. Currenttask gateprefixes
ln09h-task(failedmake),ln09h-task-r2(PASS),ln09h-merged(PASS); gatesessions75217/
33658. run_acceptance_gates.py includesexamples in sourcefreeze. task24venv3.13.5;
installed311venv W/ln09f6a-python311. Sandbox /proc/ps andsocketprobes cannotcertify
hostprocessvisibility: host/escalated verification required. Nativeproofs already
runhostescalated. Cleanup evidence ln09h-owned-server-cleanup-host.json.
SSH GIT_SSH_COMMAND='ssh -F /dev/null -o BatchMode=yes'. Preserveallbranches/worktrees.

NEVER stage/restore/fix owneredit docs/superpowers/plans/2026-10-19-live-npc-runtime.md
(observasmall, clearly specified tasksble), patchSHA
294b20313ae2de248301fa20bbb4f9c312d51efa4851a434466f98a588dd93e6.
Primary main d8ea517 hasowner-untracked .serena/ anddocs/research/, preserve.
Protectedremote refs verifiedNovember12 unchanged:
main d8ea51797b5ca3bfefa37cd5f7bafc95cbee5899;
milestone/v0.6 6bf4c63637584584a8dfce009d2d1d79987be570;
tagv0.6.0rc1 1040fd2e3e4068d3f7dba77be37179299273aa41,
peeled092715c11ed00b98255ae611fcef1bcfb8f1de9d.
Never merge/push currentwork to main/milestone/tag under thisscope.

## Owner-requested future ideas — November12

The owner asked to preserve the later worldbuilding/generational discussion in
[future_worldbuilding_vision.md](../future_worldbuilding_vision.md), linked from backlog.
This is an ideas record, not implementation authorization or a current release gate.
Resume the existing development path later. The owner separately authorized committing
and pushing this documentation. Preserve the existing owner plan edit.
