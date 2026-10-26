# LN09a — Deterministic completed-boundary disturbances

Status: amended implementation independently reviewed and task-validated; feature integration pending.
Base44b634a task/merged validated2230/10existing skips,39examples/archive/CLI/serve/wheelPASS.
Purpose: provide the missing producer for owner-approved LN09 resource_loss and
work_blockage acceptance, without a player API or harness-owned world mutation.
Existing service remains sole writer. This is prerequisite behavior, not acceptance.

## Scope

Exactly9 worker paths: new src/living_world/runtime/disturbances.py;
src/living_world/archives/model.py; src/living_world/archives/catalog.py (narrow fork policy guard only); src/living_world/runtime/entrypoints.py;
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
RuntimeService live paths for both policies through ordinary proposal gateway;
resource loss applies, canonical work truthfully yields no_eligible_work (see limitation
below). Direct helper work-applied coverage uses a domain-valid multi-tick work offer
through WorkActionHandler, not a claim about production canonical composition. Cover
all-stock resource loss exactly once, workreservation/event order,
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

## Fingerprint clarification — root before producer correction

Existing effective_config_fingerprint hashes scenario/seed/software/provider/feedback,
not arbitrarysettings. Add top-level boundary_disturbance:record.as_document() to that
fingerprint document ONLY when an active versioned record is present. Absent record
and legacy scalar-only labels retain the exact prior document/hash. Do not hash
unrelated settings or change format1. New schedule must bind every request/livecursor/
source_config_fingerprint/replay/reuse guard. Add explicit oldhash-preservation and
newpolicy separation tests; do not merely rely on schedule journal fingerprint.
Candidate mutation must require matching run_metadata scenario key/seed and valid
canonical camp settlement. Inspect public service.fork/catalog compatibility too:
changing/clearing activepolicy through a direct fork config must reject; if existing
producer does not enforce this, report exact gap before expanding file scope.

## Direct catalog fork clarification — root before correction

RunCatalog.fork currently permits same-mode live configs to alter the active policy.
Add a narrow pre-reservation guard when source.mode == target.mode == ollama:
optional versioned boundary_disturbance records must equal, rejecting enable, clear,
and change. Absent and legacy scalar-only annotations both mean no active policy.
Keep existing ollama -> journal_replay transition legal: replay target intentionally
omits the active record and executes sealed SOURCE policy. No general fork settings
rewrite or legacy compatibility expansion. Direct catalog tests cover enable/clear/
change rejection before reservation/source-byte effects, unchanged inheritance, and
legal source-policy offline replay. Other catalog behavior remains unchanged.

## Canonical work viability limitation — root investigation

Canonical FoundersRules.required_progress is1, each eligible normal work order
progresses/completes in its creating tick, while unavailable work becomes BLOCKED.
FoundersPolicy.from_scenario rejects altered policy manifests. Therefore this fixed
completed-boundary policy cannot find READY/ASSIGNED/ACTIVE canonical work through
ordinary live proposals. Preserve truthful no_eligible_work; never fabricate a work
order, alter canonical policy, or claim a custom fixture as production acceptance.
The worker must report this limitation explicitly. Applied work interruption through
the production composition remains an OPEN prerequisite to LN09 acceptance and task
completion; root must decide and document a bounded follow-up before implementation.
No full gates/approval/commit of this incomplete task solely because focused tests pass.

## Root execution-phase amendment — supersedes format-2 work limitations above

Authorization: approved LN09 requires a real work disturbance; read-only probe confirmed
that a before-work standalone hook still retries BLOCKED work immediately and newly
created work is PROPOSED. Root ruling: intervene inside existing atomic WorkExecutionSystem,
only for an explicitly installed one-step request. This preserves canonical definitions,
normal scheduler order and default recorded behavior. The earlier nine-file/no-domain
boundary and open-limitation stop are superseded ONLY by this exact amendment. Task
remains incomplete until new production-path evidence and renewed review/root gates.

Allowed worker paths are now exactly12: previous9 plus NEW src/living_world/work/interruption.py,
src/living_world/work/execution.py and src/living_world/simulation/simulation_engine.py.
Tests remain in authorized tests/test_runtime_disturbances.py; no other tests/files.
Do not edit masterplan or common root status docs. No new world schema, cursor field,
external API, CLI flag, work policy constants or canonical scenario modification.

Policy compatibility: preserve format1 at_tick2 kinds/resource+work semantics exactly,
including old completed-phase work/no-eligible outcomes. Accept format2 ONLY with
kind work_blockage, at_tick2. New factory work_blockage creates format2; resource_loss
still creates format1. Fingerprint includes unchanged full record; never reinterpret
format1 or old hashes. Journal payload keys stay identical; schedule_fingerprint binds
version/phase. Format2 work manager events occur at execution tick1, resulting completed
checkpoint/audit boundary_tick2. This is deliberate, not an event retimestamping.

