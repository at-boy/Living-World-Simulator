# LN09f1 implementation report — bounded trace analysis reader

Status: worker implementation frozen for root independent review. No worker commit,
index, branch, integration, full-repository validation or completion decision.

## Scope and behavior

Exactly the four authorized worker paths were changed:

- `src/living_world/archives/trace_analysis.py` (new domain-only reader)
- `tests/test_trace_analysis_reader.py` (new real-archive regression coverage)
- `docs/npc_information_boundary.md` (one appended engine-only paragraph)
- this report

The reader uses a fresh SQLite URI `mode=ro` connection, `query_only=ON`, explicit
transaction, one-second busy timeout, and rollback/close per operation. Ref layout,
symlink/traversal/independent-file checks precede each open. It checks the metadata,
journal and format-two BLOB table kinds/columns/types/primary keys without opening
worlds, checkpoints, reservations or ancestors. Metadata/journal byte sizes and
SQLite storage classes are checked before fetching payload text. Journal hashing
incrementally preserves the canonical record-array representation, including empty
and gapped prefixes. It retains call DTOs, offered-action vocabulary for pending
requests, action-presence flags and digest lengths rather than all journal payloads.

Page observations remain restricted to the captured prefix. Request, settlement,
action identity, offered vocabulary, response cap and shared digest-length rules
are checked locally. Metadata queries select only BLOB type/length; a body query
is digest-specific, prefix-authorized and budget-checked before loading exact bytes.
Every returned selected body has its length and SHA256 checked. Request/response,
empty, malformed UTF8/JSON, incomplete and unavailable evidence remain distinct.

Frozen DTOs expose only `trace_metadata_checked` or `selected_body_verified`.
These are deliberately narrower than complete archive validity: no world,
checkpoint, command, lifecycle, reservation/retained-input identity, parent seal,
unreferenced body or unselected body-content validation is claimed. Existing full
archive validation was not changed. No archive package export, route, CLI, UI,
writer, migration, lease acquisition, cache, index, network/provider/model call,
source-spool read, recovery or source hash/format change was introduced.

## TDD and validation evidence

Commands below used
`PYTHONPATH=src /home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/pytest`
from the isolated LN09f1 checkout. Output is summarized, not pasted.

- RED: `-q tests/test_trace_analysis_reader.py` — 64 failed because the named
  `living_world.archives.trace_analysis` module did not exist, before production code.
- Initial GREEN attempt: same suite with `--tb=short` — 63 passed, one failed
  because the real action fixture checkpoint had not advanced its world tick.
  Corrected the test fixture to tick one; no production workaround.
- Expanded snapshot/schema/local-action/budget coverage: same focused suite —
  79 passed.
- Additional RED: `-q tests/test_trace_analysis_reader.py -k 'page_dto or deep_malformed'
  --tb=short` — two failed: mutable page call container accepted; deeply nested
  malformed journal JSON leaked RecursionError. Added immutable-container rejection
  and fixed safe archive diagnostics, then focused suite — 81 passed.
- Additional RED: `-q tests/test_trace_analysis_reader.py -k 'body_dto or backend_and'
  --tb=short` — one failed and one passed: mutable bytearray accepted by body DTO.
  Added exact-bytes rejection.
- Final GREEN: `-q tests/test_trace_analysis_reader.py
  tests/test_inference_trace_storage.py tests/test_run_archive_store.py
  tests/test_run_archive_catalog.py --tb=short` — 388 passed (83 new reader cases),
  no warnings.
