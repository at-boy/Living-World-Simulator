# 23 — Canonical founders acceptance and runtime composition

## Authorization and scope

Owner-approved after reviewed Tasks22,15,15c; branch task/23-founders-acceptance
from current milestone. Root retains architecture, boundary, review/gates/VCS.
Deliver one packaged fixed-version founding scenario and three deterministic
proposal tapes, engine-owned terminal policies and read-only saved-world serving.
No live LLM, world-outcome shortcuts, new domain mechanics, schema13, general
scenario manifest framework, browser mutation/admin, main merge or tag.
Python>=3.11, strict annotations; frozen records/manager mutation/system behavior.

## Public composition and packaged assets

New living_world/founders package: model.py (fixed typed policy/error), assets.py
(packaged materialization), setup.py (setup/attachment manager), runtime.py
(preparation/system/provider/terminals/inspection restore), __init__.py exports.
Assets exactly assets/{founders,definitions,success,stall,failure}.yaml, explicit
package-data under living_world.founders. materialize_founders_assets() context
manager copies only these five known resources to one TemporaryDirectory and
yields typed frozen paths, preserving relative definitions and Python3.11/zip
portability. Never infer a saved scenario source path from a fingerprint.

Scenario key canonical_founders_v1, schema1, seed42, default max_ticks16,
terminal_conditions in order [founding_failure,settlement_success]. Entities in
label order valley,camp,ada,bryn; definitions area,settlement,founder,shelter,storage.
Only settlement participates in production; only shelter in housing. Population
is fixed2; no population/growth/weather/trade/default automatic provisions.
Camp starts resources food0,water0,timber10, population2 and recipe inputfood1,
outputsfood4/water2. Ada/Bryn have distinct names and valid NPCIdentity maps.
Shelter definition housing_capacity2, storage definition storage_capacity20;
work construction owns is_constructed and placement as in existing WorkExecution.

Camp attributes.founders_policy is a closed explicit fixed-v1 manifest containing
version1, area_label=valley, founder_labels=[ada,bryn], fixed rules below, and
initial geometry by public label: valley Bounds(-10,-10,40,40) AREA; camp
Bounds(0,0,12,8) AREA insidevalley; Ada Point(1,1),Bryn Point(2,1) insidecamp.
No internal IDs. All configuration is included in existing scenario fingerprint.
Model a frozen typed FoundersRules singleton and derive its manifest from that
single source. Parser normalizes scenario mappings and compares canonical JSON
with the complete expected v1 manifest (not loose bool/int equality), rejecting
missing/extra/type/value changes. This is a fixed acceptance preset, not a
new general authoring schema; meaningful rule changes require versioned assets.
No rule constant may silently differ from the manifest fingerprint.

Rules: deadline12; need window/duration3, requirement_per_person1, secure0.0,
strained0.5; consumptionfood1/water1 per person/tick; foodwork10,waterwork8;
work progress1,normal labor1; sheltercount1/timber2; large sheltercount2/labor3/
timber4; storagecount1/timber2; maintenance initial/max3,mincondition2,
deterioration1,recovery1,foodupkeep1; storage spoilage0 for food/water;
town population3; homeland capacity1,delay2,cost0,reliability1.0,
allowed_imports=[timber],allowed_exports=[food]; inbound dispatchfood1.
Recipe/capacities/resource starts/geometry are also explicit manifest or scenario
initial data, never hidden outcome constants.

## Initial setup and dynamic attachment ownership

FoundersSetupManager owns canonical orchestration, but every domain mutation
uses existing managers. Stage all WorldState fields using the established work
shadow pattern: deep-copy mutable entities/relationships, copy all other dict
collections, retain immutable records/scalars. Do not deepcopy frozen Event
mappingproxy attributes. Initial setup touches no shared mutable record outside
those copies; iterate dataclasses.fields for commit surface. Validate all staged
manager domains before field-wise commit to the original WorldState object.
No initial work orders (live WorkManager caches IDs). Collision-scanning entity,
relationship/event/reference managers skip staged IDs; prove next-ID behavior.
ScenarioRuntimeManager.bind is an earlier independent atomic graph boundary.
Setup failure leaves the valid bound graph only, no partial domain state or save;
retry equals clean setup. Do not claim whole-engine rollback or touch live counters.

