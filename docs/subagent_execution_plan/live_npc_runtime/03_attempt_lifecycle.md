# Task 3 / LN03 — Attempt lifecycle and retained reconstruction inputs

Status: owner-authorized execution resumed October21,2026, base0d04c1b.
Root owns architecture/review/full gates/VCS/integration. LN01/LN02 are complete.
Binding [design](../../superpowers/specs/2026-10-19-live-npc-runtime-design.md) and
[master plan](../../superpowers/plans/2026-10-19-live-npc-runtime.md).

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


## Exact authorizing task

## LN03: Attempt catalog, retained inputs, ownership and compatibility mirrors

**Files:**
- Create: `src/living_world/archives/catalog.py`, `src/living_world/archives/assets.py`, `src/living_world/archives/lease.py`, `src/living_world/archives/mirror.py`, `tests/test_run_archive_catalog.py`, `tests/test_run_archive_mirror.py`.
- Modify: `src/living_world/archives/__init__.py`.
- Slug: `attempt_lifecycle`.

**Interfaces:** `RunCatalog(root: Path)`;
`reserve(config: AttemptConfig, *, parent: tuple[str, int] | None = None) -> AttemptRef`;
`attempts() -> tuple[AttemptSummary, ...]`; `open_attempt(attempt_id: str,
*, read_only: bool = True) -> AttemptArchive`;
`fork(attempt_id: str, revision: int, *, config: AttemptConfig | None = None) -> AttemptRef`;
`retain_inputs(ref: AttemptRef, scenario_path: Path, *, tape_path: Path | None) -> RetainedInputs`;
`AttemptLease(ref).acquire()/release() -> None`;
`write_checkpoint_mirror(checkpoint: Checkpoint, destination: Path) -> None`.
`AttemptSummary` has ref, mode, scenario, parent, started/ended time, lifecycle,
last_revision/tick optional and failure code. `RetainedInputs` has resolved scenario,
definitions, optional tape paths and content hashes; no live external file reference.

**Focused verification:** `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_run_archive_catalog.py tests/test_run_archive_mirror.py -q`.
RED must identify the absent required behavior; GREEN means all selected tests pass
with no unexplained new skips. For later regressions, use the smallest named failing
case until the complete focused set is ready.

- [ ] **Step 1 — Add failing tests** unique attempt reservation; parent fork exact
  checkpoint; immutable assets with relative definition paths, spaces/?/#; missing or
  modified assets; path traversal/symlink escape; active-owner versus abandoned run;
  pre-world setup failure; mirror failure after archive commit.
  ```python
  child = catalog.fork(parent.attempt_id, revision=3)
  assert child.attempt_id != parent.attempt_id
  assert catalog.open_attempt(parent.attempt_id).checkpoint(3) == before
  assert catalog.open_attempt(child.attempt_id).checkpoint().snapshot == before.snapshot
  ```
- [ ] **Step 2 — Observe RED** run the two new archive test modules. Use two actual
  processes for exclusive ownership and unexpected exit, temporary filesystem roots.
- [ ] **Step 3 — Implement** reserve UUID attempt directory before loading scenario;
  default catalog root `$XDG_STATE_HOME/living-world/runs` or
  `~/.local/state/living-world/runs`, explicit root overrides; no code mutates HOME.
  Capture asset bytes by SHA256 into local content-addressed storage and preserve
  loader-relative names in a private per-attempt input tree. Atomic temp-file rename
  publishes manifests, but SQLite remains authoritative for progress. Lock using
  stdlib advisory file locking (fcntl on POSIX, msvcrt on Windows); never infer death
  from PID alone. Read discovery derives interrupted status if no owner exists;
  GET/discovery does not persist that status or mutate historical DB bytes.
- [ ] **Step 4 — Implement compatibility export** backup/construct a standalone
  closed temp SQLite snapshot in destination directory, fsync then atomic replace.
  Validate source/destination alias and reject overwrite of archive-owned storage.
  Parent input is read-only; child copies its exact world/cursors and reconstruction
  inputs with parent reference. New-model config requires explicit child settings;
  no archived model/token credentials inferred. Mirror failure is `ArchiveMirrorError`
  with archived attempt/revision and failed destination, never a fake rollback claim.
- [ ] **Step 5 — Observe GREEN** test all catalog/mirror cases, including destination
  disk/permission failure after archive commit and corrupt/future-format input. Views
  preserve DB bytes; failed-before-initialization attempts show `tick=None`.
- [ ] **Step 6 — Review, root gates and commit** `feat: retain discoverable isolated run attempts`.


## Root-resolved storage contract

The source allowance below is exact. LN01/LN02 are complete; consume their public
interfaces without changing model.py/store.py/world_snapshot.py or existing tests.
No world schema or archive SQL schema change is authorized in this task.

### Catalog, identities, metadata and failure discovery

