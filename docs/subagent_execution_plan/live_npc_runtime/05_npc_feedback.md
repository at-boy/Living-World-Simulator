# Task 5 / LN05 — Tape-independent founders and qualitative feedback

Status: usage checkpoint before review; draft implementation preserved uncommitted.
Root must reconcile the live-validation seam below before further implementation.
Original contract based on reviewed integration1e46cc9; capability remains unapproved.

## October21 checkpoint hold

Worker draft uncovered that FoundersSetupManager.validate_existing rejects destroyed
bound founders and compares their placements to the fixed initial layout. Both
FoundersOfferProvider.offers and shared restoration invoke this strict validation.
This conflicts with the required live relocation/destruction cases. Root verified
setup.py validate_existing and provider call sites. Do not bypass validation or
relax recorded behavior. Before resuming implementation, root must investigate the
exact live setup/restore/domain/offer paths, resolve a live-only validation policy,
and amend this task plus saved prompt BEFORE expanding the allowed file boundary.
No founders/setup.py change is authorized by this checkpoint. Current feedback draft
is incomplete, unreviewed and has not passed root gates. Existing recorded contracts
and hashes remain mandatory. This hold supersedes any decision-complete wording
elsewhere in the original material until root reconciliation is recorded.

## Global Constraints

- Branch `codex/live-npc-runtime` integrates these tasks; base `main` was `d8ea517`. Preserve `milestone/v0.6` at `6bf4c63` and `v0.6.0rc1` at `092715c`; no main integration/tag movement is authorized here.
- Python `>=3.11`; development Python3.13.5. Strict type hints, frozen domain records, manager-owned mutation, system-owned behavior and immutable events.
- No new runtime dependency or Node toolchain. No automatic model download, provider substitution, GPU driver installation, remote administration, player API, demographics or governance.
- Initial live defaults: 30-second request timeout; 512 generated tokens; 40 inference requests per attempt including retries; 20-tick headless bound; eight current perceptions; eight retrieved memories; 16,000-character serialized request ceiling; 1 MiB response limit. Reject booleans/nonpositive values for positive integer limits.
- One decision opportunity per eligible living founder per tick, sorted by scenario label. Existing recorded tapes retain one-entry-per-tick semantics.
- All CLI/browser/agent acceptance attempts archived; temporary unit fixtures explicitly choose temporary roots. No automatic deletion. Restart is a new linked attempt, browser pause/resume remains the current attempt.
- No model calls inside `SimulationEngine.step()`. No HTTP handler mutates an engine. Never persist or publish a poisoned/partial tick.
- Preserve world schema12 writes and schema1–12 reads, existing recorded payloads and public commands. Archive format1 is separate. Any necessary world-schema change requires root reconciliation and explicit contract amendment before code.
- Authenticated loopback-only operator controls; existing `create_app(engine)` and `/world/*` remain read-only. No tokens in URLs, logs, archives or browser persistent storage.
- User approval of this plan and execution method is required before implementation. Writing this plan does not execute its unchecked steps.


## Exact authorizing task text

## LN05: Tape-independent founders composition and qualitative NPC feedback

**Files:**
- Create: `src/living_world/runtime/founders.py`, `src/living_world/runtime/feedback.py`, `tests/test_runtime_founders_feedback.py`.
- Modify: `src/living_world/founders/runtime.py`, `src/living_world/founders/__init__.py`, `src/living_world/cognition/npc_context.py` (optional retriever injection/limit extension only), `src/living_world/cognition/retrieval.py` (explicit policy selection only), `docs/npc_information_boundary.md`.
- Existing founders/replay tests retain their assertions; new cases belong in the new test module. Slug: `npc_feedback`.

**Interfaces:** `FoundersLiveComposition(inputs: RetainedInputs)` implements LN04
ScenarioComposition; shared `prepare_founders_world(engine: SimulationEngine,
scenario: LoadedScenario) -> FoundersPolicy` extracted from FoundersPreparation
without changing recorded composition order. `FoundersFeedback(request_size: Callable[[NPCContext, tuple[ActionOption, ...]], int])`;
`FoundersFeedback.prepare(candidate: SimulationEngine, base: Checkpoint) -> tuple[DecisionInput, ...]`;
`FoundersFeedback.after_tick(candidate: SimulationEngine, outcomes: tuple[JournalEntry, ...]) -> Mapping[str, object]`.
Cursor stores holder/source-change fingerprints and pending observable results, never
raw prompt data inside WorldState. `DecisionInput` is LN05's public runtime value.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_founders_feedback.py tests/test_npc_context.py tests/test_npc_cognition_client.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** `test_only_local_alive_founders_receive_camp_changes`,
  `test_private_cognition_and_hidden_goal_values_never_enter_requests`,
  `test_unchanged_perception_does_not_duplicate_memory_on_restart`,
  `test_actor_result_is_observed_on_next_decision`, `test_context_budget_is_deterministic`.
  ```python
  inputs = feedback.prepare(candidate, base)
  assert tuple(item.actor_label for item in inputs) == ('ada', 'bryn')
  assert hidden_marker not in serialize_decision_request(inputs[0].context, inputs[0].options)
  memories = candidate.memories.memories_for(inputs[0].actor_id)
  assert len(memories) == 2  # fixture contains mandate plus one visible condition
  assert all(m.source_observation_ids for m in memories)
  assert all(m.holder_id == inputs[0].actor_id for m in memories)
  ```
  Pin the exact qualitative templates in test fixtures: communicated mandate,
  local need/work projections and acted/witnessed results; no invented numeric prose.