Initial manager-created records: four needs (food/water/shelter/storage), one
consumption policy, founding and growth goals, seven objectives, one known
homeland reference, initial placements and stage program. Canonical engine IDs
are fixed readable IDs generated/resolved engine-side; none appear in assets/tapes
except version/schema/ordinal fields, which are tape headers, not NPC prose.
Need IDs need_founders_{kind}; goals goal_founding,goal_growth; objective IDs
objective_founders_{water,food,shelter,storage,maintenance,connection,population}.
Goal founding owns firstsix, deadline12, authorized settlement_work. Objectives
authorize matching exact WorkCategory values (produce_food,gather_water,build_shelter,
build_storage,maintain_capability,establish_external_trade_connection as applicable).
Growth goal owns population objective, no deadline. Goals start via ordinary
manager defaults; normal goal evaluation activates/evaluates them.

Food/water completion: SustainedNeedCriterion(kind,0.0,3). Shelter additionally
ConstructedCapabilityCriterion(shelter,1) and CapacityCriterion(housing,2), plus
SustainedNeedCriterion(shelter,0.0,3). Storage additionally constructed storage1,
capacity storage20 and sustained storage0.0/3. Maintenance maintained shelter1
mincondition2; connection ExternalConnectionCriterion(homeland,contactable);
growth PopulationMinimumCriterion(3). All needs use3tick windows. Stage founding
camp empty; settlement requires all six matching requirement roles; town reuses
those plus growthpopulation3. No direct completed/failed/promoted state setters.

After successful setup, one immutable canonical_setup_completed event at tick0,
subjectcamp, exact attrs policy_version,policy_fingerprint,homeland_reference_id.
The marker + complete expected immutable definitions/policies/program/reference
policy are all-present/all-absent boundary. On resume validate immutable setup and
evolving loaded-state invariants without resetting resources/status/ticks/contact.
Marker absent with partial domains or nonzero tick rejects; never fill holes.
Marker present with incomplete/mismatched setup rejects, no repair. Dynamic
work/dispatch/events and delayed policies are permitted only through valid domains.
Restore ephemeral resource vocabulary food/water/timber on fresh/resume/inspect
only after successful validation. Repeated setup is no-op, with no duplicate events.

FoundersCompositionSystem is ordinary after default systems, before proposals/
work. Manager atomically stages attachments using same shadow pattern. Directly
owned live constructed shelters get housed_in edges for both founders and one
maintenance policy via managers, with one founders_shelter_composed event
(subjectshelter, attrs settlement_id,occupant_ids,maintenance_policy_id). Existing
valid attachments no-op; contradictory partial attachments reject, not duplicate.
Storage policy is created ONLY after owned constructed storage exists, spoilage0
for food/water; creating it initially would discard startup stocks as overflow.
Record founders_storage_composed once, subjectstorage, attrs settlement_id,
storage_policy_id. Preserve already valid dynamic policy states on resume.
Shelter built tick3 gets attachments tick4; HousingSystem first sees allocation
at5; secure shelter history5–7. Storage built4 is assessed4, policy attaches5.
Recipe/consumption/upkeep then hold camp stocksfood10/water8 within capacity20.
This is an existing engine abstraction, not an agricultural-realism claim.

## Minimal ordinary registration hook

Extend register_system(system, *, key: str|None=None) without changing unkeyed
behavior. A nonempty named key appends once, replaces exactly its registered
ordinary list position on repetition, then rebuilds existing scheduler. Invalid
system/key rejects before mutation; keyed rebuild failure restores previous
list/key registry/scheduler. No new phase. Canonical key canonical_founders
prevents duplicates across preparation instances and retains housing-before-
composition/proposal/work/consequence/need/goal/stage ordering.

## Offers, preparation and information boundary

FoundersPreparation(tape) implements ScenarioPreparation, parses exact manifest,
initializes or validates setup, installs/replaces keyed ordinary system, composes
FoundersOfferProvider and existing ReplayPreparation, and delegates finish.
Setup and replay configuration are separate documented atomic boundaries. Replay
failure may leave complete valid setup in memory, but no advance/finalize/save.
Read-only inspection uses validate_existing only; never setup missing domains.