RunCatalog(root: Path) takes an explicit Path, exposes read-only absolute root,
and supplies static default_root() -> Path: absolute XDG_STATE_HOME/living-world/runs,
otherwise Path.home()/.local/state/living-world/runs. Relative XDG_STATE_HOME is
ignored. No constructor or read method creates directories. Reservation creates
private directories only as needed; never chmod existing owner directories.

Layout: root/<lineage UUID4 hex>/<attempt UUID4 hex>/ with archive.sqlite3,
attempt.json, owner.lock, inputs.json and private inputs/. Shared verified objects
live at root/objects/<SHA256>. IDs are exact lowercase UUID4 hex; no user path is
interpreted as an ID. Reject symlinks at every path component; no traversal or
hard-link escape to another archive. A flat scan of these two identity levels
resolves attempt_id; duplicate IDs in different lineages are corruption, not a
first-match choice. Unknown IDs fail without creating files.

reserve allocates IDs/directory before scenario/provider setup, creates the fixed
owner.lock once (one nonsecret byte), holds a temporary lease while publishing a
closed format1 attempt.json and creating the empty AttemptArchive. Manifest exact
fields: format, lineage_id, attempt_id, config, parent, reserved_at, reservation_error.
config matches AttemptConfig exactly; parent is null or [attempt_id, revision];
reserved_at UTC ISO timestamp; reservation_error null or archive_initialization_failed.
Publish via closed temp file, fsync, atomic rename. After successful reserve the
reservation manifest is immutable; SQLite owns lifecycle/checkpoint progress.
An archive creation failure preserves the reservation and records its classified
error when possible; raise ArchiveReservationError(ArchiveError) exposing ref.
Never clean up evidence or manufacture an initial world. Failed/incomplete directory
entries remain discoverable even when manifest/DB publication was interrupted.

Define frozen AttemptSummary in catalog.py with fields ref:AttemptRef,
mode:Literal['recorded','ollama','journal_replay']|None, scenario:str|None,
parent:tuple[str,int]|None, started_at:str|None, ended_at:str|None,
lifecycle:str, last_revision:int|None, tick:int|None, failure_code:str|None.
Validate constructor types, exact ints/UUIDs/timestamps and freeze collections.
Known reference identity comes from both directory levels, even if metadata is absent;
unknown metadata stays None. started_at uses reservation timestamp if available,
otherwise valid archive.created_at; no invented timestamps. End time is last terminal
lifecycle time. Persisted lifecycle is last archive lifecycle, default initializing.
Terminal states: completed/stopped/failed/interrupted. Nonterminal plus definitely
unowned lease derives interrupted in the summary only. No PID death heuristic.
A probe failure preserves the known state and reports owner_probe_unavailable;
never claim interrupted on an uncertain lock. Corrupt/unknown-format attempts are
listed as failed with archive_invalid (or archive_incomplete if publication absent),
with available safe reservation metadata, without opening a runner or repairing files.
One corrupt attempt must not hide other attempts. Stable sort by identity tuple.

Attempts/open/discovery perform no mkdir, lock creation, manifest rewrite, SQLite
migration/recovery write or historical mutation. open_attempt validates ref/metadata
and returns AttemptArchive.open with requested read_only. A complete checkpoint
requires valid retained inputs; pre-world attempts may have no inputs yet. Explicit
writer callers must hold AttemptLease throughout mutation; read-only open takes
no ownership. Querying history never marks a live owned attempt interrupted.

### Retained reconstruction inputs

Define frozen RetainedInputs in assets.py with scenario_path:Path,
definition_path:Path, tape_path:Path|None, hashes:Mapping[str,str]. Paths are absolute,
contained regular files in the private input tree; hashes maps relative private
input paths to lowercase SHA256 and is deeply frozen. No external runtime reference.
Export load_retained_inputs(ref:AttemptRef)->RetainedInputs in addition to retain_inputs.
All load/open consumers recheck bytes, role/path/ID/schema/hash/type and loader validity.

Store exact original scenario and definition bytes, preserving the definition path
relative to the scenario. Retain optional tape bytes. Do not rewrite scenario YAML
or fingerprints, follow symlink files/ancestors, accept absolute/escaping loader paths,
or use an external source after publication. Spaces, ? and # in filenames are literal
filesystem names. Capture bytes once and validate only the staged retained files
with YAMLScenarioLoader/YAMLWorldDefinitionLoader and YAMLProposalTapeLoader where
applicable. Check scenario key/seed against the archive's config; loader identities
and existing recorded tape compatibility remain authoritative. Helpers may inspect
only the existing loader-required fields, not introduce a second scenario parser.

Content objects are addressed by SHA256, verified before reusing an existing object,
never silently replaced on mismatch. Private files are plain independent byte copies,
not hard links to shared objects. No ordinary copy of a SQLite DB. Publish inputs.json
only after the complete staged tree is closed and validated. Exact manifest fields:
format (1), lineage_id, attempt_id, scenario, definitions, tape, files. Role values
are relative paths (tape nullable); files is relative-path->SHA256. Unknown/duplicate
keys, unknown formats, bad hashes, missing/changed files and symlinks fail closed.
Reject extra or overlapping role paths and escaping manifest paths. An identical
repeat validates and returns existing inputs without overwriting; divergent retry
fails and preserves prior inputs. Read discovery never creates missing input files.

