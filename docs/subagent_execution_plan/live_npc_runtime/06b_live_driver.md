# LN06b — Bounded Ollama decisions and exact offline journal replay

Status: owner-authorized remainder of original LN06, after reviewed LN06a
integration9875d5e. This exact contract resolves producer/consumer seams; it does
not authorize public CLI/service/browser work (LN07/LN08). LN06 is complete only
after this stage and aggregate acceptance. No source implementation claimed yet.

## Goal, architecture and constraints

Use the existing Ollama cognition client through one bounded owned process per
request. Prepare filtered inputs outside engine.step, execute safe proposals in
the existing proposal slot through ordinary gateways, commit complete world/cursors/
outcomes together, and replay those complete ticks without network access.

Python>=3.11, strict typing, dataclasses/Protocols, standard library only. Preserve
world schema12 writes/1–12 reads, archive format1 and exact recorded worlds. Managers
mutate, systems behave, events immutable. No raw WorldState, IDs, handlers, inspector
or runtime objects in model input/worker context. No raw invalid output/CoT in any
archive/log/result file. No model download, provider substitution, GPU install,
player API, main/tag/milestone changes or deletion of branches/worktrees.

Defaults: timeout30seconds,512output tokens,1MiB response,temperature0,seed resolved
from scenario,40actual requests per attempt; fixed8current perceptions/8total memories
including mandate/16000characters of COMPLETE serialized HTTP body. max_ticks is
controller-owned (headless default20 later LN07). Reject bool/nonfinite/nonpositive
limits; do not silently accept overrides of fixed feedback caps.

## Exact file boundary and interfaces

Create only:
- src/living_world/runtime/broker.py
- src/living_world/runtime/ollama_driver.py
- src/living_world/runtime/journal_replay.py
- tests/test_runtime_broker.py
- tests/test_runtime_ollama_driver.py
- tests/test_runtime_journal_replay.py

Modify only:
- src/living_world/cognition/ollama_cognition_client.py
- src/living_world/perception/local_llm_http.py
- src/living_world/runtime/__init__.py
- tests/test_ollama_cognition_client.py
- tests/test_local_llm_http.py
- docs/npc_information_boundary.md (runtime/provider flow only)
- this task's -report.md

Root owns this plan, -prombt.md, common changelog/journal/backlog/index/continuation
and VCS. No controller/feedback/founders/archive/schema/dependency changes. Escalate a
producer defect to root with evidence BEFORE expanding any file boundary.

Public types in broker.py, exported from runtime:
- frozen ProviderConfig(model:str,base_url:str='http://127.0.0.1:11434',
  timeout_seconds:float=30.0,max_output_tokens:int=512,
  max_response_bytes:int=1048576,temperature:float=0.0,seed:int|None=None,
  model_digest:str|None=None). model_digest is declared/preflight provenance only;
  no model lookup or download in this task. Nonempty string if present.
- frozen BrokerResult(job_id:str,decision:NPCDecision|None,error_code:str|None,
  response_digest:str|None,elapsed_seconds:float). Exactly one of decision/error;
  finite nonnegative elapsed, optional lowercaseSHA256 digest, nonempty jobID.
  error vocabulary timeout/transport/http_error/invalid_response/oversized_response/
  unsafe_response/cancelled/worker_failed/uncertain (same archive vocabulary).
- DecisionBroker.start(job_id:str,config:ProviderConfig,decision_input:DecisionInput)
  ->None; poll(job_id:str)->BrokerResult|None; close()->None.
- provider_config(config:AttemptConfig)->ProviderConfig resolves archive settings
  including omitted seed using config.seed. Requires explicit model; validates
  effective limits/driver_format as below. Export for LN07 construction.

In ollama_driver.py:
- effective_config_fingerprint(config:AttemptConfig)->str (export for LN07).
- OllamaTickDriver(config:ProviderConfig,feedback:FoundersFeedback,
  broker:DecisionBroker), implementing existing TickDriver initialize/prepare.
In journal_replay.py:
- JournalReplayComposition(source:AttemptArchive,composition:FoundersLiveComposition,
  *,source_point:ForkPoint|None=None), read-only source_point:ForkPoint property,
  implements ScenarioComposition; initialize restores captured source checkpoint0
  through composition.restore, restore/terminal/finalize delegate live behavior.
- JournalReplayDriver(source:AttemptArchive,feedback:FoundersFeedback,
  *,source_point:ForkPoint|None=None), implementing
  TickDriver with zero provider/broker calls. Export both for LN07.
Use existing DriverCommit/TickPreparation protocols unchanged.

## Provider payload and safe HTTP

