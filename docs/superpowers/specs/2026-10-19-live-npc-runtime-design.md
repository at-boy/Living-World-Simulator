# Live NPC runtime, operator controls and run archives

Date: October 19, 2026
Branch: `codex/live-npc-runtime`, from `main` at `d8ea517`.
Status: owner-approved scope; written design awaiting owner review.
This document is a proposed design, not implemented behavior or an execution plan.

## Purpose and success

Build a persistent simulated world in which NPCs make real model-driven decisions,
respond to changing conditions and eventually interact with players. Player
interference is a design constraint: NPCs cannot depend on a preselected successful
sequence. Administrators must be able to observe the world and its decision process
from a browser, pause/resume it and advance one complete simulation tick.

Retain recorded founding scenarios as supported functionality for demonstrations,
regression tests, replay and diagnosis. Archive every normal CLI/browser simulation
attempt and agent acceptance run for later read-only inspection, including failures
and interruptions. Unit-test worlds remain isolated temporary fixtures.

The user selected installed Ollama as the first real provider and authorized local
execution and Podman testing. llama.cpp support already exists at the cognition
client boundary; this branch must preserve it but need not install it or establish
its live acceptance. No model download, driver replacement or system reconfiguration
is implicit in container-test permission.

Success means actual Ollama decisions reach ordinary world action handlers, NPCs
receive subsequent observable feedback, controlled disturbances change their
available actions/context, browser controls and monitoring work against the running
simulation, and every acceptance attempt can be inspected afterward. A bounded run
may succeed, stall or fail. Model claims never determine engine truth, and a valid
but unsuccessful run must not be concealed or rewritten into a success.

## Scope and alternatives

Use an integrated single-owner runtime coordinating the existing engine, cognition
clients, action gateway, runner and inspector. A separate one-off model demonstration
would not establish this full loop. A new general multiplayer/game-server framework
would expand the work before the loop is proven. Neither is selected.

In scope: explicit recorded/live decision modes; Ollama configuration and preflight;
NPC-safe perception/memory feedback; durable decision recording and replay; automatic
archives; serialized run lifecycle; local browser controls and live/historical views;
repeatable regressions and opt-in real-model acceptance.

Out of scope: player accounts or networked player commands; demographic/governance
milestones; arbitrary scenario authoring; remote multi-admin deployment/RBAC; model
training; installing GPU drivers; guaranteed model success or identical independent
live generations. Do not rename this work to the demographic v0.7 milestone.
Preserve `milestone/v0.6` and `v0.6.0rc1` without moving them.

## Existing seams and constraints

- `running/runner.py:ScenarioRunner` owns current limits, stop/checkpoint behavior.
- `simulation/simulation_engine.py` has one proposal slot between registered domain
  systems and work/consequence/need/goal/stage execution. Tick increments last.
- A failed engine step quarantines that instance; advancing/saving it is forbidden.
  There is no general promise of rolling back arbitrary failed systems in memory.
- `ReplayPreparation` and `ReplayProposalSystem` enforce tape identity, actor order,
  cursor/event consistency and one entry per tick. Live mode must not impersonate
  this binding or silently substitute a client into recorded replay.
- `NPCContextAssembler`, `DecisionEngine`, `NPCActionResolver`, existing work and
  dispatch handlers, observation/memory managers and `FoundersOfferProvider` are
  reusable seams. Founders setup must be separated from tape-specific preparation
  without changing recorded behavior.
- SQLite currently upserts one `world_snapshots(id=1)` row. It does not retain a
  history of checkpoints. Existing inspectors read detached values but their
  separate endpoints do not establish a coherent complete-tick revision.
- Definitions and runtime resource vocabulary are not completely represented by
  the world payload; archives must retain exact reconstruction inputs.

## Ownership, scheduling and live decisions

A typed run controller owns one engine and serializes all mutation. HTTP handlers
submit commands; they do not call managers or step the engine. Existing managers
remain state-mutation owners, systems own simulation behavior, events are immutable.

For live mode, use one bounded decision opportunity per eligible canonical founder
per world tick. Stable scenario-label ordering determines actor order. Only live,
valid NPC identities participate. Founder population remains unchanged by this
branch. This schedule belongs to the runtime, never to an LLM response or wall clock.

At a complete committed boundary, construct an unpublished candidate from the last
checkpoint using existing serialization/load and composition paths. Prepare its
NPC-visible observations and memories deterministically. Assemble each scheduled
actor's bounded context and safe offers against this boundary. Request proposals
sequentially from Ollama, recording each attempt before application. No model call
runs inside `SimulationEngine.step()` or holds the read-inspection publication lock.
No world mutation from another actor, browser request or future player command may
race this preparation. Each response is tied to its actor, slot, input fingerprint
and base world revision.