Provider uses current engine-owned authorization/availability and existing
WorkActionHandler/ExternalDispatchActionHandler. Offer only currently preflight-
valid actions; one aggregate work handler, one dispatch handler when offered;
keys/labels sorted per Task22 and exactly one supporting handler per offeredkey.
Per-candidate read-only work preflight may omit currently invalid ValueError
availability/authorization offers; TypeError/KeyError/malformed policy propagates.
No tape inspection/sequence branching or mutation in provider; test before/after.
Large shelter uses CapabilityWorkTarget(shelter,2), unlike modest count1, so
both have distinct existing work identities and are simultaneously offerable.
Resources/tools/progress/labor/IDs/deadlines stay hidden. Dispatch offered only
when contactable and no canonical dispatch yet; inbound food goes to the acting
founder as required by existing actor-bound gateway, not camp inventory.
Qualitative labels: Gather water, Produce food, Build a modest shelter,
Build a larger shelter group, Build storage, Contact the homeland,
Request homeland supplies. No numeric policy or internal IDs in options/prose.

Capture/audit every decision: filtered NPCContextAssembler -> RecordedProposalClient
-> DecisionEngine -> NPCActionResolver -> existing domain handlers/managers.
Do not supply inspector DTOs/rawattrs/IDs/criteria to NPCs. Context remains
ordinary holder-scoped perception/retrieval; no new observation/memory/reasoning
path. Tapes are deterministic untrusted proposal drivers, not evidence a live LLM
chooses strategy. Document engine truth/perception/translation/hidden fields/
memory/inference/context/engine-only boundary in report/operator guide.

## Terminal policy and runner compatibility

Add keyword terminal_conditions: Mapping[str,Callable[[SimulationEngine],bool]]|
None to ScenarioRunner constructor, validated nonempty unique names/callables,
no overriding tick_limit/operator_stop. Existing constructor/default behavior
unchanged; unknown selected names still reject before preparation. Callbacks are
engine-side trusted pure read policies, never LLM-provided strings/expressions.
Canonical selected order failure then success. Check custom predicates after
preparation and before first step (including zero budget/already terminal resume)
and after every complete tick, before checkpoint/final save. Do not evaluate
legacy tick/operator predicates early in ways that change existing stop reasons.
Pre-step operator request retains operator-stop precedence. Aftertick custom
failure -> success -> existing selected legacy conditions/bound/operator logic.
All terminal results use StopReason.TERMINAL_CONDITION with exact selected name.
Custom callback results must be bool. Callback exceptions/nonbool results wrap
RunSimulationError with retained cause and fixed safe outer prose; no final save
or invented simulated failure. Completed ticks are not poisoned merely by a
runner callback failure; existing failed engine-step poisoning is unchanged.

founding_failure: goal_founding FAILED. settlement_success: founding goal COMPLETED,
managed stage SETTLEMENT (or later), four current needs secure pressure0, live
maintained shelter condition>=2/no upkeep shortage, canonical inbound homeland
food1 dispatch ARRIVED to Ada/Bryn. Predicates never set world state or events.
Successnominal end10 (stage7, dispatchcreated6/departed7/arrives9), stallbound5,
failureend13 (deadline evaluated12). Actual focused evidence must confirm these;
report discrepancy and amend plan before changing rules, do not fake outcomes.

## CLI and read-only repository

Existing run PATH behavior preserved. Optional positional scenario plus new
--founders {success,stall,failure}; exactly one selector required. Alias selects
bundled scenario/tape and defaults max_ticks success16/stall5/failure16. Reject
PATH+alias or alias+--proposal-tape before database open. User explicit --max-ticks,
--save-every/--checkpoint-only keep existing per-invocation semantics. Preserve
ordinary --continuous behavior; canonical default commands are bounded.
Explicit canonical scenario PATH+--proposal-tape also composes exact preset.
Canonical run requires a tape; noncanonical paths retain ordinary ReplayPreparation.
A reserved founders_policy on wrong scenario/key rejects, never silently ignored.