OllamaCognitionClient adds optional max_output_tokens=512,temperature=0.0,seed=None
constructor keywords and build_payload(context:NPCContext,
 actions:tuple[ActionOption,...])->dict[str,object]. decide uses build_payload;
stream=false,think=false, existing SYSTEM_INSTRUCTIONS/RESPONSE_SCHEMA remain exact.
options includes num_predict,temperature and seed only when resolved/non-None.
Preserve existing client/transport/llama.cpp callers and error superclass behavior.
Reject invalid numeric values including infinite timeout.

The complete body encoding is json.dumps(payload,sort_keys=True,separators=(',',':'),
ensure_ascii=True,allow_nan=False), encodedUTF8. Count characters of that exact body,
not inner NPC JSON. Driver's injected FoundersFeedback request_size, driver preflight
and worker independently use build_payload + this encoding and enforce<=16000.
Required identity/mandate/options cannot be dropped. Feedback owns optional pruning;
if any actor still cannot fit, fail before the first network request of that tick.

UrllibJsonHttpTransport(max_response_bytes:int=1048576) uses bounded read(max+1),
rejects overflow before decoding, rejects invalidUTF8/nonobject/malformedJSON safely.
Expose read-only last_response_digest:str|None, reset per call, SHA256 of complete
bounded raw response bytes (including invalidJSON); never hash a truncated overflow
as complete. HTTPError body must not be read/unbounded or echoed. Add safe error code
attribute to LocalLLMHttpError, optional constructor keyword preserving old messages.
No raw server/exception body in classified results. Timeout/connection/HTTP/encoding
errors map to fixed archive codes; invalid UTF8/JSON ->invalid_response.

Validate credential-free loopback http URL, including malformed port/IPv6; reject
userinfo, params, query, fragment, remote hosts, bad/control/whitespace authority.
BaseURL path only '' or '/'. Actual transport endpoint may retain existing llama.cpp
paths, but must validate origin itself. Allow only127.0.0.1,::1,localhost; use private
opener with proxies disabled and redirects rejected, so redirects cannot escape the
origin. Preserve normal hostname resolution semantics for localhost; no new DNS API.
No monkeypatch-dependent production safety. Test actual local HTTP redirect, huge body,
invalidUTF8, timeout, HTTP error and proxy environment, plus normal old adapters.

## Broker ownership, deadline and IPC

One active job maximum. Spawn fresh multiprocessing.get_context('spawn') Process.
start strips DecisionInput to serialized safe context/options; only provider config,
filtered NPCContext/options JSON and owned result path cross spawn boundary. Do not
pickle DecisionInput/handlers/engine/inspector/actor_id, fingerprints or journal IDs.
Use existing serialized request schema to reconstruct safe context/options in worker.

Use private owned temporary directory + atomic bounded JSON result file as IPC.
Worker writes safe parsed decision/fixed error/digest only (no raw model output),
parent reads ONLY after process exit. Never use poll-then-blocking framed pipe reads.
Frame limit8*max_response_bytes+4096 accounts for safe JSON escaping; reject excess or
malformed result, reparse decision against exact offered actions in parent. job_id
stays parent-side; bind response to the owned process/generation, never untrustedID.

start establishes monotonic wall deadline including process startup. poll is bounded,
returnsNone while waiting; results first observed after deadline are timeout even if
worker finished just before it. On deadline/close terminate, boundedjoin then kill+
boundedjoin if needed; reap only owned worker, never Ollama server/other processes.
Cleanup owned IPC files on every path. Result IDs cannot be reused, overlapping start
rejects; unknown pollID rejects. close is idempotent cleanup and RESTARTABLE for later
jobs because RunController closes each preparation after every successful tick.
No persistent process/queue/thread between jobs. Tests use real spawn + loopbackHTTP,
including hung worker/large result/process cleanup; timing assertions allow CI margin.

## Immutable effective configuration and semantic cursor

provider_config reads immutable AttemptConfig.settings.provider with ProviderConfig
defaults; omitted seed->AttemptConfig.seed; no unrecorded constructor choice. Driver
constructor config must equal resolved archive provider before inference. mode must
be ollama; replay reads source's ollama config. driver_format omitted means1, otherwise
must1. Limits: max_requests omitted40, positive; max_perceptions8/max_memories8/
max_request_characters16000 only; max_ticks/save_every remain caller-owned.

Effective config fingerprint = SHA256 of canonical closed object:
{format:1,scenario_key,seed,software_revision,provider:{all resolved ProviderConfig
fields including model_digest:null},feedback:{max_perceptions:8,max_memories:8,
max_request_characters:16000}}. Canonical JSON uses archives.model.canonical.
Exclude launch_source, mode, attempt/lineage IDs, parent/revision/time, operational
max_ticks/max_requests/save_every. Provider changes (including declared digest) or
software/scenario/seed changes invalidate reuse. No claims of bitwise live determinism.

