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