Commands: living-world run --founders OUTCOME --database outcome.sqlite3.
Success/failure resume terminally; stall checkpoint at k resumes with --max-ticks
5-k, because bounds count additional ticks. --checkpoint-only avoids unused-tape
finalization; final runs require full tape consumption under Task22 semantics.
Tapes actorlabels alternate ada,bryn startingada. All speech/rationale qualitative.
Successentries: t0speech,t1food,t2water,t3modest,t4storage,t5contact,t6dispatch,
t7–9speech (10total). Stall first3same,t3largeshelter,t4speech(5total).
Failure13speech entries. Every command exits0 for simulated outcomes, existing
configuration/compatibility/persistence/execution exit codes retained.

New living-world inspect [PATH|--founders] --database PATH [--port8000] selects
exact scenario and existing saved world, validates identity/existing setup and
restores vocabulary only, serves create_app(snapshot_engine) at127.0.0.1.
No stepping/replay preparation/missing setup/save or automatic live-database
refresh. Port integer1..65535. Lazy uvicorn import; provide explicit optional
server extra=[uvicorn], fixed actionable error if unavailable, no default runtime
server dependency. Programmatic factory remains create_app(engine) for same-engine
live reads. CLI tests inject/patch serving function, do not hang unit suites.

SQLiteRepository(database_path, *, read_only=False): true opens URI mode=ro,
skips schema creation during load, requires existing snapshot row, rejects save
with RepositorySaveError before writes. Missing/corrupt/mismatched snapshot fails
without file creation; path URI quoting handles spaces/?/#. Default mode behavior
and schema12 unchanged. Test bytes/state unchanged by inspect and all GET routes.

## Verification, boundaries and report

TDD focused typed tests for setup/staging late failure/retry/no-op/partial mismatch,
immutable policy/marker/fingerprint, next IDs/no initial work, keyed registration
replacement/rollback/order, provider purity/options and boundary auditing, deadline/
success/stall/post-work composition ticks, safe terminal callbacks/preexisting
runner compatibility/operator/zero-tick/failed-save semantics, read-only DB and
CLI selector/server failures. Use real source/installed assets and public CLI.

Acceptance: each outcome two fresh runs plus checkpoint/resume at k1,3,4 (before/
after shelter and before storage policy); stallremaining5-k. Compare exact stored
(schema_version,payload) rowid1 byte-for-byte across equivalent finals: repository
JSON already canonical, normalize NO domain fields/events/IDs/order/charges/cursor.
Only RunResult start_tick/resumed may differ outside payload. Physical SQLite
page bytes aren't canonical state. Prove work inputs charged once and replay
cursor/event bijection; already-terminal resume adds no tick/event. Continue
success briefly with appropriate checkpoint-only to demonstrate stable needs/
provisions without new proposals if terminal predicate intentionally bypassed in
a focused programmatic test; never modify saved accepted outcome for evidence.

Inspect each result with actual API and Chrome inspector: needs/work/goals/stage/
dispatch/history evidence and Spatial drill-down; GET only and full saved world
unchanged. Add example039 using public composition and assets (bounded, no server).
Root actual threeCLI commands, all replay comparisons, full make, separate examples,
whitespace, browser, isolated wheel/install/assets/CLI/inspection gates AFTER
independent review; repeat merged required gates before next task. Workers focused
checks only; reviewers scope to task/actual diff, no repeated full gates.

Allowed files exactly:
- new src/living_world/founders/{__init__,model,assets,setup,runtime}.py and
  assets/{founders,definitions,success,stall,failure}.yaml;
- src/living_world/{cli.py,running/runner.py,simulation/simulation_engine.py,
  repositories/sqlite_repository.py}; running/__init__.py for public types only;
- pyproject.toml: founders package-data and optional server extra only;
- tests/test_canonical_founders.py, tests/test_founders_cli.py;
  focused tests/test_{runner_cli,simulation_engine,simulation_scheduler,
  sqlite_repository,world_inspector_browser}.py;
- examples/039_canonical_founders.py;
- docs/canonical_founders.md,docs/world_inspector_ui.md,docs/http_inspection_api.md,
  docs/npc_information_boundary.md,CHANGELOG.md,docs/project_journal.md,docs/backlog.md;