Driver cursor exact closed document:
{format:1,mode:'live',schedule_labels:[canonical founder labels sorted],
 binding_fingerprint:<scenario manager fingerprint>,config_fingerprint:<above>,
 next_tick:<complete world tick>,next_slot:0}.
Use candidate.state.run_metadata.configuration_fingerprint, verified against the
retained scenario; no new scenario hashing algorithm.
No request count/attemptID/timestamp/revision in semantic cursor. Request count is
number of request_started rows in CURRENT attempt, including failed/uncertain/retry;
response_reused imports count zero. This cursor is opaque semantic input to LN05.

initialize is synchronous/model-free: verify config/binding, feedback.initialize,
return initial cursor/feedback. prepare verifies current world/cursor/binding/tick,
then feedback.prepare all actors (already sorted/eligible) and full payload limits.
A config mismatch in base cursor is allowed ONLY on sealed linked childrevision0
with exact source snapshot/cursors and constructor matching child's new config;
this is explicit fork config change, never in-place mutation. New cursor uses child
config after successful tick; changed config never reuses prior response.

Journal input_fingerprint = SHA256(canonical({feedback_input:<DecisionInput.input_fingerprint>,
 payload:<complete build_payload object>})). Journal request is parsed inner
serialize_decision_request only. config_fingerprint is effective config above.
No base operational revision in semantic fingerprint: selected parent cursor/world
copied to childrevision0 must yield same input identity.

## Live preparation, proposal phase and audit

Each poll stages at most one active request. Before broker.start, atomically record
request_started (new opaque requestID, base revision,source_tick,actor_label,
input/config fingerprints, filtered request). Count budget before sending; budget
exhaustion ->provider_error with safe request_budget_exhausted, no inventedstart.
If spawn fails after start, settle response_failed(worker_failed), pause. Parent
revalidates safe decision via DecisionEngine using staged context/options and through
current NPCInformationBoundary.validate_conversation_prose for every returned prose
field (speech/action/rationale/argument keys+values) BEFORE response_validated.
Persist only safe decision, optional digest/elapsed. Rejected unsafe/invalid output
records response_failed with fixed code/digest, never raw response.
First provider failure pauses; no auto-retry/fallback. RunController Retry alone
permits a new prepare after error, increments actual budget on new start. Pause
accounts bounded current call but launches no further actor; retain validated rows,
return paused with no world tick. close cancels/reaps active job and settles it as
response_failed(cancelled) if needed; append candidate_aborted for discarded prepared
candidate, once, not for successfully finished tick. No archive close in driver.

install registers one private SimulationSystem via configure_proposal_system.
System step runs after domain registration, before work/consequence/needs/goals/stages,
with zero HTTP. For each STAGED actor label sorted, validate staged safe decision via
DecisionEngine/prepared local client against staged offered vocabulary. Revalidate
returned prose against current boundary. For actual action fetch FRESH
FoundersLiveOfferProvider options/handlers and use NPCActionResolver through
engine.resolve_npc_action. Changed offers reject gracefully, not provider error.
If actor no longer eligible/living/in camp, use empty current offers/handlers so an
action rejects through gateway; no substitute actor. Structural malformed world still
fails closed. No-action iff decision.action_requestNone, even if actor became absent.
Capture event IDs newly added by this actor gateway only, in insertion order; no
speech auto-broadcast, conversation or shared memory. Prepared handlers never cross IO.

finish_tick only after exactly+1tick returns DriverCommit with next complete semantic
cursor, feedback.after_tick(candidate,outcomes), and action_resolved for each staged
slot. Entries reference matching local validated requestID/base/actor/tick; outcomes
accepted/rejected/no_action and eventrefs. Atomic checkpoint owns all outcomes; no
speculative action row before commit. Controller failure keeps prior durable world.
Driver caches must not retain discarded engines/handlers; GC regression required.

## Response recovery and explicit retry

Reuse current-attempt validated/imported request only if same local base slot AND
full regenerated input/config fingerprints/request/decision. Deterministic preference:
response referenced by matching committed action, otherwise latest validated row.
Never pending/failed as validated. Already committed source tick is not re-executed.

For child reuse, derive RunCatalog from current archive's established layout. Follow
parent attempt IDs/revisions through catalog only, with cycle guard, not arbitrary
source paths. Verify selected parent checkpoint exact snapshot/cursors, sealed prefix
journal_boundary(through_sequence=seal.sequence)==seal, and source record/decision/
input/config identity before import. Ignore source appends beyond seal. Follow chains
only while selected world/cursors remain exact and same config. Legacy unsealed parent
is readable but reuse is declined, never guess a horizon. Tampered/missing seals fail
closed before any HTTP. Import response_reused with new LOCAL requestID and verified
source attempt/request/boundary plus safe provenance; no request_started/no HTTPcount.