- Scoped Ruff: task24 venv `ruff check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed. Initial lint found unused/unsorted
  imports and immutable dataclass default-call warnings; fixed imports and used
  a shared frozen default value.
- Scoped Black: task24 venv `black --check
  src/living_world/archives/trace_analysis.py tests/test_trace_analysis_reader.py`
  — passed, two files unchanged after formatting.
- Four-file whitespace scan (trailing whitespace, conflict markers, final newline)
  — passed. Root owns authoritative `git diff --check` and all Git operations.

The initial concurrency test used a WAL writer. Independent review found this
mode could mutate source-side coordination files; the correction below replaces
that fixture and narrows supported operation to product rollback journals.

Memory tests scope tracemalloc after imports/fixture setup. A 16MiB unrelated
`zeroblob` plus tiny retained evidence stays below 8MiB Python peak for page and
selected-body operations; query tracing checks the sole raw-body query is selected
by digest. A separate 16MiB journal payload trips the row budget without a journal
payload SELECT and below 8MiB peak. Body budget failure emits no raw-body SELECT.
Full-reader accessors are patched to raise in the narrow-reader test, and the real
full reader independently rejects the same-length corrupt body and later corrupt
world/command fixture which narrow metadata analysis can inspect.

Source-byte and mtime checks include synthetic opaque owner-lock, reservation and
retained-input files, successful reads, selected-read failures and malformed
storage failures. Missing/symlink/hardlink/traversal paths reject without database
creation. Legacy format one remains untraced and unmigrated; partial attempts with
no checkpoint remain analyzable.

## Limits and handoff

Defaults: 100000 journal rows, 67108864 journal bytes, 2097152 bytes per metadata/
journal row and 8388608 selected body bytes. Limits are exact positive integers;
page size is 1..100. Explicit budget excess raises the fixed
`Trace analysis limit exceeded.` diagnostic. No silent truncation or unlimited mode.
Scanning is O(selected-prefix rows/bytes), not constant-time pagination. Python
indexes and parsed payloads are bounded by the explicit budgets, not a claim of
constant memory. Only selected body bytes are hashed.

No unresolved seam or scope expansion was needed. Independent review, required
full task gates, exact canonical/CLI/source-server/wheel gates, common-document
updates, VCS and any later integration remain root responsibilities.

## Fixround 1 — review findings corrected, frozen for re-review

Read the complete independent review and root-amended task/prompt before editing.
Both P1 findings were valid: mode=ro/query_only did not preserve WAL sidecars, and
column/PK metadata alone did not prove an INTEGER PRIMARY KEY rowid alias.
The earlier report's broad source-preservation claim did not cover WAL sources;
that claim is superseded by the explicit supported rollback-only boundary below.

Correction one follows the root ruling: before each SQLite connection, recheck
safe paths and read exactly at most the 100-byte regular database header. Require
the SQLite magic and read/write version bytes both one. Any unsupported header or
existing `archive.sqlite3-wal`/`archive.sqlite3-shm` path (including dangling
symlinks) rejects with `Trace analysis requires rollback-journal archives.`
No SQLite connection, sidecar mutation, immutable mode, VFS, source copy,
permissions change or product writer change is used to work around WAL.
External concurrent journal-mode conversion is outside supported operation.

The concurrency fixture now uses the product's normal rollback mode. The reader
holds its shared snapshot lock while an ordinary archive writer prepares and
attempts COMMIT. An event observed outside the SQLite callback confirms the
writer has not finished during that read; the writer completes after reader
close, and a fresh reader observes the append. No WAL support is claimed.

Correction two rejects metadata/journal tables without a true rowid identity:
WITHOUT ROWID or a separate primary-key index, including SQLite's inline
`INTEGER PRIMARY KEY DESC` exception, rejects at schema validation. Metadata
identity inspection now returns only storage-class/equality scalars, never raw
id values. Before initial raw MAX(sequence), a scalar-only existence query checks
journal identity storage types/range. This adds defense before either identity
can become Python data.

Targeted RED/GREEN evidence, using the same task24 venv and PYTHONPATH as above:

- RED: `pytest -q tests/test_trace_analysis_reader.py -k
  'unsupported_journal_modes or descending_pk' --tb=no` — 11 failed, 83
  deselected. WAL/header/sidecar fixtures reached the forbidden connection guard;
  malformed descending-PK fixtures did not report schema rejection.
- Targeted GREEN: `pytest -q tests/test_trace_analysis_reader.py -k
  'unsupported_journal_modes or descending_pk or real_concurrent' --tb=short`
  — 12 passed, 82 deselected.
- Final focused GREEN: `pytest -q tests/test_trace_analysis_reader.py --tb=short`
  — 94 passed, no warnings. Includes page/body connection guards, absent/existing
  WAL sidecars, unsupported header/magic, recursive byte/mtime preservation,
  metadata and journal 16MiB descending-PK identities at both row-limit64 and the
  default row budget, no raw identity/MAX query, and Python peaks below8MiB.
- Scoped `ruff check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed. Initial correction lint found
  one nested-if simplification; resolved before final checks.