### Fork and configuration semantics

Parent belongs to this catalog, validated read-only; selected revision is exact
nonnegative int, never bool. New child keeps lineage, gets a fresh attempt ID and
explicit (parent attempt_id, selected revision) link. Copy exact selected snapshot
(schema/payload/digest) and both cursors through child.commit(expected_revision=None,
entries=()), producing child revision0. Retain exact parent input bytes privately.
No clock-driven world advance, no inherited command receipts or domain events.
Parent DB/inputs remain byte-identical. No provider calls or simulation setup here.

config=None preserves parent config. Explicit config must keep scenario_key and seed;
recorded can only remain recorded; ollama may remain ollama or become journal_replay;
journal_replay stays journal_replay. New nonsecret model/limit settings are an
explicit child operation. Retain exact source cursors initially; later live driver
reconciles an explicit changed configuration against parent binding, never guesses.
Do not duplicate/rewrite parent decision journal into child: immutable parent link
retains the source for later LN06 fingerprint-validated response reuse at the selected
parent revision. Changed config cannot reuse old prepared responses. The live driver
can open that same-catalog parent read-only through RunCatalog; no implicit fresh HTTP.
A child setup error after reservation leaves its attempt inspectable; do not delete it.

### Exclusive ownership

AttemptLease(ref) acquire/release plus static is_owned(ref)->bool and context-manager
support. Acquire uses existing fixed owner.lock and nonblocking stdlib advisory
exclusive locking (fcntl POSIX, msvcrt Windows), owned descriptor retained until
release. Only acquire may create a missing lock for a valid reservation. Probe opens
an existing lock and never writes bytes/mtime; absent lock means unowned, errors raise.
Handle same-process competing handles and real competing processes, release after
unexpected exit, double release, closed resources and inherited-process misuse.
No PID metadata or process killing. Browser/history reads never acquire run ownership.
Windows implementation should be isolated; report if only POSIX was exercised.

### Compatibility mirror: explicit required source context

Root amendment supersedes the incomplete plan signature for this new interface:
write_checkpoint_mirror(checkpoint:Checkpoint, destination:Path, *,
attempt:AttemptRef)->None. The required attempt supplies truthful error identity and
archive-owned path protection, which Checkpoint deliberately does not contain.
Future service/CLI callers must pass attempt explicitly; no metadata added to world.
ArchiveMirrorError(ArchiveError) exposes attempt, revision and destination.

Validate source attempt identity/layout, selected checkpoint ownership/equality
against its read-only archive, destination/source alias and path safety before writes.
Reject any destination inside this catalog's archive-owned root (including other
attempts, objects, manifests and DBs), any symlink path/ancestor and an existing
multiply linked file. Do not follow an output link or overwrite archive storage.
Destination parent must already exist. Create a unique closed temporary SQLite
file in that directory, using the exact checkpoint schema/payload for the sole
compatible world_snapshots row; validate via existing read-only repository/codec.
Fsync the completed file, atomic os.replace and fsync parent on supported POSIX.
Every error is ArchiveMirrorError with authoritative attempt/revision and destination;
parent/previous mirror unchanged on pre-replace failure. Clean up only this operation's
own unpublished temp file. Never promise rollback after a completed replace or
cross-file atomicity; archive already committed remains authoritative.

### Validation and non-goals

Use real child processes and pipe handshakes for ownership/unexpected exit; no sleeps
as correctness proof, no production test switches. Read tests compare DB and retained
input bytes, including active-owner discovery. Exercise setup failure before initial
world, reservation/create failure, corrupt/future formats, parent/mirror alias/hardlink/
symlink/traversal, changed inputs/config, paths containing spaces/?/#, actual permission
failure with prior mirror retained and explicit archive-ahead diagnosis. Cover root
that does not exist without read-side creation. Focused TDD archive catalog/mirror,
then archive store/codec/repository regressions; worker no full make/examples.
Root independent review then full make/separate examples/whitespace/canonical hashes
on task and merged trees. No CLI, controller, provider, browser or NPC context changes.

## Exact worker ownership

Create only archives/catalog.py, assets.py, lease.py, mirror.py under src/living_world;
tests/test_run_archive_catalog.py and tests/test_run_archive_mirror.py. Modify only
archives/__init__.py and this task's 03_attempt_lifecycle-report.md. No other edits,
subagents, VCS mutation, dependencies, full make or source changes in earlier tasks.
Ask root before widening scope or choosing unresolved architecture. Worker returns
stable uncommitted diff. Root common docs: this task's three artifacts, execution
index README, CHANGELOG, journal, backlog and continuation. Preserve owner plan edit.