- this plan, matching23_canonical_founders_acceptance-prombt.md and required-report.md.

No other domain manager/system/model/API/inspection/persistence-schema changes.
Amend plan/prompt before concrete necessary expansion; a separate new domain
capability outside canonical composition requires owner approval. Report commands,
counts,warnings, each outcome/terminal ticks, full payload hashes/comparisons,
per-proposal trust audit, inspector evidence, review fixes and honest limitations.

## Fixed manifest field spelling

Top-level founders_policy keys exactly version,area_label,founder_labels,rules,
placements. placements uses publiclabel keys and {geometry,containing_label,
bounds_kind,overlap_policy}; point/bounds geometry follows existing kind/x/y/
width/height DTO with no entity_id. Initial four entries follow label order.
The typed rules dataclass/manifest keys and values are exactly:

```yaml
deadline_tick: 12
need_window_ticks: 3
need_duration_ticks: 3
need_requirement_per_person: 1
need_secure_maximum: 0.0
need_strained_maximum: 0.5
food_per_person_per_tick: 1
water_per_person_per_tick: 1
food_work_quantity: 10
water_work_quantity: 8
required_progress: 1
normal_labor: 1
modest_shelter_count: 1
modest_shelter_timber: 2
large_shelter_count: 2
large_shelter_labor: 3
large_shelter_timber: 4
storage_count: 1
storage_timber: 2
housing_capacity: 2
storage_capacity: 20
maintenance_initial_condition: 3
maintenance_maximum_condition: 3
maintenance_minimum_condition: 2
maintenance_deterioration: 1
maintenance_recovery: 1
maintenance_food_upkeep: 1
storage_spoilage_per_tick: 0
town_population: 3
homeland_capacity: 1
homeland_delay_ticks: 2
homeland_cost_per_unit: 0
homeland_reliability: 1.0
homeland_allowed_imports: [timber]
homeland_allowed_exports: [food]
dispatch_quantity: 1
```

Use the same typed rules as sole source for criteria/targets/policies, not copied
numeric constants. Validate loaded initial scenario population/resources/recipe,
identity labels/definitions and capability capacities against fixed rules before
setup. Subsequent world resource/status changes are dynamic and must not be
compared to initial values. Definition-file/initial-attribute bytes already bind
existing scenario identity; all manifest fields join the same fingerprint.

## Contract-review resolutions — binding public APIs and cardinality

Public exports in founders/__init__.py exactly FoundersOutcome,FoundersAssets,
FoundersRules,FoundersPolicy,FoundersSetupManager,FoundersPreparation,
FoundersConfigurationError,materialize_founders_assets,founders_terminal_conditions,
load_inspection_engine. Avoid eager cycles; runtime imports may be lazy.

- FoundersOutcome StrEnum SUCCESS/STALL/FAILURE values success/stall/failure
 FoundersAssets frozen fields scenario,success,stall,
  failure:Path; tape_for(outcome:FoundersOutcome)->Path is pure.
- materialize_founders_assets()->Iterator[FoundersAssets] is a contextmanager,
  writes only its private tempdirectory, cleans it after run/serve lifetime.
- FoundersRules frozen typed dataclass has exactly appendix rules fields/defaults.
  FoundersPolicy frozen fields version:int,area_label:str,founder_labels:
  tuple[str,...],rules:FoundersRules,placements:tuple[FoundersPlacement,...].
  FoundersPlacement is an internal frozen record of publiclabel, Point|Bounds,
  containing_label:str|None,bounds_kind:BoundsKind|None,overlap_policy:OverlapPolicy.
  FoundersPolicy.from_scenario(scenario:LoadedScenario)->FoundersPolicy is pure;
  to_manifest()->dict[str,object] returns detached normalized data; fingerprint
  property is SHA256 of complete normalized to_manifest canonical JSON with
  sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False, encoded
  strictUTF8. No Unicode normalization. Invalid encoding/type/value becomes fixed
  FoundersConfigurationError invalid_policy with suppressed cause.