- Scoped `black --check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed, two files unchanged.
- Four-file whitespace scan — passed (trailing whitespace, conflict markers,
  final newlines). Root retains authoritative Git whitespace validation.

Only the same four authorized paths changed. The single engine-only boundary
paragraph now states rollback support and pre-open WAL rejection. No VCS, full
gates, subprocess network/model/provider actions, subagents or other paths.
This correction is frozen for independent re-review; root owns broader validation
and completion disposition.

## Root review and validation in progress

Independent astra spec/quality review1 found two P1s: WAL sidecar creation and
oversized malformed primary-key identity prefetch. Root amended task/prombt to
support normal product rollback journals only, with explicit pre-open WAL rejection;
normal store creation always selects DELETE. Original worker fixed both under the
same four-file boundary and original reviewer scoped re-review passed, two addressed,
zero open, no substantive findings. Review packages/reports retained in root ignored
plan workspace. Final focused94 passes supersede original83; no full WAL support claim.

Root compatibility gates PASS: exactcanonical26/twofresh/resume1/3/4/read-only complete
points with prior hashes and DBbytes unchanged; CLI7/sourceServe4/wheel11+actualServe4,
41normalattempts retained. Postfix reader checks on9 saved native-provider archives
verify30 local calls includingreused, exact selected bytes/SHA/length, stable pages,
and recursive sourcebytes+mtimes unchanged. No new inference/world created by these
reader checks. Fulltask make73219 exited0:2641passed/10existing deliberate skips480.14s, actualChrome
and39examples. Separateexamples39 and git diff --check PASS. Reviewedsource unchanged.
Featureintegration/repeatedgates remain pending.
Reviewed source/tests/pyproject SHAdbee511dbeb5b5c7902d3fe10d3bf608a9e1e85feed8764116369f695be8b610.

## Fixround 2 — R3 schema-introspection prefetch corrected

Read the complete root finding and amended task/prompt before correction. Root's
additional P1 finding was reproduced: raw PRAGMA schema enumeration materialized
unrelated table/index names and selected malformed column names/types into Python
outside the payload prefetch budgets. The earlier memory checks covered bodies,
journal payloads and identity columns but did not establish bounded schema
introspection. Their general memory claim is superseded by this added coverage.

Schema validation now uses table-valued PRAGMAs with parameter-bound fixed table
names and returns only scalar counts, flags and byte lengths. It never returns
unknown schema names, declared types, index names or unrelated names to Python.
The selected table must be one ordinary main-schema table. Selected column counts
must match the closed schema; each column's name-plus-declared-type byte length
must fit max_row_bytes before exact cid/name/type/not-null/PK/hidden predicates
are checked within SQLite. The rowid requirement remains: WITHOUT ROWID and a
separate PK index (including inline DESC-PK) reject via scalar flags/existence
queries without materializing index names. No change to archive format, writers,
world validation or the rollback-only source-preservation boundary.

Validation used the same task24 venv and PYTHONPATH as above:

- RED: `pytest -q tests/test_trace_analysis_reader.py -k 'giant_schema'
  --tb=short` — four failed, 94 deselected. Measured Python peaks were
  16788998 bytes (unrelated table name), 16783632 (unrelated index name),
  16789914 (selected column name), and 33565104 (selected declared type).
  All fixture metadata strings were 16MiB, created and released before
  tracemalloc started.
- First correction run of `-k 'giant_schema or descending_pk' --tb=short` —
  eight failed at import due to a SQL string quoting SyntaxError. Corrected
  the literal; no test or contract workaround.
- Targeted GREEN: `pytest -q tests/test_trace_analysis_reader.py -k
  'giant_schema or descending_pk' --tb=short` — eight passed, 90 deselected.
- Final focused GREEN: `pytest -q tests/test_trace_analysis_reader.py --tb=short`
  — 98 passed, no warnings. All previous 94 cases remain green. New tests
  assert successful narrow page analysis despite unrelated giant table/index
  names, rejection of giant selected column-name/type metadata, Python peaks
  below8MiB for each, no raw schema PRAGMA enumeration and recursive source
  bytes/mtimes unchanged.
- Scoped `ruff check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed.
- Scoped `black --check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed, two files unchanged after
  formatting.
- Four-file whitespace scan — passed (trailing whitespace, conflict markers,
  final newlines); root retains Git whitespace validation.

Only the existing allowed source, test and report paths needed correction; the
single engine-only boundary paragraph remains unchanged from fixround1. No new
paths, VCS/index actions, full gates, subagents, provider/model/network activity or
other checkout edits. Correction frozen for scoped independent re-review. Prior
full validation belongs to prior source bytes; root owns repeat gates and later
integration/completion.

## Fixround 3 — R3 schema-function shadowing corrected

Read the amended task/prompt, root's verbatim finding and the complete fixround2
independent review. R3 remained open: bare `FROM pragma_table_list` could bind to
an archive-owned table/view, and the former raw `max(wr)` could return a giant
BLOB into Python before rejection. Fixround2 addressed the original schema-name
fixtures but its broad scalar-transfer claim was incomplete for these shadows.

The query now explicitly invokes `pragma_table_list()`; all PRAGMA table-valued
functions in schema validation are explicit invocations. Archive-owned tables or
views shadowing these names fail closed through the fixed SQLite read error.
The without-rowid result is also intrinsically scalar, `max(wr!=0)`, rather than
returning unknown `wr` data. Every schema result remains a count, predicate flag
or byte length. Real product archives, giant unrelated schema names, selected
schema limits and the true-rowid/DESC-PK checks remain supported unchanged.

Validation used the same task24 venv and PYTHONPATH as above:

- RED: `pytest -q tests/test_trace_analysis_reader.py -k shadowed_schema
  --tb=short` — two failed, four passed, 98 deselected. Both table and view
  shadows of `pragma_table_list` reproduced the prefetch bypass with Python
  peaks 16783785 and 16783601 bytes. Shadow fixtures use a SQLite 16MiB zeroblob;
  all fixture construction and source snapshots occur before tracemalloc.
- Targeted GREEN: `pytest -q tests/test_trace_analysis_reader.py -k
  'shadowed_schema or giant_schema or descending_pk' --tb=short` — 14 passed,
  90 deselected. New cases cover table and view shadows of all three used
  function names (`pragma_table_list`, `pragma_table_xinfo`,
  `pragma_index_list`), both page/body calls at max_row_bytes64, safe rejection,
  Python peaks below8MiB, and unchanged recursive source bytes/mtimes.
- Final focused GREEN: `pytest -q tests/test_trace_analysis_reader.py --tb=short`
  — 104 passed, no warnings. All prior 98 cases remain green.
- Scoped `ruff check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed.
- Scoped `black --check src/living_world/archives/trace_analysis.py
  tests/test_trace_analysis_reader.py` — passed, two files unchanged after
  formatting.