Once all scheduled proposals are available, the candidate executes exactly one
ordinary engine tick. Its live proposal system consumes only these prepared values
in the existing proposal phase. Domain systems still run in their established order;
offers/authorization are revalidated at execution because conditions may have changed
since the decision input. A stale or unauthorized request is rejected through the
gateway, never forced through to preserve a model's plan. Record each outcome.
Commit candidate world, outcomes and next decision cursor together, then publish the
new immutable revision. Never publish a candidate merely because its model calls
finished or its in-memory tick advanced.

If a tick, validation or persistence operation fails, discard/quarantine the candidate
and retain the last durable published revision. Do not save a partially advanced
engine. Initialization also establishes a valid checkpoint before the first model
request; failures before initialization remain inspectable attempt metadata without
pretending that a world exists.

## NPC information and feedback contract

The engine knows exact resources, work availability/progress, objective criteria,
relationships, placement, internal identities and action results. Its perception
policy selects only facts actually observable or communicated to the particular NPC.
A founding mandate is an explicitly communicated qualitative purpose, not hidden
goal criteria copied into a prompt. For this branch, eligible founders receive the
mandate once at initialization. Direct camp needs and visible camp work/capabilities
are observable only while the founder is alive and placed within that same camp.
Use existing typed qualitative need/work/goal projections, with an explicit allowlist
of that camp's communicated mandate and locally visible records. A founder receives
feedback about their own action and directly witnessed camp changes; external
contact/dispatch results are communicated only to the acting recipient unless a
separate observation establishes sharing. Neither distant dispatch details nor
another NPC's private cognition becomes shared knowledge. Global inspector access
is not an NPC perception mechanism.

Translate permitted changes into qualitative observations through existing
perception boundaries and `ObservationManager`; retain bounded selected experiences
through `MemoryManager` with valid observation provenance. Create a retained memory
once for the initial mandate and each newly observed
qualitative change/action result; unchanged perceptions do not create repeated
memories. Key engine-side observation/provenance selection by holder, completed
revision and source change so candidate reconstruction/restart is idempotent.
Record observable action
results for the next decision boundary, including visible refusal/blockage without
leaking privileged rejection details. Unobserved events do not magically become
knowledge. Memory and an NPC's inference remain interpretations, not engine truth.

`NPCContextAssembler` selects holder-scoped perceptions and bounded retrieval;
`NPCInformationBoundary` validates every visible field. Prompts contain no raw world,
entity/record IDs, exact protected thresholds, arbitrary objects, inspector DTOs or
other NPCs' hidden cognition. Goal/need/work prose must use explicitly approved
qualitative projections. Use deterministic perception translation initially, so the
new real-model dependency is decision making rather than a second model pipeline.

The cognition client receives only filtered context and safe offered actions. Parse
and validate its proposal, validate all visible rationale/speech/arguments again,
and apply only through existing engine gateways. Speech is not a factual observation
or a successful action. Do not automatically turn every model utterance into trusted
memory. Existing cognitive managers and provenance remain authoritative.

## Provider errors, limits and recording

Use existing loopback Ollama transport and configurable model, timeout and generation
limits. Resolve the installed model explicitly during acceptance; do not silently
download, switch provider or replay a canned decision. The model configuration and
sampling settings are immutable for an attempt; changing them starts a child attempt.

A timeout, unavailable server or invalid/unsafe response does not advance the world.
By default there is no automatic network retry. A browser run enters a recoverable
provider-error pause; an operator can inspect it and explicitly retry. A headless
attempt checkpoints its last completed state, reports a nonzero exit and remains
archived. Keep finite request, context, response and per-attempt decision budgets;
reaching a budget stops or pauses with an explicit reason, never an endless loop.
Initial defaults are a 30-second request timeout, 512 generated tokens per response,
40 inference requests per attempt (including retries), and a 20-tick headless bound.
Explicit positive limits may be configured; continuous mode still requires a finite
inference budget. Context selection retains at most eight current perceptions and
eight retrieved memories, with a 16,000-character total serialized request ceiling.
Reduce optional oldest records deterministically before final validation; if required
identity/mandate/action vocabulary alone exceeds the limit, report a preparation
error rather than silently truncating fields. Bound transport response bytes before
JSON parsing (1 MiB default). Record effective limits in the attempt configuration.

Journal request identity/input fingerprint before sending and a validated safe result
before applying it. Preserve safe NPC request context, offered vocabulary, parsed
proposal, short returned explanation, latency and classified failure. Do not request
or store private model chain-of-thought, secrets, authentication headers or raw unsafe
response text. Invalid output retains diagnostic classification and a content digest,
not an unvalidated prompt-visible payload. Distinguish inference request attempts,
valid proposals, gateway resolution, committed world effects and aborted candidates.

