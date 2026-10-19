# 22 — Deterministic recorded proposal tapes

## Status, objective and authority

Authorized after reviewed Task 21, merged as `1ab288b` and checkpointed at
`b055619`. Execute only on `task/22-recorded-proposals` from that reviewed head.
Deliver deterministic untrusted proposal replay through the ordinary filtered
context, `DecisionEngine`, and `NPCActionResolver` path, with durable cursor and
checkpoint recovery. No live model or canonical founders content is required.

Root owns architecture, allowed-file amendments, review, final validation,
commits, pushes and integration. Never modify `main`. Workers do not commit,
push, merge, switch branches or spawn agents.

## Non-goals

No canonical founders setup/content, goal/stage terminal-condition extension,
inspector UI, administration, general transaction framework, live providers,
arbitrary serialized callbacks, or tape authority over domain outcomes.
Task 23 owns canonical initialization and terminal outcome composition.

## Strict tape version 1

Create frozen, slotted `ProposalTapeEntry(sequence: int, actor_label: str,
decision: NPCDecision, rationale: str)` and `ProposalTape(schema_version: int,
scenario_key: str, scenario_fingerprint: str, entries:
tuple[ProposalTapeEntry, ...])` under `src/living_world/replay/model.py`.

The YAML top-level fields are exactly `schema_version`, `scenario_key`,
`scenario_fingerprint`, and `entries`, all required. Version is exactly integer
1, not bool. Scenario fingerprint is the existing
`LoadedScenario.configuration_fingerprint`, a lowercase SHA256 hex string.

Each entry requires exactly `sequence`, `actor_label`, `action`, and
`rationale`, with optional `speech` defaulting to null. Sequence starts at 1
and increments by 1 in input order; reject missing, duplicate or reordered
entries rather than sorting them. Entries are nonempty. `action` is null or
an exact mapping with `key`, `target_label` (nullable string), and `arguments`
(string-to-string mapping, possibly empty). Speech is null or nonempty prose;
speech and action cannot both be null. Rationale is always nonempty prose;
for actions it becomes `ActionRequest.rationale` and must match the entry.

Use existing frozen `NPCDecision`/`ActionRequest` validation. Reject internal
record-ID forms in all visible strings including actor label and arguments.
Reject unknown/missing fields, duplicate YAML keys, nonscalar keys, invalid
shapes, bool-as-int, unsupported versions and malformed decisions. Never echo
input content, source paths, YAML snippets, provider payloads or secrets in
errors. Define `ProposalTapeError(ValueError)` with one of the stable codes:
`invalid_tape`, `scenario_mismatch`, `actor_mismatch`, `offered_action_mismatch`,
`tape_exhausted`, `unused_entries`, `missing_replay_preparation`,
`replay_state_invalid`. Messages contain the code and fixed prose only.

`YAMLProposalTapeLoader.load(path: Path) -> ProposalTape` uses safe YAML and
returns validated records. `ProposalTape.fingerprint` derives SHA256 over UTF8
canonical JSON of normalized tape fields and decision values, including
explicit null speech/action, with `sort_keys=True`, `separators=(",", ":")`,
`ensure_ascii=False`, `allow_nan=False`. Preserve Unicode codepoints; no Unicode
normalization or source path in the digest. Normalized entries have exactly
sequence, actor_label, action (null or key/target_label/arguments), speech
(decision.spoken_text, including explicit null) and rationale; action rationale
is represented once by the outer rationale field. Callers cannot supply a fake
hash.

## Stateless cognition adapter

`RecordedProposalClient(entry: ProposalTapeEntry, *, expected_identity: str)`
implements `NPCCognitionClient`, with `provider_name="recorded_proposals"` and
ordinary `decide(context: NPCContext, actions: tuple[ActionOption, ...]) ->
NPCDecision`. It has no world, holder ID, inspector, provider, handler, tape
header, cursor, or manager reference. It checks the expected entity-name
identity and offered key/target before returning the immutable decision.
Runtime still passes it through `DecisionEngine` before gateway resolution.

Actor label is a scenario label; actor ID is engine-only; expected identity is
the acting entity's current name. Do not substitute labels or IDs for
`NPCContext.identity`. Context is assembled for the engine-bound actor through
`NPCContextAssembler`; a duplicate entity name does not replace that binding.

## Scenario labels and lifecycle

Add `WorldState.scenario_entity_bindings: dict[str, str]`. The existing
`ScenarioRuntimeManager` exclusively creates this initial label-to-entity-ID
map while staging fresh scenario entities. Its public
`entity_bindings() -> Mapping[str, str]` returns a detached read-only mapping.
Validate unique labels/IDs and referenced entity existence. Resume validates
mapping labels against the loaded scenario and definition keys of the initial
entities; entity names may legitimately differ later.