- Four-file whitespace scan — passed (trailing whitespace, conflict markers,
  final newlines); root retains authoritative Git whitespace validation.

Only the allowed source, test and report paths changed for this correction.
The boundary paragraph remains unchanged from fixround1. No scope expansion,
VCS/index actions, full gates, subagents, network/model/provider activity, or other
checkout edits. This correction is frozen for scoped independent re-review;
root owns finding closure, repeat full validation and integration/completion.


Root final corrected-task validation: `make VENV=<task24venv>` PASS2651tests/10existing
deliberate skips481.84s, actualChrome/39examples; separate `make examples`39PASS;
`git diff --check`PASS. Existing helpers recorded_matrix.py26/read-only unchanged/
priorhashesexact, archived_cli_acceptance.py7, served_cli_acceptance.py4,
wheel_serving_check.py11resources+actualServe4, check_gate_results.py41normalattempts
allPASS. trace_reader_native_check.py9savedarchives/30localcalls includingreusedPASS
exactbytes/SHA/length/stablepages and recursive sourcebytes+mtimes unchanged. No new
inference/world for native-reader check. Prefixln09f1-fix3-task; gate session10879
exited0, allchildjobs0. Reviewedsource7eeb0344e913514b49b596dcc532ab5bbfcff7cc0bdd4cd77f335d7c4d716989 unchanged.
Originalastra scoped fixround3 spec+qualityPASS, cumulative3addressed/0open.
Earlier task/abortedmerged2641counts belong to older source and are superseded.
Corrected taskdelivery checkpoint only; featureintegration/repeatedgates pending.
Pause before usage10%threshold; no newtask or integration until ownerresume.
