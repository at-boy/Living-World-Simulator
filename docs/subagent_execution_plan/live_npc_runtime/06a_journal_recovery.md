# Task LN06a — Recovery journal integrity (bounded LN06 producer stage)

Status: owner-authorized bounded stage of LN06, from reviewed integrationf13641e. Original owner-approved LN06 includes durable
request/response recording, safe restart reuse, atomic actions and exact replay.
LN06a closes its storage seams; LN06b implements provider/broker/live/replay drivers.
LN06 is NOT complete until both stages and aggregate acceptance are reviewed.
No master-plan/owner-local edit, milestone, main or tag changes.

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



## Objective and non-goals

Expose truthful committed journal linkage and seal the source journal prefix selected
when forking a checkpoint. Support safe cross-attempt validated-response provenance
without pretending reuse is a new HTTP request. No provider calls, runtime drivers,
feedback changes, entrypoints, browser, world schema or dependency changes. Preserve
world schema12 writes/1–12 reads, exact recorded rows and archive format1. New metadata
is additive/optional for reading legacy valid archives. Newly forbidden standalone
or unvalidated action outcomes are invalid archives, not backward-compatible execution.

## Exact interfaces and ownership

Add frozen validated records in archives/model.py and export through archives package:
- JournalRecord(sequence:int,entry:JournalEntry,checkpoint_revision:int|None,
  revision_context:int|None). Sequence positive; nullable revisions nonnegative.
- JournalBoundary(sequence:int,digest:str). Sequence nonnegative; digest lowercaseSHA256.
- ForkPoint(checkpoint:Checkpoint,journal_boundary:JournalBoundary).

AttemptArchive additions:
- journal_records(*,through_sequence:int|None=None)->tuple[JournalRecord,...]
- journal_boundary(*,through_sequence:int|None=None)->JournalBoundary
- fork_point(revision:int|None=None)->ForkPoint
- read-only parent_journal_boundary:JournalBoundary|None property
- initialize accepts keyword parent_journal_boundary:JournalBoundary|None=None in
  addition to existing parent argument. A boundary requires a parent pair.
Existing entries() return/API and parent:(attempt_id,revision) tuple API unchanged.
AttemptConfig contents/fingerprints unchanged. No new SQL table/column/schema version.

The journal boundary hashes UTF8 canonical JSON array of records, each with closed
keys sequence,kind,payload,checkpoint_revision,revision_context; payload normalized
through existing canonical helpers. This includes all audit/proposal/control records.
Empty prefix is sequence0 and SHA256(canonical([])); preserve gaps if any, never
renumber. through_sequence0 returns empty; explicit nonzero boundary must identify
an existing sequence and cannot exceed latest. None means all currently visible rows.
One call reads/validates within one existing _connect readonly transaction. Results
are deeply immutable and input type errors reject bool/negative/invalid bounds.

fork_point reads selected/latest checkpoint AND its visible journal prefix/boundary
within ONE readonly SQLite snapshot (existing _connect uses BEGIN). No source mutation,
lease acquisition or new locks. Missing revision/no checkpoint fails safely. Reads
must not write files, metadata, timestamps or SQLite sidecars. Preserve existing
archive ownership and validation; no public SQLite connection escape hatch.

## Sealed parent metadata and catalog

Add optional nullable parent_journal metadata document {sequence,digest} to the closed
reservation JSON and archive_meta payload. Legacy missing meansNone; new writers use
consistent normalized representation. Validate exact schema/types and boundary-parent
correspondence. Both immutable child reservation and archive carry the same boundary;
RunCatalog.open_attempt checks parity alongside its existing identity/config/parent
checks. Root directory layout and read_reservation's existing4value return contract
remain unchanged; shared helpers may expose/validate optional metadata without
changing assets/lease producer interfaces. Do not duplicate entire metadata parsers.

RunCatalog.reserve may accept keyword parent_journal_boundary=None for publication
plumbing; all prior calls remain valid. RunCatalog.fork obtains source.fork_point,
then reserves/publishes the child with the selected checkpoint and sealed prefix.
World/cursors remain exact childrevision0; no journal copying/relabeling; parent
bytes remain unchanged. Later parent appends are outside the child's sealed prefix.
Same-boundary replay can recompute journal_boundary(through_sequence=sealed.sequence)
and compare digest; tampered prefix or missing sequence fails closed. Legacy child
with no seal remains readable; future live reuse must decline unsealed provenance
rather than guessing a source horizon. No source-prefix verification IO in record
constructors; driver/catalog consumers own external-source verification.

## Truthful action resolution and imports