Mapped entity removal is prohibited while bindings persist, preserving history.
Destroyed historical entities may remain mapped. Replay pending actors must
be live, and destruction is prohibited only while the actor appears in the
remaining sequence. Destruction after its final entry is allowed. Compose
scenario/replay lifecycle guards without weakening work, goal, need,
consequence, spatial, dispatch or stage guards. No binding clear/delete API
is introduced. Document the record-retention limitation.

Legacy snapshots with no label map continue ordinary runs. Enabling replay on
such a populated legacy run fails closed; never infer IDs from names/order.
Fresh binding remains atomic and the populated-world guard includes all
persisted domain/replay collections.

## Manager-owned durable replay

Frozen slotted records:

- `ReplayBinding(scenario_key: str, scenario_fingerprint: str,
  tape_fingerprint: str, actor_sequence: tuple[str, ...], configured_tick: int)`;
- `ReplayState(next_index: int, last_attempt_tick: int | None = None)`;
- `ReplayOutcome(str, Enum)`: exactly `ACCEPTED="accepted"`,
  `REJECTED="rejected"`, `NO_ACTION="no_action"`.

Add optional `WorldState.replay_binding` and `replay_state`, either both absent
or both present. `ReplayManager(state: WorldState, events: EventManager)` is the
exclusive mutation boundary with these public methods:

- `configure(binding: ReplayBinding) -> ReplayBinding`;
- `current() -> ReplayState | None`;
- `consume(*, sequence: int, actor_label: str, outcome: ReplayOutcome) -> ReplayState`;
- `validate_loaded_state() -> None`;
- `validate_entity_removal(entity_id: str) -> None`;
- `validate_entity_destruction(entity_id: str) -> None`.

Configuration validates scenario metadata, label bindings, live pending actors,
strict fingerprints and tick, and creates cursor 0. Exact reconfiguration is
idempotent and preserves cursor; changed binding is rejected. It emits no event
(identity binding mirrors existing run identity). Store no decisions,
callbacks, source paths or arbitrary objects in durable replay records.

At most one entry is consumed per tick, in tape sequence order. Rejected
ordinary gateway requests and speech-only decisions count as consumed. Invalid
context/vocabulary/decision or unexpected exceptions do not consume. Runtime
becomes idle after exhaustion; a direct over-consume request raises
`tape_exhausted`. No silent skipped or re-ordered entry is permitted.

For index n>0, `last_attempt_tick == configured_tick+n-1`; cursor 0 requires
None. Ticks are nonnegative integers, excluding bool, not future. At a saved
completed-tick boundary with pending entries,
`world.tick == configured_tick+next_index`; after exhaustion later idle ticks
are allowed. At attempt time `world.tick == configured_tick+next_index` and the
next sequence is `next_index+1`. Distinguish in-phase validation from complete
snapshot validation, so the just-consumed entry is valid before tick increment.
Actor sequence length is the entry count; do not persist a redundant count.

Consume only after complete gateway resolution or validated speech-only
proposal. Prevalidate the next record, record exactly one immutable
`replay_proposal_resolved` event, then store next state. Event subject is the
acting entity ID; attributes are exactly `sequence`, `actor_label`, `outcome`.
No reason, speech, rationale or arguments are persisted in the replay event.
On failure restore prior replay state and remove only newly created transaction
events, following existing manager-owned event rollback patterns. Domain
mutation already performed cannot be saved by the failed engine described below.

## Runtime offers and tick placement

Frozen slotted ephemeral `ReplayActionOffers(actor_id: str,
options: tuple[ActionOption, ...], handlers: tuple[NPCActionHandler, ...])`.
`ReplayOfferProvider` protocol:
`offers(*, actor_id: str, inspector: WorldInspector) -> ReplayActionOffers`.
Default `EmptyReplayOfferProvider` returns an empty bundle. The provider gets
the existing read-only inspection protocol, not the mutable engine. Trusted
engine-authored handler factories may be injected at composition time; provider
construction is pure and cannot determine outcomes. This is a typed authority
boundary, not a claim to sandbox arbitrary Python application code.

Bundle actor ID must match. Option keys are unique and lexically ordered;
target labels are unique and sorted by `(strip().casefold(), original)`.
Exactly one handler must support each offered key; reject missing or duplicate
ownership before mutation. One handler may own several keys. Existing
`WorkActionHandler` and `ExternalDispatchActionHandler` retain their normal
manager authority. Only `NPCActionResolver` determines accepted/rejected;
never persist handler diagnostics as tape output.

`ReplayProposalSystem` receives the tape, manager, offer provider and required
engine-side context/inspection/gateway composition. For the next entry, resolve
actor label through stored bindings, assemble filtered context, build/validate
ordinary offers, ask stateless client through DecisionEngine, validate speech,
rationale and argument prose through state-aware NPCInformationBoundary, resolve
any action through the ordinary gateway, and ask ReplayManager to consume.
Do not auto-inject tape speech into cognition/history.

