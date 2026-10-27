# LN09c — Inference trace storage implementation report

Status: worker implementation ready for independent review; root completion gates pending.
Base supplied by root: `ccf9763`, branch `codex/live-npc-ln09c-trace-storage`.
Worktree: `.worktrees/live-npc-ln09c`. No worker Git/index/commit operations.

## Scope and behavior

Implemented privileged archive storage only. New archives use format 2 and immutable,
content-addressed SQLite BLOB records. Format 1 remains readable and ordinarily writable
without migration or querying the new table. Exact opaque bytes, including invalid UTF-8,
embedded NUL and observed empty responses, are retained without decoding. Unavailable
responses reference no bytes; incomplete responses identify only their observed prefix.

Closed request/response validators return deeply frozen metadata. Optional trace fields
extend existing request, accepted/failed response and reused-response journal documents.
Omitted fields preserve historical journal payloads and boundary hashes. Existing world,
checkpoint, driver/feedback cursor, transport content_digest and elapsed_seconds behavior
is unchanged. Reused observations require copied request metadata and use its response
size bound. Request-only reused traces remain valid.

`append` and `record` publish supplied BLOBs and journal references in the existing single
writer transaction. Duplicate identical records/BLOBs are idempotent; divergent journal
identities fail without patching existing evidence. Full archive validation checks the
format-two table, actual SQLite BLOB types, SHA256 bytes, lengths, every reference,
request/response association and orphan rows. Prefix reads validate once inside one read
transaction, preserve requested digest order and require every digest to be referenced
within the selected journal prefix. Existing writer ownership/read-only guards and
boundary hashing are unchanged.

Root corrected the initial endpoint contract to existing Ollama `/api/generate` before
implementation. Root also amended task and saved prompt to permit exactly the existing
future-format fixture's `2` to `3` correction after the compatibility test exposed it.
No provider behavior changed.

## Validation evidence

All commands ran from the assigned worktree with existing
`VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`.
No dependencies were installed.

- RED: `PYTHONPATH=src $VENV/bin/python -m pytest -q tests/test_inference_trace_storage.py`
  — 63 failed, 1 passed, 0.76s. Missing blob export/module/APIs and journal optional
  fields caused the expected failures; the existing closed-schema behavior already
  rejected the invalid cases in the passing test. No collection errors.
- Initial GREEN, same command — 64 passed, 0.48s.
- Expanded storage coverage, same command — 88 passed, 0.40s.
- Initial requested compatibility run (the five files below) — 354 passed, 1 failed,
  8.43s. `test_run_archive_store.py::test_reading_corruption_and_future_format_never_repairs`
  still injected now-supported format 2. Reported the out-of-boundary fixture seam to
  root; changed only its injected value to 3 after root amended both task and prompt.
- Subsequent requested compatibility run — 379 passed, 8.19s.
- Final GREEN: `PYTHONPATH=src $VENV/bin/python -m pytest -q
  tests/test_inference_trace_storage.py tests/test_run_archive_store.py
  tests/test_run_archive_catalog.py tests/test_run_archive_fork_setup.py
  tests/test_runtime_broker.py` — 387 passed, 8.13s; 96 storage tests and 291 compatibility
  tests. No warnings reported.
- Scoped `$VENV/bin/python -m ruff check` for the six Python files below — passed.
  An earlier run found four import/formatting issues; scoped Ruff fixes resolved them.
- Scoped `$VENV/bin/python -m black` formatted four changed Python files; final scoped
  `black --check` — passed, six Python files unchanged.
- `git diff --check` — passed.

Coverage includes request/response closure and exact types, nonfinite numbers, UTC,
loopback endpoint/header guards, deep immutability, request/response/BLOB SQL failure
rollback, duplicate writes, divergent identities, missing/orphan/type/hash/length/schema
corruption, response max+1 observation, request association, copied reuse bounds,
missing/gapped/empty journal prefixes, later-body invisibility, preserved prefix seals,
authorized prefix copying, read-only bytes, writer thread guards, genuine format-one
open/record/commit/command behavior, and unchanged untraced checkpoint/cursor/seal values.

## Allowed worker path inventory

1. `src/living_world/archives/inference.py` — new frozen bytes record and validators.
2. `src/living_world/archives/model.py` — optional closed journal metadata.
3. `src/living_world/archives/store.py` — format 2, transactional BLOBs, audit and prefix reads.
4. `src/living_world/archives/__init__.py` — public `InferenceBlob` export.
5. `tests/test_inference_trace_storage.py` — new storage coverage.
6. `tests/test_run_archive_store.py` — only injected unsupported format `2` to `3`.
7. This report.

Task/prompt amendments visible in the worktree are root-owned. No worker edits outside
this amended inventory.

## Limitations and remaining work

No provider capture, broker integration, reuse/replay consumer integration, admin analysis,
portable export, real provider acceptance or world/NPC exposure is implemented here.
Validators certify representation and byte-reference consistency, not actual HTTP
activity, canonical provider generation or timing-clock provenance. Full archive
validation deliberately rehashes retained bytes on every validation, as required.

No unresolved implementation seam is known. Independent review, full repository/example
gates, common documentation, integration and VCS are root responsibilities and were not
run or claimed by this worker. Sources are frozen for review after the checks above.

## Root independent review and task gates — October27,2026

Independent solhigh review SPEC PASS / QUALITY PASS, NO SUBSTANTIVE FINDINGS.
Frozen package SHA256 c7d74fbe58f0fe40ae0e35b533215f4e19908a993494e6f1318aa4aa2d5f9a62.
Root task `make VENV=ABS_VENV` passed: 2469 tests, 10 existing deliberate skips,
429.60s; actual Chrome coverage and all 39 examples passed. Separate `make examples`
after make exited passed. Root exact canonical matrix26 passed with prior success/stall/
failure payload hashes; all26 new-format2 attempts reopened read-only at latest complete
checkpoint without changing database bytes. Archived CLI7, source serving4 and offline
wheel11 resources plus actual wheel serving4 passed (41 normal attempts retained,
including normal failed attempts). Whitespace/cached checks passed. Reviewed source/tests/
pyproject diff SHA fae773e77296a78805dbd0a1570ee18ea27844fb2f3721397602ca9811ca7716
remained exact after formatters. Evidence retained in root ignored ln09c-task-* artifacts.
No real provider inference, capture or admin completeness claim. Feature integration and
repeated merged gates remain pending at task commit.
