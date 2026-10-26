# LN09a — Deterministic completed-boundary disturbances

Status: authorized prerequisite after LN08f integration44b634a.
Base44b634a task/merged validated2230/10existing skips,39examples/archive/CLI/serve/wheelPASS.
Purpose: provide the missing producer for owner-approved LN09 resource_loss and
work_blockage acceptance, without a player API or harness-owned world mutation.
Existing service remains sole writer. This is prerequisite behavior, not acceptance.

## Scope

Exactly8 worker paths: new src/living_world/runtime/disturbances.py;
src/living_world/archives/model.py; src/living_world/runtime/entrypoints.py;
src/living_world/runtime/ollama_driver.py; src/living_world/runtime/journal_replay.py;
new tests/test_runtime_disturbances.py; docs/npc_information_boundary.md (newpathflow
only); own docs/subagent_execution_plan/live_npc_runtime/09a_boundary_disturbances-report.md.
Root owns exact task/prombt/common4statusdocs. No other production/domain/service/
controller/feedback/provider/API/CLIparser/schema-file/version/dependency changes.
Python>=3.11, strict hints/frozen records. No worker VCS/index/subagents/fullmake/
examples/installs/realmodel/othercheckout writes. Normal attempts retained; unittemp
fixtures allowed. Producer gaps -> root amendment before scope expansion.

## Schedule and compatibility

Define frozen keyword-only dataclass BoundaryDisturbance in archives.model: format:int=1, at_tick:int=2,
kind:Literal[resource_loss,work_blockage]. Strict actualint (notbool), exactconstant
format/tick/kind. Provide as_document()->dict[str,object] with all3fields and
fingerprint:str property sha256(canonical(as_document())). parse_boundary_disturbance(value:object)->BoundaryDisturbance uses
existing document grammar/exactkeys {format,at_tick,kind}; no runtime imports in model.
New optional AttemptConfig.settings key boundary_disturbance contains that JSONrecord,
legal only modeollama, existing disturbance label must equal kind. Absence preserves
all old semantics/fingerprints, INCLUDING old scalarlabel-only annotations (no new
behavior magically activated). Explicitnone omits both newrecord and disturbancekey
on fresh requests. No arbitrary schedule, amounts, scripts or target IDs from users.
Config is retained immutable attempt input; no new retainedfiles/migrations. Old
archives remain readable; older readers may reject the new optionalsettings/kind.

prepare_archived_launch adds optional keyword disturbance:Literal[none,resource_loss,
work_blockage]|None=None. Validate strict string/knownchoice beforeeffects. None means
nooverride/inherit, freshpreset None/none retains oldsettings exactly. Freshlive
resource/work builds matching label+versionedrecord. Freshrecorded/replay reject any
explicitdisturbance beforeeffects. Resume/fork explicitvalue must exactlymatch source
activepolicy (none onlymatches no activepolicy); never enable/clear/change policy on
an existing source, including legacy scalar-only annotations. DefaultNone inherits.
Use _requested and sourceconfig unchanged, no duplicated equality/provider logic.
No CLIflags here; latermanualharness passes typedfactoryargument. No runtimeexports.

## Phase, authority and exactly-once

Apply on detached candidate AFTER ordinary engine.step/domain work/needs/goals/stage
and existing terminalfinalization, inside _LivePreparation.finish_tick, BEFORE driver/
feedback cursor collection and atomic advancing archive.commit. At worldtick2 only.
This completed boundary precedes NEXTtick feedback; do not bypass feedback exactbase
validation, invent a syntheticCheckpoint, or mutate published/source world.
No same-tick changed checkpoints, source cursor changes or new drivercursor fields.
Absolute tick means childat>=2 never repeats; childbefore2 applies once on its own
advancing path. Pause/abort before commit applies nothing; pending request provenance
uses unchanged predisturbancebase. Failure after manager mutation discards candidate
through existing controller failure semantics, archive stays at lastcompletepoint;
no claim general in-memory rollback or physicalrepair.

apply_boundary_disturbance(candidate:SimulationEngine,config:AttemptConfig,*,
base_revision:int)->tuple[JournalEntry,...] validates policy/candidate binding and
returns () for absent policy or tick!=2. When configuredtick2, emits exactlyone
closed boundary_disturbance entry including no-effect/terminal outcomes. Before any
mutation use existing centralized founders_terminal_conditions predicates; if any
terminal true, record terminal and skip (do not recompute/override goal authority).
No normalcase can force terminal/stage/resource completion. Nonterminal resource/
work changes take effect in worldtruth at boundary2; needs/goals systems reevaluate
normally on nexttick. Allwrites via existing managers; no state dictionary writes.

## Resource loss

Owner state.scenario_entity_bindings[camp], valid canonical camp settlement. Validate
resources iscopied mapping with exactlycanonical food/water/timber and strict
nonnegative integer quantities; reject malformed/bool/unknown beforemutation. Policy
removes ALL currentlyheld timber (explicit all policy, no clamping/literalstock guess).
Before>0: entities.set_attribute(entity_id=camp,key=resources,value=updatedcopy),
then events.record(kind=runtime_resource_loss,subject_id=camp,attributes containing
resource=timber,quantity_before,quantity_after=0,quantity_removed=before). EventManager
owns immutable event. Do not call private ResourceSystem or add a resource subsystem.
Before0: no manager/event mutation, journal empty_stock. Existing work may later block
on missing reserved inputs through ordinary systems; no fabricated replenishment.