`SimulationEngine.configure_proposal_system(system: SimulationSystem | None)
-> None` replaces one ephemeral slot and rebuilds the scheduler without
registering duplicate systems:

`ordinary -> proposal(if present) -> work -> consequences -> needs -> goals
-> settlement stages -> tick increment`.

One global tape entry per tick is the v1 actor schedule. No independent
alphabetical actor scheduler, parallel decisions or multiple entries per tick.
Providers/inspectors/handlers never enter the adapter or NPC context. Avoid
import cycles: engine-dependent runtime/inspection imports may be local or
TYPE_CHECKING; do not eagerly import runtime through a pure model package.

## Failed-tick recovery

Guard the entire scheduler tick in `SimulationEngine.step()`. An Exception
escaping ordinary systems, proposal work, any later phase, or tick increment
marks a process-local failed-tick record retaining the original exception,
then re-raises it. Subsequent `step()`, `run()` (including zero steps), and
`save_world()` raise `FailedTickError` with fixed message
`Cannot advance or save a failed tick; reload the last checkpoint.` and original
cause. `run()` validates its step count before entering ticks and delegates
through guarded step. Invalid configuration before ticking, preparation/
finalization errors and repository save errors alone do not poison the engine.

Inspection/direct manager access is still available; do not claim the entire
object is disabled. Direct manager exceptions outside ticks retain existing
transactional retry behavior. No generic in-memory world rollback is added.
A fresh engine from the last complete checkpoint restores cursor and all
uncheckpointed domain changes together; the failure record is not serialized.

## Runner preparation, finalization and CLI

Add `ScenarioPreparation` protocol in running/runner.py:

- `prepare(engine: SimulationEngine, scenario: LoadedScenario) -> None`;
- `finish(engine: SimulationEngine, result: RunResult, *, finalize_proposals: bool) -> None`.

`ScenarioRunner(engine, preparation: ScenarioPreparation | None = None)` loads
scenario, validates terminal names/configuration, then prepares once on new and
resumed runs. Replay-bound saves without matching preparation reject before
any step/finalization/save, including exhausted and zero-tick runs.

`ReplayPreparation(tape: ProposalTape, offer_provider: ReplayOfferProvider |
None = None)` verifies exact scenario/tape binding, preserving configured tick
on resume, and installs/replaces the controlled proposal slot. Preparation is
atomic for replay binding/state and previous proposal slot on failure. Task 23
will compose canonical domain setup before this preparation hook.

`RunConfiguration` gains validated boolean `finalize_proposals=True`.
`RunResult` gains `proposals_finalized: bool | None = None`: None without replay,
False for intermediate checkpoint/operator stop, True after required unused-entry
validation succeeds. A successful stop always saves after finish.

After each completed tick determine terminal/limit/operator stopping before
periodic saving. If stopping, construct result -> finish -> final save. Otherwise
periodic checkpointing proceeds normally. Zero-tick runs also prepare/finish.
Simulation failure skips finish/save; finish failure prevents final save; save
failure occurs only after finish succeeds. Do not persist a terminal/final-limit
tick before unused-entry validation. Earlier checkpoints remain recoverable.

Finish rejects unused entries on terminal/final tick-limit stops when
finalize_proposals is true. Operator stops allow leftovers. Explicit intermediate
bounded runs use finalize_proposals=False, preserving entries for resume.

CLI `living-world run` adds `--proposal-tape PATH` and `--checkpoint-only`;
the latter sets finalize_proposals=False. Default tape preparation offers no
actions, allowing speech-only runs. Canonical domain offers belong in Task 23.
Print proposals_finalized only for replay runs; ordinary CLI output remains
compatible. Use safe tape errors in existing invalid/incompatible-run handling,
without payloads or secrets. No goal/stage terminal strings added in Task 22.

## Persistence, inspection and NPC boundary

SQLite schema 12 persists scenario label bindings, ReplayBinding and ReplayState
in the same atomic snapshot as domain effects. Schemas 1–11 load empty bindings
and absent replay records; write forward without inventing labels/cursors.
Validate strict fields/discriminators/order, references, fingerprints, cursor/tick
relations and live pending actors after prerequisite records reconstruct.
Failed save leaves the previous snapshot intact. Serialization does not persist
runtime objects. New/resumed runs must converge on cursor, state and events.

Expose detached engine-only `WorldInspector.replay() -> Mapping[str, object]`
(empty mapping if absent), GET-only `/world/replay`, and summary
`replay_configured`. Include bindings/current cursor needed for operator diagnosis.
Protect replay fingerprints, internal binding values (not public label keys),
and replay numeric fields in NPCInformationBoundary. No auto context injection.

## Required tests and example

