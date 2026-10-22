# LN07c — Parent-aware deferred setup publication

> Execute as a bounded task under the approved live runtime design and original LN07.
> Root owns architecture/integration; worker TDD then independent SPEC/QUALITY review.

Goal: reserve a linked child before provider IO, discover changed installed-model
identity, then publish immutable effective config AND exact selected world/cursors
before certifying completion. Original Task7 remains incomplete; service/CLI follow.
Spec: docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md.
Base: reviewed integration724d15a. Existing LN07b contract continues to bind all
parentless setup behavior, leases, publication marker, safe failures and IO guards.
No NPC-facing path, HTTP/process/domain/schema/CLI/controller/driver change. No model
downloads, source mutation, repair, initialized-config rewrite or new dependencies.
Python>=3.11, strict types and existing frozen records/canonical serialization.

## Exact worker boundary

Modify src/living_world/archives/catalog.py; optionally assets.py only if needed for
parent-aware setup input validation. Create tests/test_run_archive_fork_setup.py.
Update own07c_fork_setup-report.md. Four allowed worker paths. Root owns other docs/
plan/prompt/VCS. Ask root before widening; no other tests/store/model/lease changes.

## Interfaces and ownership

Add RunCatalog.reserve_fork_setup(attempt_id:str, revision:int|None,
*, requested:AttemptConfig|None=None)->AttemptRef. Extend existing complete_setup
for this intent; ordinary reserve/fork/parentless setup APIs and formats unchanged.

Read parent through same catalog, require parent mode ollama and complete checkpoint.
Validate revision as current fork_point (None selects latest). Call parent.fork_point
ONCE to capture checkpoint plus visible journal horizon in one storage snapshot.
Requested defaults to exact source config. Explicit requested must remain ollama with
same scenario_key,seed,software_revision and all settings outside provider/limits
canonically equal to source (missing/present outside keys are significant). Provider
and limits may change, including removing old digest when explicitly changing model;
existing AttemptConfig and later preflight enforce their validity. Existing ordinary
fork transitions must not be strengthened. Never infer a recorded-to-live transition.

Validate retained source inputs, allocate same lineage, immutable setup intent and
lock under same ownership machinery as parentless setup. Retain EXACT source inputs
under this method's brief child lease before returning. No provider calls. Caller
later owns normal child lease for preflight/final completion. Method returns after
valid child intent+inputs, before any attempt.json/SQLite/setup_complete exists.

Any error after allocation raises ArchiveReservationError(ref), retaining discoverable
identity and immutable linkage; best effort fail_setup(code=setup_failed) if intent
exists and no final publication started. Do not obscure identity on retention fault.
No rollback/deletion of source, child directory or content-addressed objects.

## Exact private setup metadata

setup.json retains current format1 and required fields. Add optional closed `fork`
object; old parentless documents omit it (null/unknown keys rejected). Fields:
- parent: [source_attempt_id, selected_revision] (existing strict parent_pair).
- parent_journal: {sequence,digest} (existing JournalBoundary/parent_boundary).
- checkpoint_sha256: SHA256(canonical({snapshot:{schema_version,payload},
  driver_cursor:<selected>,feedback_cursor:<selected>}).encode()). No operational
  revision/IDs/timestamp in this digest; snapshot payload bytes not normalized.
- source_config_sha256: SHA256(canonical(config_document(source_config)).encode()).
- input_hashes: exact retained name->SHA256 map (existing private_name/digest rules).

Strict closed field/type/UUID/revision/boundary/digest checks; sourceID must differ
from childID; fixed ref layout/catalog root checks remain. Parent lineage validated
at allocation; no path supplied by metadata is followed as a filesystem path.
Intent describes engine-only lineage/history/config, never NPC knowledge.

## Completion and read semantics

Before publishing any final file, current child lease and pending single-use rules
apply. validate_setup_config still binds effective to requested (model normalization/
actual digest allowed only as LN07b). Reopen recorded parent via this catalog:
verify its full config hash, retained hashes, selected checkpoint digest and journal
prefix through exact stored boundary. Source may ADVANCE after reservation; do not
select latest checkpoint or latest horizon again. Missing/changed parent, inputs,
checkpoint or sealed prefix fails closed before final publication. Caller can record
setup_failed while still pending; no silent fallback to another revision.

Ordinary attempt.json and SQLite receive exact intent parent pair+boundary,
reserved_at and effective config. Use existing narrow publication helper. Reopen new
SQLite directly under current lease (ordinary catalog.open rejects until marked),
commit selected snapshot and driver/feedback cursors as child revision0, entries=(),
expected_revision=None. Write existing immutable setup_complete.json ONLY AFTER
commit succeeds and archive closes. No source lifecycle/journal/copied request rows,
no invented tick, no finalization/engine.step or semantic cursor translation.

Partial SQLite publication or committed cp0 before marker remains initializing while
owned; failed/archive_incomplete once unowned. No retry completion/reconfigure/repair.
Preserve existing safe setup failure and malformed metadata classification.

Update shared reservation parity to accept exactly the fork-intent pair+boundary;
parentless still requires None. Discovery of pending/failed/partial child returns
its captured parent pair, never invented revision/tick. Pending retained input
validation still uses setup intent+any present reservation without opening partial
SQLite. Marked child open validates metadata/config/marker, retained hashes and cp0
exact digest (even after child later progresses). Validate those hashes against
intent on read to reject self-consistent manifest+bytes replacement. Discovery/open
remain read-only. Completed child inspection must not require parent availability;
its exact captured hashes and copied cp0 suffice. Completion requires parent; later
recovery already validates source prefix when actually reusing source responses.

## Validation and review focus

- [ ] Focused baseline catalog/assets tests. New API missing gives genuine RED.
- [ ] New linked child discovered before any provider IO; changed-model request has
  no actualdigest yet, complete with normalized model+digest later; inherited source
  request/config/input/world/journal bytes remain unchanged. Same-config path works.
- [ ] Select older revision, then advance source checkpoint AND journal during
  preflight; complete child with exact captured world/cursors and stored seal, not
  latest. Count fork_point exactly once per reservation. RevisionNone chooses once.
- [ ] Reject wrong mode/identity/seed/software/non-provider settings, foreign refs/
  thread/lease, repeated completion, failure+final conflicts, malformed fork metadata,
  parent pair/boundary/reservation disagreement, source config/cursor/input/prefix
  tamper, missing parent, retained child manifest+bytes self-consistent replacement.
- [ ] Inject failure after allocation during retention, before SQLite, empty/schema-
  partial SQLite, before cp0, after successful cp0 before marker. Preserve linkage,
  safe exception ref, no false checkpoint in pending summaries/no repair; completed
  marker/cp0/cursor/hash tampering remains invalid. Real killed owner before completion.
- [ ] Byte-identical read-only pending/failed/completed discovery and source tree;
  completed child opens after parent unavailable and after later child revisions.
- [ ] Existing parentless setup and ordinary reserve/fork tests all remain green.

Focused final: PYTHONPATH=src "$TASK_PY" -m pytest
 tests/test_run_archive_fork_setup.py tests/test_run_archive_catalog.py
 tests/test_run_archive_store.py tests/test_runtime_ollama_driver.py -q.
TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/
.worktrees/task24/.venv/bin/python. Scoped Ruff/Black/whitespace, truthful report
commands/counts/RED-GREEN/limits/selfreview. No VCS/subagents/fullmake/examples/installs
by worker. Root independent review/corrections, task+mergedmake/separateexamples/
whitespace/exact canonical matrices and persisted CLI archives before commits.