- [ ] **Step 2 — Observe RED** new feedback tests using managers to create actual
  placements/goals/observations/memories, including another holder's secret records.
- [ ] **Step 3 — Implement** explicitly communicate mandate once; living same-camp
  eligibility via existing spatial manager, owned result feedback and observed camp
  changes only. Use existing typed goal/need/work/external projections and validate
  every final prose through NPCInformationBoundary. Record observations/memories
  through managers. Mandate uses CognitiveSalience(0.8, is_core=True); changed local
  conditions/results use CognitiveSalience(0.6, is_core=False). Never fabricate a
  perception from an unseen dispatch or another NPC's uncommunicated model speech.
- [ ] **Step 4 — Implement bounded retrieval** expose core mandate plus at most eight
  current perceptions and eight distinct holder-owned retrieved memories total
  (deduplicate core/retrieved overlap). Stable salience/newest/tie-ID ordering; prune
  oldest optional entries until injected request_size <=16000 characters; retain required
  identity/mandate/options. If required content alone is too large, fail preparation.
  Fingerprint exact serialized input and base world/driver identity; exclude actor_id,
  operational UUID/time from provider JSON. Capture staged provenance in archive cursor
  for deterministic reconstruction, not extra untyped world attributes.
- [ ] **Step 5 — Observe GREEN** context/information-boundary/perception/feedback suites;
  relocate or destroy an actor between boundaries, mutate a work target legitimately,
  and assert changed safe inputs/offers. Recorded fixtures/hashes stay unchanged.
- [ ] **Step 6 — Review, root gates and commit** `feat: feed observed world changes into NPC decisions`.


## Root-resolved architecture and scope

Based on reviewed integration1e46cc9. LN04 is complete. This task adds model-free,
tape-independent founders composition and safe qualitative feedback. No provider,
broker, proposal execution system, CLI/service/browser or archive-schema changes.
No live strategy success claim. Preserve every recorded canonical row/hash.

### Existing architecture and shared setup

Extract `prepare_founders_world(engine, scenario) -> FoundersPolicy` from the
existing first block of FoundersPreparation.prepare: policy validation, manager
initialize_or_validate, resource vocabulary restoration, then canonical domain
system registration, in exactly their existing order. Recorded prepare calls it
then installs its existing ReplayPreparation unchanged. Export the shared function
from founders/__init__.py. Do not change replay finalization or recorded assertions.

FoundersLiveComposition(inputs:RetainedInputs) validates retained scenario/definition
bytes against their hashes (tape is optional and ignored for live composition),
loads the existing scenario through SnapshotRepository, invokes shared preparation
and does NOT configure replay binding/progress/proposal systems. Restore must not
change the saved world. Use the existing scenario-ordered founders terminal callbacks
with strict bool validation; skip tick_limit/operator_stop sentinel names as LN04.
finalize validates the composition but has no replay tape finalization or extra domain
mutation. Engine authority owns terminal success/failure. No engine retained by
composition/preparation caches after caller discards it: heed LN04 weak-key/value cycle.

### Driver seam amendment carried from LN04

TickDriver.initialize(candidate,archive)->DriverCommit is synchronous/model-free and
runs only before an absent initial checkpoint. TickPreparation.poll supports paused
as well as waiting/ready/provider_error and has activity/error_code properties.
LN06 must consume these exact interfaces; LN05 does not implement a driver.

Add `FoundersFeedback.initialize(candidate:SimulationEngine)->Mapping[str,object]`
to establish initial feedback observations/memories/cursor before inference. It is
model-free. LN06 driver.initialize will return that feedback cursor in DriverCommit.
`prepare(candidate,base)->tuple[DecisionInput,...]` consumes base.feedback_cursor,
records newly observed changes in the detached candidate, and stages next cursor.
`after_tick(candidate,outcomes)->Mapping[str,object]` returns its completed cursor
with pending own results for the NEXT decision. No per-tick IO or world save here.
All three use managers for observation/memory mutation and never mutate base.snapshot.
Do not introduce runtime operational IDs/time/attributes into WorldState.