- FoundersSetupManager(state:WorldState,definitions:DefinitionManager).
  initialize_or_validate(policy:FoundersPolicy)->None may atomically mutate only
  world on wholly absent setup, otherwise delegates pure validate_existing.
  validate_existing(policy:FoundersPolicy)->None is strictly world-read-only.
  compose(policy:FoundersPolicy)->None atomically attaches pending constructed
  capabilities through existing managers; otherwise no-op.
  restore_resource_vocabulary(policy:FoundersPolicy,registry:
  ResourceDefinitionManager)->None first validates existing setup, then changes
  only the ephemeral registry. Setup/compose may use private shadow helper;
  never deepcopy immutable Events or mutate shared frozen records.
- FoundersPreparation(tape:ProposalTape) implements exact existing prepare/finish;
  rejects absent/wrong tape type as missing_tape/invalid_policy. It mutates world
  only through setup/replay managers and ephemeral keyed ordinary/proposal slots.
  Private FoundersCompositionSystem(state,definitions,policy) binds manager and
  verifies scheduler-supplied state identity before compose; offers provider is
  private FoundersOfferProvider(engine:SimulationEngine,policy:FoundersPolicy).
- founders_terminal_conditions()->Mapping[str,Callable[[SimulationEngine],bool]]
  returns a fresh detached read-only mapping in failure/success order; callbacks
  are pure, engine-side and use existing authoritative managers/state.
- load_inspection_engine(scenario_path:Path,database_path:Path)->SimulationEngine
  loads through read_only repository; requires saved run metadata before any
  engine.load_scenario call, so no initial graph can be created. Validates exact
  run identity and restores ephemeral definition vocabulary. Canonical reserved
  key/policy invokes validate_existing/resource registry restore; noncanonical
  snapshots retain ordinary inspection. No world mutation/initialization/replay
  preparation/step/save. CLI and tests/example use these public composition APIs.

Fixed errors: FoundersConfigurationError codes invalid_policy=>"Invalid founders
policy.",setup_mismatch=>"Founders setup does not match.",missing_tape=>"Founders
run requires a proposal tape."; str is code plus fixed prose, never input payload.
CLI maps setup_mismatch to incompatible-save3, other codes invalid-config2.

Policy IDs: consumption_founders singleton, storage_founders singleton, and
maintenance_founders_ + complete constructed shelter entity ID (no truncation,
collision-free). Per owned constructed shelter, in deterministic entity-ID order:
exactly two housed_in edges (one per configured founder), one maintenance policy
and one composition marker. Multiple shelters multiply upkeep/allocations under
existing rules; canonical success builds one, stall counttwo remains blocked.
Contradictory partial edges/policy/marker reject. Entirely absent attachment may
be pending only at complete boundary tick<=entity.created_tick+1; after the next
ordinary phase it must be complete. Staged composition is allowed to create the
whole missing attachment when due. Never reset an existing maintenance state.

Storage policy is owner-wide aggregate: exactly one storage_founders and one
composition marker, subject the first qualifying constructed storage by entity-ID
order. Later storage needs no second policy/marker; aggregate capacity reads all
owned storage. Missing singleton is pending only immediately after first storage
construction; partial/mismatched singleton records reject. Existing marker/history
and valid dynamic policy state are retained rather than recreated.

Resume exact non-dynamic collections: four need defs/states, two goal defs/states,
seven objective defs/states, one consumption policy/state, one camp stage program/
state, one homeland reference. Reject extra entries in those collections. Storage
and maintenance policy/state keys must be exactly the dynamic canonical set above,
including their valid pending boundaries; no unrelated consequence policies.
Existing valid work/reservation/dispatch/history/entity evolution is allowed by
normal domain validators; don't reset it or compare resources/status to initial.
Initial graph-only setup requires tick0, exact initial entities/relationships/
bindings and no canonical domains/marker/work/dispatch records; otherwise reject.

Runner copies validated terminal mapping before storing it. Keys are nonempty
lowercase snake_case names; reserved legacy names cannot be overridden. Unknown
selected conditions retain existing pre-preparation validation. Mutating caller's
mapping later must not affect run. Callback failures wrap fixed
RunSimulationError("Terminal condition evaluation failed.") with original cause.
Nonbool return wraps TypeError("Terminal condition must return bool.") as cause.
No callback value/name/payload appears in outer prose. Do not poison an otherwise
completed engine tick, mutate goals or save final checkpoint on callback failure.