work/interruption.py owns frozen keyword-only WorkInterruptionRequest(settlement_id:str,
execution_tick:int) and WorkInterruptionResult(request:WorkInterruptionRequest,
outcome:Literal[applied,no_eligible_work],work_id:str|None,event_references:tuple[str,...]).
Strict nonempty IDs, nonnegative actualint (notbool), closed outcomes, applied nonempty
work/ref tuple, noeligible None/empty; unique ordered eventrefs. No archive/runtime
imports or world references. WorkExecutionSystem.configure_interruption(request|None)
validates/replaces request and clears previous result; readonly interruption_result
property exposes last successful phase result. SimulationEngine public
configure_work_interruption(request|None) delegates and checks failed-tick guard;
readonly work_interruption_result delegates. No scheduler replacement/rebuild required.

Execution: create result ONLY for request.execution_tick == state.tick. Current scheduler
executes systems before tick increment. No policy means EXACT old ordering/events/world.
Keep ordinary deadline/prerequisite/permanent-target/readiness and resource/labor/tool
availability checks. Select FIRST executable target-settlement work in existing work.all()
order. Newly PROPOSED is normally promoted READY; BLOCKED with successful normal preflight
is normally marked READY. Existing ASSIGNED/ACTIVE must have a valid reservation first.
Select before charging/progress; for READY after successful preflight but BEFORE new
reservation, for valid ASSIGNED/ACTIVE BEFORE adding phase-local labor/tool locks.
Call existing work.block(id,External work interruption), capture ONLY emitted release/
blocked eventrefs in manager order, immediately continue that order for this phase.
Do not consume labor/tool phase locks for interrupted work; other orders execute normally.
Do not select unavailable/deadline/prerequisite/invalid-target work, fabricate work, or
mutate dictionaries. At most one selected order; if none emit noeligible result even with
zero work. Publish result ONLY after atomic shadow phase successfully publishes state;
exceptions publish neither result nor advancing archive. Next tick retries normally.

runtime/disturbances.py adds frozen PreparedBoundaryDisturbance carrying only parsed
policy, request|None and terminal_before_step:bool (no engine/WorldState references).
prepare_boundary_disturbance(candidate,config)->PreparedBoundaryDisturbance|None validates
binding and only prepares format2 work when candidate.tick+1==2. Use existing central
founders_terminal_conditions before intervention. Terminal base => prepared terminal flag,
no installed request. Otherwise configure matching request(camp,candidate.tick) and retain
prepared token. Other policy/tick =>None, existing finish-only format1 unchanged.
apply_boundary_disturbance adds optional prepared keyword defaultNone. Format2 completed2
requires exact matching prepared policy/request. If terminal_before_step, emit terminal;
else require matching successful engine work_interruption_result and translate exact
outcome/work/eventrefs into unchanged journal grammar. Applied interruption may coexist
with resulting terminal checkpoint: later consequences/needs/goals/stage retain authority.
Do not replace applied with terminal after the effect. Validate matching candidate config,
metadata/camp for both phases; reject missing/inconsistent results before archive commit.

Live and replay preparation.install call prepare helper before ordinary engine.step and
retain token; finish_tick passes token before cursor/snapshot checks/commit. Replay uses
sealed SOURCE config. close clears candidate transient request/result and token; no data
is retained outside ordinary blocked WorkState/events/config/journal. Failure discards
candidate under existing service semantics, no fake general rollback. Exact offline
comparisons and normalized local base_revision remain mandatory for format1 AND2.

NPC flow: only next normal feedback sees fixed qualitative blocked work projection and
ordinary offers; no new context/feedback API, numbers, IDs, phase/schedule/audit data.
Document phase and engine-only token/result before new code in existing allowed doc.

TDD: first reproduce canonical factory work policy currently always noeligible. Update
factory expectation to format2 and prove ordinary fake-provider live gateway-created work
BLOCKED at completed2 with no selected input charge/progress/effect, next feedback blocked
prose and later ordinary retry. No custom work fixture may substitute this proof. Cover
no proposals/unavailable work/zero work, deterministic multiple orders, released reservation
and lock reuse, injected manager/event failure no result/advancing commit/publication,
pause/staged response reuse/cold restart/child before+after2/fork inheritance, exact offline
all-world/events/cursors/audit/revision normalization and tampered version/result/event
rejection. Preserve format1 resource AND old work helper/replay coverage plus oldhash.

Focused regression command: existing6 modules plus tests/test_work_execution.py if that
filename exists (otherwise report actual owning test path before changing command). Scoped
Ruff/Black all authorized Python paths. Append amendment RED/GREEN/evidence to own report;
root renewed independent review and full task/merged gates before any commit/integration.

Cleanup clarification before worker code: SimulationEngine.configure_work_interruption
checks failed-tick guard for NON-None requests only. None clearing of transient request/
result is always allowed, including failed candidates; it changes no WorldState and
does not clear failed-tick guard or permit engine reuse/step. Test failed-step cleanup
while subsequent engine.step still rejects. This overrides earlier unconditional-guard
wording and lets close deterministically release transient references without masking
the original failure.

Result validation clarification: require matching prepared policy/request/result plus
ordered referenced immutable events existing with execution tick/kinds/target/camp.
Do not require final WorkState still BLOCKED if later ordinary consequence systems
legitimately transition it; applied interruption can coexist with resulting terminal
checkpoint. Work-phase result and immutable block event establish the action, not a
forbidden override of subsequent domain authority.