### Explicit founder eligibility and source allowlist

Use only FoundersPolicy.founder_labels bound through scenario_entity_bindings, sorted
lexicographically. An actor must exist, not be destroyed, have valid NPCIdentity,
and have nonempty placed geometry transitively contained by the bound camp. Walk
placements with a visited set; malformed/missing/cyclic chains are ineligible or
fail closed, never hang. Match WorkActionHandler containment semantics; do not count
an arbitrary newly created NPC as a founder. Camp itself must be live and placed.

Communicate only the explicitly allowlisted `goal_founding` mandate, verifying it is
a SETTLEMENT goal owned by this camp. Never enumerate unrelated goals/objectives or
copy criteria/purpose/deadlines/progress values. Use its NPCGoalInterpretation.
Only camp-owned need definitions and work definitions with settlement_id==camp and
location transitively inside camp are locally visible. Work prose is exclusively
NPCWorkInterpretation (public label/fixed qualitative status), not target internals,
resource arithmetic, reservations or remote dispatch details. Need prose is exclusively
NPCNeedInterpretation. Validate each projection and final prose through
NPCInformationBoundary before it becomes observation/memory/context. A malicious
public label causes classified preparation failure; do not silently sanitize it.

Templates (exact; typed projection values substitute the braces):
- mandate: `You were asked to help the camp: {description}`
- need: `{label}: {description}`
- work: `{label}: {description}`
- own accepted result: `Your proposal was accepted.`
- own rejected result: `Your proposal could not be carried out.`
- own no_action result: `You chose not to propose an action.`

Initial mandate uses CognitiveSalience(0.8,is_core=True); changed local conditions
and own results use (0.6,False). Observation confidence1.0 denotes a permitted
simulation observation, not proof of an NPC inference. Observation subject and
memory.subject_id are camp for mandate/needs, work.location_id for work, actor for
own result. All records are holder-owned and memories reference the actual new
observation ID. Evidence/metadata contains only stable engine provenance: source
kind/id and qualitative hash; never a provider request/attempt UUID, raw speech,
private rationale, unsafe response or model chain-of-thought. Provider JSON receives
only the visible description, never evidence/metadata or provenance IDs.

Witness feedback means changed permitted local need/work projections; journal event
presence alone is NOT proof of perception. No other actor's model speech/decision or
external dispatch result becomes shared knowledge. No numeric prose or hidden goal
thresholds are invented. Actions remain proposals until ordinary gateway execution
in LN06; this task cannot mutate needs/work/goals to satisfy a model statement.

### Cursor, own-result provenance and rollback

Feedback cursor is a closed validated JSON mapping:
`{format:1,mode:'founders_feedback',holders:{actor_label:{sources:{source_kind:{source_id:sha256}}}},pending_results:[{actor_label,source_tick,outcome}]}`.
Source kinds are mandate/need/work; source IDs engine-only. Holder labels must belong
to policy; hashes are lowercase SHA256; source_tick exact nonnegative int; outcome
accepted/rejected/no_action. Sort holder/source mappings and pending results by
(source_tick,actor_label); reject duplicate result keys. Empty feedback cursor is
accepted only by initialize, never silently resets an existing checkpoint cursor.

Fingerprints hash exact qualitative source prose, keyed per holder/kind/source ID.
Communicate mandate once on first eligibility and record each changed projection
once. Repeated same boundary, candidate reconstruction, retry or child restart must
allocate the same observations/memories and cursor. Retain prior source fingerprints
when sources disappear or a founder leaves; absent sources are excluded from current
perceptions while old memories remain historical. A returning actor sees only new
qualitative changes; an A->B->A change is new. No deletion of cognitive history.

`after_tick` accepts only validated action_resolved JournalEntry values from the
just-completed tick, one per staged scheduled actor (post-tick relocation/destruction does not rewrite
the committed actor schedule), source_tick==tick-1, correct
staged base revision, actor label and existing event references. It does not trust
arbitrary journal prose. It stores only actor/source_tick/outcome as pending results;
no need to infer a private action label/reason from request/response. Stable result
identity is (source_tick,actor_label), not operational request UUID. At next prepare,
only its own eligible holder receives each pending result once, then it is consumed.
Ineligible holders' pending results remain pending. after_tick does not create an
observation for an unobserved result or share it with witnesses. Require exact staged
candidate/tick continuity; no after_tick without matching prepare. Feedback cursor
and mutated observations/memories commit atomically via LN04+LN06 DriverCommit.