## Root resolution — population authorization

GoalManager requires nonempty authorization categories for every goal and
objective. Set both goal_growth and objective_founders_population to exactly
("settlement_work",). This existing generic goal category is inert here: no
canonical offered work references the population objective, and existing work
authorization still requires its exact WorkCategory value. Do not add a work
category, growth action, provider offer, or domain manager exception. Preserve
this exact category in setup/resume validation and focused assertions.

## Root resolution — real history accumulation and explicit zero capacity

The first actual founders run exposed an existing goal-evaluation classification
bug, not a missing domain capability: authoritative but still accumulating need
history was classified identically to absent data and deadlocked the unchanged
ACTIVE-only work gateway. Keep WorkActionHandler and all its existing exact-ACTIVE
authorization tests unchanged. Never bypass dependencies, seed synthetic history,
add fake authorization objectives or mutate statuses/outcomes directly.

Expand allowed files solely to src/living_world/goals/evaluation.py,
tests/test_goal_evaluation.py, and docs/adr/ADR-0019-engine-owned-goals.md for this
bounded correction and documentation. No public model/schema/manager changes.
For SustainedNeedCriterion with adequate configured window and a valid need state,
a nonempty history shorter than required duration is UNSATISFIED (pending) only
when its unique matching immutable need_created event anchors exactly that
history: event.tick<=current tick, history ticks equal every integer from event.tick
through state.tick, current is the last history entry, and all assessments have
available numeric pressure and non-UNAVAILABLE level. Missing/duplicate creation
provenance, empty history, missing/ambiguous domain, inadequate configured window,
gaps/truncation/stale history or unavailable assessment remains UNAVAILABLE.
History still reaches SATISFIED only through the existing full-duration criterion.
Use stable safe pending prose and existing filtered source-event provenance;
no lifecycle mutation in criterion evaluation. Existing dependency/terminal/deadline
precedence remains unchanged. Add late-created need and checkpoint/resume coverage.

Canonical camp initial scenario data additionally explicitly declares
housing_capacity=0 and storage_capacity=0. Validate those exact initial integers;
they participate in existing scenario fingerprint. Existing capacity evaluator
stays unchanged: authoritative zero is unsatisfied, absent capacity is unavailable.
Actual constructed owned capabilities add capacity normally. No fake capability.

TDD must prove pending-to-real-window progression, malformed/missing/gapped/stale/
unavailable prefix rejection, active authorization at canonical tick2, unchanged
exact-ACTIVE gateway rules and deadline/terminal behavior. Run focused goal, work
gateway and canonical tests. Report initial deadlock and compatibility change;
retain original 10/5/13 outcome predictions until actual evidence confirms them.

## Root resolution — public dispatch action key versus prose

Real success reaches tick6 through the unchanged gateway but replay wrongly
validates the existing public DISPATCH_ACTION_KEY (dispatch_external_trade) as
conversation prose, mistaking its prefix for an engine record ID. Expand allowed
files solely to src/living_world/replay/system.py and
tests/test_recorded_proposal_tapes.py for this existing integration correction.
Keep the public key, tape key, dispatch handler and NPCInformationBoundary unchanged.
In ReplayProposalSystem, validate option/request action keys as structured action
vocabulary: exactly existing DISPATCH_ACTION_KEY may pass its key-field validation;
all other keys retain current prose validation. Apply the same rule both before
DecisionEngine and before resolver execution. Existing offered-vocabulary matching,
exact one supporting handler, ordering, actor/domain authorization and pure
preflight remain mandatory. Do not exempt target labels, descriptions, rationales,
speech, argument keys/values or any context field: even the public key string
must still reject when embedded there as prohibited prose. Reject other dispatch_*
IDs as keys and all engine identifiers in prose, with no broad prefix allowlist.

TDD: real dispatch key proceeds through ordinary replay+gateway; unknown/unoffered
or internal-ID keys still reject; same string in prose/labels/descriptions/arguments
still rejects without mutation. Canonical success must still demonstrate actual
ARRIVED dispatch. No boundary regex/global cognition/gateway changes.