If matching last request is pending/failed in current or verified parent history,
first preparation after process restart must report provider_error (uncertain or
recorded failure) WITHOUT resending. A driver-local latch permits retry on the next
prepare for that same base/input; controller only calls it after explicit Retry.
A newly completed failure also arms this latch, so one explicit Retry suffices.
If budget exhausted, Retry stays paused without new start. A cold restart clears the
latch and again requires explicit Retry. Mismatching old inputs/config do not block
fresh intended requests. Validated earlier actors remain reusable on retries/pauses.
No marker granting automatic retry may be persisted in semantic world/cursors.

## Offline exact replay

Capture source.fork_point() and journal prefix at construction (or verify the supplied
source_point against source.checkpoint(point.revision) and its exact sealed prefix).
Composition exposes its captured point; LN07 must pass that same point to driver,
so a concurrent source append between their constructors cannot choose two horizons.
Both only load checkpoints through point.checkpoint.revision and journal through its
boundary; default standalone construction remains supported. Test appending between
constructors with one shared source_point: replay must stop at the captured horizon.
Source readonly,
modeollama, config resolved as above. Later source appends excluded. Composition
initialize restores exact sourcecheckpoint0 (which may already contain tickN, memories,
work and pending feedback from a parent), never a fresh WorldState. Driver initialize
returns sourcecheckpoint0 cursors without reinitializing feedback.

For each source advancing checkpoint, regenerate feedback/options and completepayload
with SOURCE config/semantic cursor (not replay mode/UUID/revision), compare every
staged fingerprint/request, require exactly one checkpoint-owned action row per staged
actor and referenced validated/imported response. Failed inference rows remain audit
history, not turns. Apply safe decisions through same private live proposal system and
fresh gateways; require outcomes/eventrefs match, then compare ENTIRE snapshot payload,
events and work charges with source complete checkpoint. Feedback/driver cursors also
match. Any divergence/missing record aborts before publication; no normalization.

Replay target archive modejournal_replay must use same scenario/seed and required
settings.source_config_fingerprint equal source effective fingerprint. Its own provider
settings/operational mode cannot redefine source encoder. Record local response_reused
for source validated decisions with captured source boundary and local base revision;
then local checkpoint-owned action rows. No request_started/network. Terminal/stop
same-tick source checkpoints may be skipped only after proving identical complete
world/cursors and no action rows; divergent same-tick commits fail closed. Never add
an extra tick at end. JournalReplayComposition.terminal_condition returns the actual
live terminal if present, otherwise journal_replay_complete when the captured last
source tick is reached, including a zero-tick source. No inferred extra model turn.
Retained input hashes must match source inputs before replay.

## Required TDD, evidence and completion

Focused baseline old HTTP/Ollama/controller/feedback/archive regressions first.
Add genuine RED then GREEN per vertical slice, smallest named correction first.
Focused final command with PYTHONPATH=src "$TASK_PY" -m pytest:
 tests/test_runtime_ollama_driver.py tests/test_runtime_journal_replay.py
 tests/test_runtime_broker.py tests/test_ollama_cognition_client.py
 tests/test_local_llm_http.py tests/test_runtime_founders_feedback.py -q.

Required regressions: real bounded spawn/stubHTTP timeout/hugebody/redirect/UTF8/cleanup;
complete-body escaping boundary/required budget failure before calls; two actor sort/
real gateway effect/no HTTP inside step; speech-only; target invalidated in domain
phase; pause mid-secondrequest/reuse first; retry/default40 count/importzero; unsafe
output; pending kill/validated-beforekill/commit-beforepublication recovery; selected
parent seal/tamper/postforkappend/recursivecontinuity/configchange; no duplicate effects
or work charges; exact offline replay every world/event/charge and source config
mismatch, child initialworldtick>0; GC/no discarded-engine retention. Existing recorded
matrix remains exact; no real model in make, actualOllama acceptance belongs LN09.

Worker updates report commands/counts/warnings, boundaries/selfreview/limitations,
RED/GREEN evidence and concerns. No VCS, subagents, fullmake/examples/dependency work.
Root independent SPEC/QUALITY review -> bounded worker corrections/rereview -> task
make,separateexamples,whitespace,exactcanonicalmatrix -> delivery -> merged gates ->
integration/push. Preserve owner-local master-plan patch and current SDD evidence.