Candidate preparation may add only allowed observations/memories; no domain state
mutation. Any projection/context/size/consistency failure raises a short safe
RuntimePreparationError code without unsafe exception messages/causes, and leaves
publication/archive unchanged. Partial
candidate mutation is discardable, never persisted on failure. No persistence or
provider retry here. Cache staged primitive cursor data per candidate without a
value->engine strong reference; a fresh feedback object can reconstruct from base.

### DecisionInput, offers, retrieval and complete request budget

Define frozen/slotted DecisionInput in feedback.py with actor_id (engine-only),
actor_label (scenario label), context:NPCContext, options:tuple[ActionOption,...],
handlers:tuple[NPCActionHandler,...] (engine-only gateway bundle), and
input_fingerprint:SHA256. Validate identities/types and tuple immutability. Handler
objects remain ephemeral and are never serialized, persisted or sent over broker IPC.
LN06 DecisionBroker strips ALL fields except filtered context/options before IPC.

Obtain offers from the existing FoundersOfferProvider and EngineWorldInspector in
engine-only preparation, preserving current offer ordering and handler semantics.
Never expose inspector DTOs to contexts; only safe ActionOption values. Fingerprint
canonical serialize_decision_request(context,options) plus base snapshot digest and
base driver/feedback semantic cursors; exclude operational attempt UUID/time/revision.
Keep base_revision separate as staged audit validation context. LN06 binds this
fingerprint to effective source provider configuration and its complete payload
encoder; child revision renumbering must not invalidate an otherwise matching world.

Use existing NPCContextAssembler with an explicitly injected holder-memory retriever
implemented locally in feedback.py; keep default assembler/retriever behavior unchanged.
Select required communicated mandate and at most eight DISTINCT holder-owned Memory
records TOTAL across core_cognition/retrieved_information. Required mandate counts
against eight. Remaining memories sort by descending salience, newest tick, then ID.
Core records go only in core_cognition, noncore only in retrieved_information, no
overlap. No unrelated holder records, beliefs/experiences or global cognition in this
initial fixed policy. At most eight CURRENT permitted perceptions, sorted newest
observation tick then observation ID; absent/old source observations remain memory
history, not current perceptions. Build identity/self_knowledge through assembler;
if necessary assemble with max_perceptions=0 and replace only explicitly selected
perceptions/retrieval tuples, then validate the complete resulting NPCContext again.
No new generic assembler selector or public retrieval policy API is needed.

The injected request_size(context,options) measures canonical JSON of the ENTIRE
provider HTTP body, including escaping/model/system/schema/options (LN06 supplies
its authoritative encoder). Validate an exact nonnegative int result, reject bool.
Prune oldest optional perceptions/memories deterministically until <=16000 chars:
compare tick then stable ID, perception before memory on exact ties. Remove optional
selected entries only; never remove identity, mandate or offered actions. If required
content alone exceeds limit, raise RuntimePreparationError('context_budget_exceeded').
Validate final context/options after pruning; identical source input yields identical
selection/fingerprint. This task tests injected complete-body sizing; actual Ollama
payload builder and independent worker enforcement are LN06.

### Focused tests, documentation and allowed boundary

Add real-manager tests in test_runtime_founders_feedback.py, not weakened existing
founders/replay assertions. Include tape-free init and byte-exact restore, unchanged
recorded setup/order, transitive placement, destroyed/unplaced/nonfounder actors,
unrelated goals/work excluded, private holder secrets and hidden thresholds absent,
exact templates/salience/provenance, same-source dedup/reconstruction/child restart,
A->B->A/local relocation/removal, own accepted/rejected/no_action next-boundary only,
unseen dispatch/other speech not shared, cursor corruption/staged continuity failure,
noncore retrieval/mandate overlap/8+8 bounds, deterministic oldest pruning/required
content failure, provider JSON excluding every engine-only field, and candidate GC.

Allowed worker files ONLY: new runtime/founders.py, runtime/feedback.py,
tests/test_runtime_founders_feedback.py; existing founders/runtime.py and
founders/__init__.py for shared setup extraction/export only;
docs/npc_information_boundary.md for this pathway; this task's05report.
The original optional cognition/npc_context.py and cognition/retrieval.py edits are
unnecessary and NOT authorized by this narrower contract. No runtime/__init__.py
export change (LN06 owns it). Tell root before any scope/architecture expansion.

Required documentation explains engine truth, observable/communicated selection,
projection/transformation, hidden fields, memory provenance, bounded inference
context and engine-only DecisionInput/handlers/cursor. Worker uses focused TDD,
scoped lint/format and whitespace, no subagents/VCS/full gates. Root owns independent
review, corrections, full task and merged make, separate examples, whitespace,
canonical recorded CLI matrices, common-doc updates, commits/push/integration.
