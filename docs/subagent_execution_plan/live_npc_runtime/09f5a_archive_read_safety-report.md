# LN09f5a implementation report

Status: implementation and focused validation complete; frozen for root independent
review. Full validation, approval, Git operations and integration remain root-owned.

## Changes and boundary

- Added `src/living_world/archives/sqlite_readonly.py` with
  `require_rollback_database(path: Path) -> None`. It checks regular/non-symlink
  status before opening bytes, reads only the first 100 bytes, checks SQLite magic
  and rollback header versions, and rejects any adjacent WAL/SHM entry, including
  dangling symlinks. Filesystem failures use the fixed error without a raw cause.
- `src/living_world/archives/store.py`: import and guard on every read-only
  connection after existing `_path` validation; default writers are unchanged.
- `src/living_world/archives/trace_analysis.py`: import and replacement of duplicate
  checks; existing stricter path validation, connection options, transactions and
  cleanup remain intact.
- Added `tests/test_archive_read_safety.py` with 23 cases against real store files,
  including native-connect rejection spies and byte/mtime inventories.
- `tests/test_trace_analysis_reader.py`: only the authorized fixed guard message
  assertion changed.
- `tests/test_run_archive_store.py`: only
  `test_fork_point_uses_one_snapshot_during_source_append` changed, under the root's
  explicit plan/prompt amendment. Its concurrent WAL snapshot still uses the
  existing writable/default store path; concurrent append and snapshot assertions
  remain intact. The root amended the boundary before this test was edited.
- `docs/trace_analysis.md`: shared full-store scope, writer compatibility and limits.
- This report is the eighth worker-owned path. Root-authored plan/prompt amendments
  were preserved; no other files or checkouts were edited.

## TDD and validation evidence

Python used throughout:
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`
(denoted `<python>` below). All commands ran in the assigned LN09f5a checkout.

1. RED, before production edits:
   `PYTHONPATH=src <python> -m pytest -q tests/test_archive_read_safety.py`:
   16 failed, 2 passed. Fifteen failures proved unsupported sources or subsequent
   handle reads reached the forbidden native connect. One fixture failed because
   it updated a lifecycle row that had not been created. The fixture was corrected
   to create a lifecycle row before its transaction.
2. Corrected RED, still before production edits:
   `PYTHONPATH=src <python> -m pytest -q tests/test_archive_read_safety.py --tb=no`:
   15 failed, 3 passed; all failures were missing pre-SQLite rejection behavior.
3. Initial focused GREEN:
   `PYTHONPATH=src <python> -m pytest -q tests/test_archive_read_safety.py tests/test_run_archive_store.py tests/test_trace_analysis_reader.py tests/test_runtime_revision_source.py`:
   264 passed.
4. Additional permission and missing/dangling-path coverage initially yielded
   1 failed, 268 passed with the same focused command. The simulated database
   `lstat` failure intercepted existing `_path` validation before the shared helper;
   that specific helper-error assertion was isolated to the helper. Open and
   sidecar-stat permission failures still exercise `AttemptArchive.open`.
5. Final focused GREEN, same four-file command: 269 passed, no warnings reported.
6. `<python> -m ruff check` and `<python> -m black --check` over the six changed
   Python paths: both pass. Initial style checks found one import-order issue and
   new-test formatting; both corrected before the final focused run.
7. Scoped whitespace check using Python over the eight worker-owned paths:
   passed; no trailing whitespace or missing terminal newlines. Root retains
   authoritative `git diff --check` responsibility.

No full `make`, examples, dependency installation, real model calls, subagents,
Git/index/commit commands, or other-checkout edits were performed.

## Self-review and limits

- Rejected sources are tested for native-connect avoidance and unchanged bytes,
  entry inventory and modification times. FIFO rejection happens before file
  opening; source access times are intentionally outside the preservation claim.
- Real external WAL conversion without sidecars is covered independently from
  present/dangling WAL and SHM entries. Existing handles recheck before each
  checkpoint, latest-revision and world-load connection.
- Real DELETE-mode transactions retain an active rollback journal during successful
  full-store and trace reads; the writer then commits and its data is readable.
  Standalone refs, hardlinks, writer creation/default opens, world loading and
  checkpoints remain supported. The existing concurrent writable WAL snapshot
  regression is retained under the amended contract.
- Shared guard failures use the fixed error. Existing caller path validation and
  its behavior are deliberately preserved, including stronger trace-only rules.
- The precheck is not protected against hostile filesystem races and does not
  bound native SQLite parser memory. No recovery, conversion, schema, runtime,
  model/provider, NPC context, gateway or simulation-authority changes were made.
- No unresolved implementation concerns found within the amended boundary.
  Independent review and all authoritative full gates remain pending with root.

## Root task validation — November11,2026

Independent review: spec compliance PASS, quality PASS, NO SUBSTANTIVE FINDINGS. Root task gate session98204/prefixln09f5a-task all jobs0. `make VENV=<task24venv>` PASS2895/10 existing intentional skips in679.32s, including actualChrome and39examples; separate `make examples`39 and `git diff --check` PASS. Canonical26/priorhashes/read-only/CLI7/sourceServe4/wheel14+Serve4/native-reader9archives30calls/installedwheelAPI8+Chrome exactdownload/CLI16+SIGINT+SIGTERM/custody/sourcebytes+mtimes checks PASS. Reviewed304files/source0ef4c55c6e1cdda4158012490de4272efbfb26b0c1a1f407861d745fed1543fa unchanged before/after gates. No new model calls or full runtime acceptance claim. Feature integration/repeated gates remain pending.