A crash can make it impossible to know whether the model server completed a request.
Do not claim exactly-once HTTP inference. Record uncertain requests. Reuse a durable
validated response only if its full actor/slot/input fingerprint still matches; an
explicit retry creates a new request-attempt record. Atomic world/cursor commit and
revalidation prevent duplicate committed work or charges.

## Run archives and compatibility

Reserve a unique attempt directory before scenario/provider execution. It contains
an archive-owned SQLite database and content-addressed, immutable copies of scenario,
definitions, required assets/tapes and effective nonsecret configuration. Also record
software version/revision, schema/format versions, seed, driver mode, model identity
and available model digest, start/end times and launch source. If archive reservation
or required initial persistence fails, report failure before simulation mutation.

A run lineage groups related worlds; each process invocation/restart is a distinct
attempt. Browser pause/resume stays inside the running attempt. Restarting or branching
from an archived checkpoint creates a new attempt with an explicit parent/checkpoint
link. Prior attempts never get overwritten or retroactively turned into a later
successful attempt. This makes every manual/agent run, failed restart and experiment
available for analysis. No automatic retention deletion is introduced.

Operational archive data is separate from `WorldState` and deterministic scenario
`RunMetadata`: timestamps, model settings, request traces, controls and attempt IDs
must not perturb existing recorded world payloads. Give the archive envelope its own
version. Retain existing schema-1–12 world compatibility and reuse the established
world serializer/validator rather than creating an independent serialization format.
Any implementation evidence requiring a world-schema change must be brought back
for an explicit contract amendment, not introduced silently.

The archive-owned database stores the compatible current world row plus append-only
checkpoint history, decision journal, controller/driver identity and progress,
command audit and attempt lifecycle. One SQLite transaction commits world checkpoint,
applied outcomes and driver cursor. Store a completed checkpoint for each advanced
tick in this initial bounded vertical slice, plus initial/pause/final boundaries;
repeated no-change saves may reference an existing checkpoint digest. Historical
entries are immutable. Costs must be measured before scaling to long-lived worlds;
compaction or automatic deletion is later work.

Archive mode/driver binding is required for live continuation and validated together
with saved world, exact composition inputs and cursor. A detached raw world checkpoint
is inspectable but is insufficient to resume a live controller. Never guess missing
identity or silently reinterpret it as recorded mode. Live journal replay uses the
same live schedule, input validation and action gateways with saved decisions, not
fresh model calls. Existing v0.6 proposal tapes keep their existing one-entry-per-tick
runtime and unchanged interpretation.

Preserve the existing recorded CLI commands and explicit `--database` checkpoint
workflow. The archive-owned database is authoritative for analysis; the requested
legacy database path is an atomically replaced compatibility checkpoint mirror.
Use SQLite backup/closed transactional export, never ordinary copy of an open DB.
The archive commits first; if mirroring fails, stop and report exactly which archive
is ahead and which compatibility output failed. Do not promise cross-file atomicity.
Read and validate an existing recorded resume input without overwriting its archive;
create a new attempt, then mirror only fully committed checkpoints. Live resume
selects an archived checkpoint with its complete envelope, not just this legacy file.
CLI diagnostics always identify the attempt and archive even when a run fails.

Incomplete directories and process-crash attempts remain discoverable. Use a per-attempt
exclusive owner lock; an active process must not be relabeled interrupted merely
because a browser reopened. Once no owner exists, discovery marks an unfinished
attempt interrupted and shows its last committed checkpoint and incomplete request
records. No fictitious final world or successful shutdown is manufactured.

## Operator lifecycle and browser interface

States distinguish initialization, paused, running, awaiting-model, pause-requested,
provider-error-paused, stepping, completed, stopped, failed and interrupted. The exact
state-transition table and persisted command/result schemas belong in the approved
implementation plan before code is assigned.

Pause requests stop scheduling new model calls/ticks. An in-flight request can finish
within its timeout; no partial tick is exposed. If candidate advancement has already
started, finish and durably commit that complete tick before acknowledging pause.
Resume continues only a healthy paused controller. Single-step is valid only while
paused, schedules exactly one full world tick (all eligible actors), commits it, then
returns to paused unless an authoritative terminal condition ends the run. At provider
error it advances zero ticks. Stop finalizes the attempt at the last safe boundary.
Repeated step requests must not accidentally advance several ticks.