## Work blockage

Filter work.all() in its existing deterministic (-priority,created_tick,id) order
for camp and state READY/ASSIGNED/ACTIVE, choosefirst. No targetfromNPC/model/harness.
Call work.block(id,External work interruption); manager owns reservationrelease/events.
Do not construct work or change inputs/progress directly. No eligible =>journal
no_eligible_work, no retry/deferredschedule/fabricatedeligiblework. Actualacceptance
must report effectunmet if model generated no eligiblework by boundary2.

## Journal contract

Newkind boundary_disturbance strict exactpayloadkeys:
base_revision, boundary_tick, kind, schedule_fingerprint, outcome, target_id, resource,
quantity_before, quantity_after, event_references. base_revision nonnegativeint,
boundary_tick actualint2, kind closed, fingerprint64lowerhex sha256(canonicalrecord),
outcome applied|empty_stock|no_eligible_work|terminal. Engine-only IDs nonemptystrings
orNone; event_references ordered unique nonemptystring IDs generated bymanager.
resource applied/empty_stock: targetcamp nonnull, resource timber, before>=0,after0;
applied before>0 and exactlyone loss event, empty_stock before0/events[]. workapplied:
targetworknonnull, resource/quantitiesNone, referencesall emitted reservationrelease/
blocked events in order; no_eligible_work target/resource/quantitiesNone/events[].
terminal target/resource/quantitiesNone/events[]. Reject kind/outcome mismatches.
Entries atomically accompany advancing snapshot, never appended applied ahead ofcommit.
Actor requests/action outcomes retain existing provenance/charges; journalids never
enter cognitive records or offered prose.

## Replay

JournalReplay uses SEALED SOURCE config/schedule at same finish_tick phase after
ordinary gateway/worldstep and before targetworld/cursor comparisons. Validate
expectedsource boundaryentry count0/1 against activepolicy/targettick and exact
semantic payload. Source base_revision must match selected previoussourcecheckpoint;
normalize generated localentry to localbase_revision for targetjournal. Compare all
otherfields including target/amount/outcome/eventrefs/fingerprint exactly. Import
normalized generatedentry together with existingoutcomes. Never weaken source seals,
_same_checkpoint/cursor/request/gateway/feedback comparisons or contact provider.
No schedule from replaytargetconfiguration; no inference from arbitrary journallabels.
Missing/extra/wrongboundary/mismatched entry or mutation =>failclosed/no nextcommit.

## NPC-visible flow (document before implementation)

Engine truth: changed camp timber or blockedwork through managers. Perception:
following existing feedback samples only holder-scoped local need/work/mandate facts.
Transformation: existing adapters produce qualitative prose/safe offeredlabels.
Memory: existing ownerobservations/memories update on changed qualitative hashes at
NEXTprepare, unchangedfacts remain deduplicated. Inference: actualLLM sees filtered
context and offers, proposes only. Gateway revalidates worldtruth/action availability.
Hiddenengine-only: scheduleconfig, exact quantities, manager IDs, event/audit refs,
archive/checkpoint/fingerprint fields. No raw WorldState/runtimeobjects/otherNPC's
private cognition in prompts. No success injected when actualmodel declines actions.

## Tests and gates

Meaningful RED beforecode. Unit strictgrammar/legacycompatibility and fakeprovider
RuntimeService live paths for both policies with eligiblework created by ordinary
proposal gateway, all-stock resource loss exactly once, workreservation/event order,
empty/noeligible/terminal/malformedstate outcomes, manager/eventfailure no advancing
commit and sourcestate untouched. None behavior byte-exact to old reference.
Pause after stagedresponses before boundary2, close/restart childexactworld/cursors,
reuse validresponses/no duplicatecharges, one committeddisturbance; childbefore/after
boundary and forkinheritance/sourcebytes. Offlinereplay with transportforbidden
compares every advancing completeworld/events/cursor, semanticjournal and charges;
missing/extra/tampered schedule/entry failclosed. Fixed terminalzero-step unchanged.
Newfeedback sample after boundary2 demonstrates changed safe perception/offers,
restartdedup and hiddenfields absent from serializedcontexts. Stale work/resource
offer capturedbeforemanagerchange is rejected by existing public WorkActionHandler/
gateway without extra mutation; this defensiveunitproof does not fake realmodeloutput.
Factorytypedkeyword validation/configinheritance with no parser changes.
Focused newtest +test_runtime_ollama_driver.py +test_runtime_journal_replay.py +
test_runtime_founders_feedback.py +test_runtime_launch_request.py +test_run_archive_store.py,
scopedRuff/Black, rootwhitespace. ReportRED/GREEN, command/result/counts/warnings,
actualscope/authority/persistence/NPC/replay evidence and rootgatespending. No commits.
Independenthighreview before root task/merged make,separateexamples,canonical26/CLI7/
sourcepublicserve4/wheel11+actualserve4. Preservebranches/worktrees/owneredit. LN09b
manualharness/examples/docs/actualOllama disturbedruns and fullacceptance follow;
this prerequisite alone cannot complete originalLN09 or authorize main/tag changes.
