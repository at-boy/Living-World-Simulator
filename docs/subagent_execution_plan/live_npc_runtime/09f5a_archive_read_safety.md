# LN09f5a — Read-only archive SQLite safety implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox tracking.

**Goal:** Preserve saved archive bytes and modification times when read-only consumers encounter unsupported SQLite sources.
**Architecture:** Share a bounded filesystem/header precheck between the full archive store and trace reader. Existing callers retain their path, identity, schema and transaction checks. Product rollback-journal writers remain unchanged.
**Tech Stack:** Python >=3.11, pathlib/stat, SQLite, pytest.
**Spec:** Approved live-NPC runtime design and remaining offline historical-world inspection scope; `docs/trace_analysis.md`; parent `docs/superpowers/plans/2026-10-19-live-npc-runtime.md` (owner edit preserved).

## Global Constraints

- RuntimeService remains sole simulation writer; managers own mutation, systems own behavior, events are immutable.
- NPC contexts remain filtered. LLM output remains an untrusted proposal through the ordinary action gateway.
- No archive format/schema, provider, prompt, parser, gateway, world reconstruction, API/UI or lifecycle changes.
- Preserve existing low-level standalone AttemptRef support; do not impose catalog nesting or new hardlink restrictions on AttemptArchive.
- No source writes, migration, conversion, copies, chmod, immutable mode, recovery, dependencies or model servers.
- Root owns task contracts, common documentation, all Git operations, full validation and integration. Preserve all existing branches/worktrees and owner edits; never main/milestone/tag integration.

## Review Focus

- Externally converted WAL databases, even without sidecars: reject before SQLite opens.
- Existing or dangling WAL/SHM sidecars: reject without changing source bytes/mtimes.
- Missing, symlink, directory, FIFO and malformed header: fail promptly with ArchiveFormatError, no creation.
- Existing read-only handles: recheck on each subsequent connection.
- Normal rollback writers/readers: checkpoint, trace and concurrent append behavior remains supported.

## Task 1: Shared read-only guard

**Worker allowed files (seven; no others):**
- Create `src/living_world/archives/sqlite_readonly.py`.
- Modify `src/living_world/archives/store.py`: import and read-only `_connect` guard only.
- Modify `src/living_world/archives/trace_analysis.py`: import and `_snapshot` guard extraction only.
- Create `tests/test_archive_read_safety.py`.
- Modify `tests/test_trace_analysis_reader.py`: only expected guard message in `test_unsupported_journal_modes_reject_before_sqlite_open`.
- Modify `docs/trace_analysis.md`: document shared full-store read-only scope and limits.
- Create `docs/subagent_execution_plan/live_npc_runtime/09f5a_archive_read_safety-report.md`.

**Interfaces:**
- Produce `require_rollback_database(path: Path) -> None` in the new module.
- Require existing regular non-symlink database BEFORE opening its bytes (avoid FIFO blocking); read only first 100 bytes. Require length 100, magic `SQLite format 3` followed by NUL, header bytes 18:20 equal 1,1. Reject adjacent `<database-name>-wal` or `-shm` if existing or dangling symlink. Missing/unreadable/unsupported input raises fixed `ArchiveFormatError("Read-only access requires rollback-journal archives.")` without raw path/error disclosure.
- Do not reject ordinary `-journal` files: product DELETE-mode writers may have an active transaction.
- `AttemptArchive._connect`: after existing `_path` validation, before sqlite3.connect, call guard on every read_only connection. Preserve writer/create/default behavior, full validation, errors, transactions and ownership.
- `_snapshot`: replace duplicate header/sidecar checks with helper, retaining validate_ref/safe_path regular+singlelink, mode=ro, query_only, timeout, transaction and cleanup semantics.
- Existing path-validation messages can remain; the shared guard's own failures use the fixed message above.

- [ ] Write meaningful failing tests against actual AttemptArchive.open(read_only=True): real external WAL without sidecars; WAL/SHM present/dangling; invalid headers; missing/nonregular/symlink paths. A connect spy proves rejection before native SQLite; byte/mtime inventory proves preservation. Run RED before implementation.
- [ ] Implement helper and two narrow integrations; update the existing trace assertion's message only.
- [ ] Test an already opened read-only handle rejects newly added sidecar or subsequent WAL conversion. Verify normal full-store checkpoint/load/latest and trace reads, standalone refs and hardlink behavior retained, default writer creation remains usable. Include an actual rollback writer with a live journal and successful subsequent commit/read; avoid timing-only concurrency tests.
- [ ] Run focused suite with task24 Python: `PYTHONPATH=src <venv>/bin/python -m pytest -q tests/test_archive_read_safety.py tests/test_run_archive_store.py tests/test_trace_analysis_reader.py tests/test_runtime_revision_source.py`. Run scoped style and whitespace.
- [ ] Document scope honestly: supports product rollback databases, rejects external WAL; precheck is not a hostile filesystem race-proof snapshot and does not bound native SQLite parser memory. Source atime is not part of the preservation claim.
- [ ] Self-review and write own report: RED/GREEN commands, counts, meaningful failures/warnings, files and limitations; freeze for independent review. No successful output dumps.
- [ ] Root independent review, then full task gates (`make`, separate `make examples`, whitespace and existing compatibility/installed-wheel/browser gates). Root commits delivery only after passing; no-ff feature integration and repeated full gates before feature push.

Root preflight: the helper consumes only Path, avoiding trace-reader catalog/singlelink assumptions in the full store. Shared fixed error requires one narrowly allowed existing-test assertion update. No other conflict found; all five review inputs map to tests above. This is a prerequisite within existing approved execution, not activation of a new milestone.