Controls use a separate local-admin POST API, not mutation added to read-only world
inspection. A single-owner command queue, expected revision and idempotency key
validate lifecycle and serialize requests; duplicate command IDs return their original
result, stale/conflicting commands fail explicitly. Audit accepted/rejected commands
and final effects outside NPC state. Preserve existing GET-only inspection tests.

Bind control serving to loopback initially; require a per-session admin token supplied
outside URLs/logs/archives, same-origin validation and CSRF protection. No permissive
CORS or unauthenticated world mutation route. Render model/player prose as text, never
HTML. Remote exposure and multi-user authorization need a separate design.

Live browser inspection reads an immutable, last-durable complete revision. Expose
revision/tick/freshness and acquire one revision for a multi-panel refresh so panels
cannot accidentally mix ticks. Model progress/control status is separately labeled
operational activity; the UI remains responsive while inference waits. If the user
requests a revision that has expired from live memory, offer its archived checkpoint.

Provide an archive list with mode, scenario, start, parent, status, outcome and last
committed tick; allow a historical checkpoint to open in an inspector instance/view.
Each historical view binds read-only repositories and retained reconstruction inputs,
never a runner. Its revision is fixed and labeled historical, and it has no active
run controls. Inspection must preserve complete world payload and physical DB bytes.
Explicit resume/fork creates another attempt; viewing alone never does.

## Acceptance and task boundaries

Require all of the following, with truthful command/results and recorded artifacts:

1. Existing recorded success/stall/failure commands and exact fresh/resume behavior
   remain supported; archive metadata does not alter recorded world payload hashes.
2. Real Ollama calls produce validated proposals executed by ordinary handlers; show
   actual NPC observations and holder-owned memories informing later safe requests.
3. Repeat controlled disturbances through existing manager/gateway paths at completed
   boundaries. Prove changed observations/offers, stale-action rejection and preserved
   engine authority. Inspect actual live decisions without requiring an invariant
   winning strategy from a nondeterministic model.
4. Replay an archived live attempt from its initial checkpoint without model access;
   compare complete committed world checkpoints, ordered domain events, charges and
   decision outcomes. Test crash/restart before/after response recording and commit.
5. Pause/resume/step under inference latency, repeated clicks, concurrent requests,
   terminal conditions and invalid model responses. Exactly one requested step commits
   exactly one tick; admin requests never write state from an HTTP handler.
6. Discover and read every acceptance archive, including provider/setup failure,
   Ctrl-C, hard process loss and persistence/mirror failure. Do not present poisoned
   state as the last complete world. Verify parent links, exact retained inputs,
   unique attempt IDs and no overwrite of earlier artifacts.
7. Actual browser checks cover live updates, coherent revisions, controls, errors,
   archive selection, historical read-only behavior and untrusted-text rendering.
   Test unauthorized, cross-origin, stale and duplicated control requests.
8. Unit tests use temporary archive roots and deterministic fake transports. Real
   Ollama/container tests are explicit acceptance gates, not mandatory model calls
   during `make`. Run current required repository validation after reviewed tasks.

Implementation should be decomposed by dependency: archive/checkpoint envelope;
controller and safe publication; qualitative cognition feedback; live driver and
journal/replay; CLI/browser controls and archive inspection; real-provider acceptance
and operator documentation. Exact plans/prompts/reports, allowed files, migrations,
phase ordering and focused tests must be decision-complete before each task starts.
This section gives boundaries, not permission to execute these tasks yet.

## Environment evidence and next gate

Read-only October19 checks: Ollama client installed (0.24.0); default loopback API
not reachable from the current execution context. Podman runtime inspection works
outside the sandbox (`runc`). Host enumeration lists AMD Navi10 and NVIDIA GTX1060;
`nvidia-smi` cannot communicate with the driver. NVIDIA CDI tooling was not found
on PATH. No claim of working container GPU inference or model generation is made.
Prefer native installed Ollama for initial acceptance; CPU operation is acceptable
if bounded timings are practical. GPU support is a measured deployment capability,
not a prerequisite for the engine design. Environment changes require scoped work.

Owner approval of this written design is the next gate. After it, create the exact
implementation plan and agree execution method. No product implementation, dependency
installation, container workload, main integration, tag change or v0.7 work is
performed by this design-authoring step. Current authoring scope is this spec plus
CHANGELOG, journal, backlog and continuation status on the isolated branch only.

## Design-authoring verification

Root reconciled two independent narrow read-only investigations and self-reviewed
this spec for scope, missing decisions, contradictions and placeholders. Focused
authoring checks passed for five documents and seventeen local file links; heading
anchors were not checked. `git diff --check` passed. No source, tests or dependencies
changed, so no new full-suite or live-model success is claimed for this design-only
checkpoint. Existing release validation remains historical evidence.
