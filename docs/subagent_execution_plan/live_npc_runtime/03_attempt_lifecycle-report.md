# LN03 attempt lifecycle report

Status: independent review and root task gates passed; delivery/integration pending. Worker returned an uncommitted diff on
`codex/live-npc-ln03-attempt-lifecycle`, based on `bcbb5bd`.

## Implemented

- Nested UUID catalog reservation, immutable format-one reservation metadata,
  initialization-failure references and discovery of incomplete/corrupt attempts.
  Read operations allocate nothing, preserve historical bytes and derive interrupted
  lifecycle only from a definite absence of advisory ownership. Duplicate attempt
  identities fail closed. Invalid lineage nodes are never followed; independently
  corrupt attempt entries do not hide valid attempts.
- Exact staged scenario/definition/tape retention, loader-relative private paths,
  SHA256 content objects and closed immutable manifests. Definition filenames with
  spaces, question marks and hashes remain literal. Load/open validates hashes,
  schema/identity/configuration, roles, missing/extra files and loader compatibility.
  Private copies are independent files; divergent retries and damaged existing
  content objects fail without replacing retained inputs.
- OS descriptor-held leases, nonblocking independent acquisition, read-only probes,
  process/thread ownership bookkeeping, double release and inherited-handle rejection.
  Per root amendment, retention borrows a caller's actual current-thread lease or
  owns a short standalone lease; writer opens require caller ownership.
- Same-lineage forks retain exact selected snapshot and both cursors at child
  revision zero, privately retain reconstruction bytes and reference the parent
  revision. Parent journal/world/input bytes are unchanged; command/event receipts
  and decision journals are not copied. Mode/scenario/seed transitions are checked.
- Explicit-attempt compatibility mirrors validate checkpoint ownership and unsafe
  destinations, construct/close/validate/fsync a standalone SQLite temporary file,
  atomically replace the destination and sync the parent directory on POSIX.
  Publication errors carry attempt/revision/destination and never imply archive
  rollback. Only this operation's unpublished temporary file is cleaned up.

## Verification evidence

All Python commands used the dependency-only interpreter
`.worktrees/task24/.venv/bin/python` with `PYTHONPATH=src` in the LN03 checkout.

- Baseline: `-m pytest tests/test_run_archive_store.py tests/test_world_snapshot.py
  tests/test_sqlite_repository.py -q` — **175 passed**.
- Initial RED: `-m pytest tests/test_run_archive_catalog.py
  tests/test_run_archive_mirror.py -q` — **2 collection failures**, naming absent
  required catalog/mirror modules. Subsequent targeted RED cycles reproduced
  symlink-attempt masking, missing-reservation timestamp fallback, unlisted private
  files, absent caller-lease enforcement/borrowing and invalid-lineage masking.
- Final focused/regression command: `-m pytest tests/test_run_archive_catalog.py
  tests/test_run_archive_mirror.py tests/test_run_archive_store.py
  tests/test_world_snapshot.py tests/test_sqlite_repository.py -q` — **222 passed**
  (**47 new catalog/mirror cases**, **175 existing regressions**), no skips/warnings.
- Scoped `-m ruff check` on the five source files and two new test modules — passed.
- Scoped `-m black --check` on those same seven paths — passed after formatting
  the last appended test. Earlier style findings were corrected before handoff.
- `git diff --check` — passed.

Real spawned processes and pipe handshakes prove competing ownership and release
following unexpected termination. A real fork checks inherited bookkeeping; a real
foreign thread checks borrowing/writer rejection. Actual directory permission denial
preserves a prior mirror after archive commit. Separate injected fsync failures cover
pre-replace preservation and post-replace error reporting without a rollback claim.
Tests compare historical DB/input bytes, check special filenames and nested paths,
verify setup/initialization failures remain discoverable, and exercise invalid future
formats, manifests, hashes, missing inputs, symlink/hardlink aliases and mode changes.

## Self-review and limits

Reviewed allowed-file boundaries, immutable public records, lease lifetime,
read-side writes, fork precision, partial publication and mirror error identity.
Fixed the discovery/retention gaps above using focused regression cases. Existing
LN01/LN02 interfaces, world/archive SQL schemas and recorded payloads are unchanged.
No CLI, controller, provider, browser or NPC-facing path is introduced.

Only POSIX locking, fsync and permission behavior was exercised on this Linux host.
The isolated stdlib Windows locking branch still needs Windows execution. File checks
reject symlink ancestors and multiply linked regular files; this does not claim
protection against a malicious same-user process concurrently replacing filesystem
components during an operation. Full repository `make`, separate examples and
independent review remain root responsibilities, as assigned.

Worker changed only the four new archive modules, archive exports, the two new test
modules and this report. Root-owned task/prompt amendments were preserved. No
subagents, dependency changes or stage/commit/merge/push actions were performed.

## Independent review round 1 correction

Root relayed one substantive P1 finding: although the initial attempt read was
protected, fallback `Path.exists()` calls could raise `PermissionError` for an
inaccessible attempt and suppress summaries for every other attempt.

The actual-permission regression
`test_inaccessible_attempt_does_not_hide_good_attempt_or_repair_history` reserves
two attempts, removes all permissions on one attempt directory, discovers both
identities, checks the damaged entry is failed with `archive_invalid` and the good
entry remains visible, then restores permissions and compares all saved file bytes
and mtimes. Targeted RED reproduced the unguarded `attempt.json` existence check;
targeted GREEN passed after protecting every fallback classification probe.
Inaccessibility now preserves any safely known metadata and does not claim that
publication is absent. Fallback also revalidates the reference before probing it.

Correction verification, using the same interpreter and checkout:

- Targeted regression command — **1 failed before correction**, then **1 passed**.
- Five-module catalog/mirror/store/codec/repository pytest command above —
  **223 passed** (**48 new cases**, **175 existing regressions**), no skips/warnings.
- Scoped Ruff and Black checks on the same seven source/test paths — passed.
- `git diff --check` — passed.

Only catalog implementation, its existing test module and this report changed in
this correction. No VCS/full-gate/subagent actions. The independent review recheck
and root gates remain pending; Windows execution remains unverified as disclosed.

## Root independent review and task validation

Independent reviewer /root/ln03_review found one P1: an inaccessible attempt's
error-classification probes could suppress the entire catalog. Original worker
reproduced actual chmod-denied RED and corrected it, then223focused passes.
Scoped re-review returned SPEC compliant / QUALITY approved and NO SUBSTANTIVE
FINDINGS. No deferred/parked code findings. Windows locking remains unverified
on this Linux host; the report makes no Windows execution claim.

Final task tree, dependency-only Python3.13.5 with PYTHONPATH=src:

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`:
  **1551 passed / 10 existing deliberate skips**, including actual Chrome;
  lint/format and **39 examples passed**, no new warnings.
- Public CLI canonical matrix: all3pinned schema12 hashes, two fresh runs/outcome,
  resume1/3/4 complete row equality and success/failure terminal zero-step passed.
  Outcomes remain success10/stall5/failure13.

Evidence in ignored current-plan SDD workspace beneath integration checkout:
ln03-task-make.log and ln03-task-matrix/results.json plus exact retained assets/DBs.
Separate examples, final whitespace and merged validation follow below.
No CLI/browser/live-model or runtime-cold-restart capability claimed by LN03.

Separate task `make examples` with the same VENV: **39 passed**. Final staged
and unstaged `git diff --check`: passed. Evidence ln03-task-examples.log.