Add typed tests/test_recorded_proposal_tapes.py. Tests must cover strict loading
and safe diagnostics; sequence, shape and fingerprint mismatches; context
isolation and identity translation; option/handler ownership; accepted,
rejected and speech-only consumption; invalid decision nonconsumption; duplicate
attempt/exhaustion/idle behavior; exact scheduler placement; failed-tick
step/run/save refusal with retained cause and checkpoint recovery; atomic
prepare/idempotence; persisted label bindings and actor lifecycle; schema1–11
defaults/write-forward, corrupt schema12 and failed-save preservation; identical
fresh replay and resumed replay at multiple ticks; zero-tick/operator-stop/
checkpoint-only/unused-entry finalization, including terminal checkpoint ordering;
CLI no-live-model path; detached GET-only inspection and NPC boundary rejection.
Use independent literal expected outcomes; keep corruption fixtures explicitly
typed/cast. Add example038 showing normal context/gateway replay and resume.

TDD and focused tests during implementation. Final focused matrix includes new
tape tests and affected runner/scenario/engine/scheduler/persistence/spatial/API/
NPC-boundary tests. Worker runs focused matrix, lint/format and diff checks and
reports evidence. Root runs make, separate make examples and git diff --check
once independent review/corrections are ready and again on merged milestone.
This validation ownership supersedes repeated worker full runs in the old prompt.

## Allowed files and documentation

- src/living_world/replay/{__init__,model,loader,client,manager,system,runtime}.py
- src/living_world/state/world_state.py
- src/living_world/scenarios/runtime.py
- src/living_world/simulation/simulation_engine.py
- src/living_world/managers/entity_manager.py
- src/living_world/repositories/sqlite_repository.py
- src/living_world/running/{runner,__init__}.py
- src/living_world/cli.py
- src/living_world/api/{inspection,server}.py
- src/living_world/cognition/information_boundary.py
- tests/test_recorded_proposal_tapes.py
- focused tests/test_{runner_cli,scenario_run_contract,simulation_engine,
  simulation_scheduler,sqlite_repository,spatial_domain,inspection_api,
  npc_information_boundary}.py changes
- tests/test_settlement_stages.py: only existing current-schema expectations
  updated from 11 to 12; no stage behavior changes
- examples/038_recorded_proposal_tapes.py
- docs/adr/ADR-0025-deterministic-recorded-proposals.md
- CHANGELOG.md; docs/{core_model,engine_glossary,npc_information_boundary,
  project_journal,backlog}.md
- this plan, saved 22_recorded_proposal_tapes-prombt.md and required
  22_recorded_proposal_tapes-report.md

ADR-0025 must document the accepted tape/phase/cursor/identity/lifecycle/recovery
contracts before implementation. The report records behavior, files, red/green
checks, review corrections, counts, warnings and limitations, without successful
logs. Amend this plan and saved prompt before any boundary expansion.

## Execution amendment — 2026-10-14

Permit only the current-schema assertions in existing settlement-stage tests
to move from 11 to 12. Keep all stage behavior/migration checks intact. Direct
engine advance/save, as well as the runner, reject replay-bound state without
its prepared controlled proposal system, including exhausted tapes; this is
a safe missing_replay_preparation error, not failed-tick poisoning. Raw
repository serialization remains independent for valid snapshot tests.

## Resume review clarification — 2026-10-14

For a present ReplayBinding, loaded/complete-snapshot validation also requires
a bijection between next_index and immutable replay_proposal_resolved events:
exactly sequences1..next_index, no duplicates/gaps/extra resolutions, tick
configured_tick+sequence-1, actor_label matching actor_sequence, subject matching
the stored label binding, and exactly the defined three event attributes with
a valid closed outcome. Reject missing, mismatched or future resolution evidence
with replay_state_invalid. Apply this check at loaded/complete boundaries, not
while prevalidating the next state before its event is created. No binding means
legacy replay-like history is not used to invent progress. Configuration must
reject contradictory reserved replay resolution history. Add corruption tests
for each invariant plus valid checkpoint/resume. This closes the worker's
explicitly recorded cursor/history question within the existing allowed files.

## Root validation amendment — work-phase retry test

The root full gate found one old test retries `engine.step()` after an injected
failed tick. That conflicts with Task22's explicit checkpoint-reload requirement.
Extend allowed files only to
`tests/test_work_execution.py::test_failed_construction_phase_preserves_next_entity_relationship_and_event_ids`.
Preserve its injected failure, rollback, next-ID and successful completion
assertions, but exercise `WorkExecutionSystem.step(engine.state)` directly for
the phase retry. This tests the existing phase-local rollback contract without
claiming that a poisoned whole engine is reusable. No other work behavior test
or production work code change is authorized. Existing replay tests separately
prove failed engine step/run/save refusal and checkpoint recovery.