Strengthen write AND read-side _audit/validation:
- action_resolved must follow response_validated or a valid response_reused for the
  same logical local request. Merely request_started/response_failed is insufficient.
- It must be checkpoint-owned, in the checkpoint transaction advancing its base
  revision by1. Reject standalone append/record, duplicate reuse in another checkpoint,
  missing/incorrect checkpoint FK and mismatching actor/tick/base slot.
- Base checkpoint tick equals source_tick; committed checkpoint tick is source_tick+1.
- outcome no_action iff safe decision.action_request isNone; otherwise accepted/rejected.
  Keep existing request/offered vocabulary and command/lifecycle audit checks intact.
All validations occur before transaction commit; rollback leaves world/cursors/
journal/commands unchanged. Readonly loading catches equivalent rawSQL corruption.
No speculative/apparent applied outcome can be replayed as a committed domain tick.

Extend response_validated with OPTIONAL content_digest and elapsed_seconds fields.
content_digest uses existing SHA256 validation; elapsed is finite nonnegative real,
notbool. Both are safe operational provenance, never WorldState/NPC input. Existing
valid records without them remain readable. BrokerResult.response_digest in LN06b
will map to content_digest; effective config is already bound by request+archive,
so don't duplicate provider objects or retain raw body/invalid output/CoT.

Add JournalEntry kind response_reused with required closed payload:
{request_id,base_revision,source_tick,actor_label,input_fingerprint,config_fingerprint,
request,decision,source:{attempt_id,request_id,boundary:{sequence,digest}}}, and optional
content_digest,elapsed_seconds. request/decision use existing safe schema/offered-action
validation; other slot/fingerprint fields use the same checks as request_started.
Source attempt ID is a canonical UUID, boundary is JournalBoundary. This means a
previously validated proposal imported for a local slot, NOT a new network request.
LN06b verifies source prefix/decision/input/config before appending it; storage checks
closed shape and local audit consistency, without opening arbitrary source paths.

Imported local request_id shares the exact request identity namespace with
request_started: sameID divergent entry/kind conflicts, byte-identical repeat is
idempotent. response_reused atomically establishes the local request+validated response
for auditing; an additional response_validated/failed for thatID conflicts. An action
may then reference it only in its own complete checkpoint transaction. Within-current-
attempt reuse simply references the existing validated request ID, no imported row.
Actual current-attempt request counts in LN06b are request_started rows only, including
failed/uncertain/retry starts; imports do not claim or consume another HTTP call.

## Tests, documentation and exact boundary

TDD: baseline existing archive suites; genuineRED for missing records/accessors,
uncommitted/failed action acceptance, and unsealed parent fork. Add cases for:
- atomic journal/metadata linkage, immutable records, empty/invalid/exact prefix bounds;
- source append after fork leaves sealed prefix stable; old-prefix tampering detected
  by recomputed digest; selected checkpoint/cursors exact and parent bytes unchanged;
- one-snapshot fork read under source activity, safe incomplete/malformed metadata and
  reservation/archive disagreement, legacy missing metadata reads without writes;
- request identity/import idempotence/conflict, offered decision validation and optional
  provenance value rejection; imports distinguished from actual request starts;
- pending/failed/standalone/duplicate/cross-checkpoint outcomes rejected on write/load;
  wrong source tick/base tick/committed tick and no_action disagreement fail atomically;
- retain existing checkpoint crash, command Step, lifecycle, lease/catalog and recorded
  resume assertions. Adapt an old fixture that wrote standalone action ONLY to place
  it in the required complete transaction and preserve its actual assertions; explain
  every intentional expectation change in report, never delete/weaken unrelated checks.

Allowed worker files ONLY: archives/model.py, store.py, catalog.py, __init__.py;
tests/test_run_archive_store.py, tests/test_run_archive_catalog.py; this task's report.
No assets/lease/runtime/cognition/HTTP/WorldState or other source. Root amends task/prompt
BEFORE any additional boundary/architecture decision. Keep strict types/Python>=3.11,
manager-owned mutation, immutable events, source history and all branches/worktrees.

Focused command: PYTHONPATH=src "$TASK_PY" -m pytest tests/test_run_archive_store.py
 tests/test_run_archive_catalog.py tests/test_runtime_recorded.py -q.
Smallest RED/correction tests first; final focused/scoped Ruff/Black/whitespace clean.
Worker no VCS/fullmake/examples/dependencies/subagents. Canonical report records
commands/results/counts/warnings, scope, limitations, selfreview and concerns.
Root independent review then full task/merged make, separate examples, whitespace and
exact canonical matrices before commits/integration. No partial completion claim.
