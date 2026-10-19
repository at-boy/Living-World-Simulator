# LN01 — World snapshot codec implementation report

Status: independently reviewed; task and merged gates passed. Integration commit follows this report.
Worker checkout: `.worktrees/live-npc-ln01`, branch
`codex/live-npc-ln01-world-snapshot-codec`.
Root owns review, full validation, commit and integration.

## Implementation and scope

Created `src/living_world/repositories/world_snapshot.py` with frozen
`WorldSnapshot(schema_version: int, payload: str)`, its exact UTF-8 SHA256 digest,
`encode_world` and `decode_world`. The value validates exact integer schema types
(excluding bool) and string payloads. Unsupported versions and malformed payloads
fail through `WorldSnapshotError` (with an unsupported-schema subtype).

Moved the existing canonical serialization/deserialization helper implementation
mechanically into that module. A direct comparison against HEAD confirmed that
all helper bodies, from `_serialize_world` through the final helper, are
byte-identical. Schema version remains 12 and supported reads remain versions
1–12. Existing stage/replay encode validation and all decode validation remain in
the same order.

`SQLiteRepository` delegates to the codec and translates failures back into its
existing repository exceptions and messages. Original malformed-data and
save-validation causes remain directly accessible; unsupported-schema errors
retain their original absent cause. `_serialize_world` and `_deserialize_world`
remain compatibility imports from `sqlite_repository.py`. Constructor, load/save
signatures, table definition and persistence transaction behavior are unchanged.

Created `tests/test_world_snapshot.py` and extended
`tests/test_sqlite_repository.py`. Tests pin the complete pre-extraction schema-12
payload independently of the new implementation and compare the complete codec
row against the actual SQLite row. Coverage also includes detached nested entity
attributes, independent decodes, immutable snapshots, exact digest/version/UTF-8
bytes, malformed/future versions, all supported schemas without rewriting input,
and repository diagnostics/cause/unchanged stored bytes on rejected loads.

Only the four authorized source/test paths and this report were edited. No
schema, dependency, world-field, live behavior, NPC context, archive, CLI or API
changes. No staging, commit, branch mutation, integration or subagent delegation.

## Focused verification and TDD

Interpreter: `/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`
(`$TASK_PY` below). Every test command ran from this worker checkout with
`PYTHONPATH=src`.

- Baseline: `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_sqlite_repository.py -q`:
  **88 passed**, no skips or warnings.
- RED: `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py -q`:
  **1 collection error**, the required expected absence of
  `living_world.repositories.world_snapshot` (`ModuleNotFoundError`). This was
  observed before creating the codec or changing production code.
- Initial GREEN attempt: codec/repository focused tests produced **117 passed,
  1 failed**. Existing
  `test_schema_v6_load_rejects_duplicate_goal_labels_for_one_owner` caught an
  extra codec wrapper obscuring the existing direct cause diagnostic.
- Correction: restore the original underlying cause at the repository boundary.
  Smallest named regression command:
  `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_sqlite_repository.py::test_schema_v6_load_rejects_duplicate_goal_labels_for_one_owner -q`:
  **1 passed**, no warnings.
- Final core GREEN:
  `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py tests/test_sqlite_repository.py -q`:
  **121 passed**, no skips or warnings.
- Expanded regressions:
  `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py tests/test_sqlite_repository.py tests/test_canonical_founders.py tests/test_settlement_stages.py -q`:
  **334 passed**, no skips or warnings. This includes canonical exact fresh/resume
  payload checks, replay persistence/cursor failures and stage save/load validation.
- `"$TASK_PY" -m ruff check` on the four source/test paths: **passed**.
- `"$TASK_PY" -m black --check` on the four source/test paths: **passed**, four
  files unchanged. Initial import-order/re-export lint findings were corrected
  within the same authorized files before these final checks.
- `git diff --check`: **passed**.

## Self-review and remaining ownership

The codec contains the only canonical serializer implementation, has no dependency
on the SQLite repository and introduces no import cycle. Snapshots contain only a
schema integer and immutable payload string; decode constructs detached engine
state. Legacy input payload/version values are not normalized or rewritten.
Existing canonical tests and assertions were preserved unchanged.

No known implementation concerns or scope expansions. Independent review and root
full gates (`make`, separate `make examples`, canonical CLI hashes, final
whitespace) remain root-owned and were not run by this worker. No commit claimed.

## Independent review round 1 correction

Reviewer found a diagnostic regression for SQLite rows whose INTEGER-affinity
schema column contains unsupported text: snapshot type validation happened before
the repository's historic unsupported-version classification. Restored the raw
stored-version support check before constructing `WorldSnapshot`, reusing the
codec's canonical supported-version set. Snapshot exact-integer typing remains
unchanged. Unsupported text, REAL and BLOB values now receive the original exact
`RepositoryLoadError` message, absent cause and unchanged database bytes.

Added parametrized regressions for `'invalid'`, `12.5` and `b'12'`:

- RED: `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_sqlite_repository.py::test_unsupported_raw_sqlite_schema_types_preserve_diagnostics -q`:
  **3 failed**, each showing the incorrect malformed-data diagnostic before the fix.
- GREEN: `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py tests/test_sqlite_repository.py -q`:
  **124 passed**, no skips or warnings.
- Expanded regression rerun:
  `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_world_snapshot.py tests/test_sqlite_repository.py tests/test_canonical_founders.py tests/test_settlement_stages.py -q`:
  **337 passed**, no skips or warnings.
- Focused `ruff check`, `black --check` and `git diff --check`: **passed**.
  The new supported-version import was sorted before final lint verification.

Same authorized paths only; no staging, commits, full gates or scope changes.
Ready for root re-review with no known remaining implementation concerns.

## Root independent review and task gates

Independent reviewer /root/ln01_review found one P2 raw unsupported SQLite schema
diagnostic regression. Original worker corrected it with RED3/GREEN124 tests; scoped
re-review returned SPEC PASS / QUALITY PASS and NO SUBSTANTIVE FINDINGS. Reviewer
confirmed the moved helper bodies and independently reconstructed complete reference
payload are identical to the base. No parked or deferred findings.

Final task tree, Python3.13.5 dependency-only environment from task24, PYTHONPATH=src:

- `make VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: passed, **1452 tests / 10 existing
  deliberate skips**, including real Chrome checks; lint/format passed and
  examples001–039 passed. No new warnings.
- Separate `make examples VENV=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`: passed, **39 examples**.
- Staged and unstaged `git diff --check`: passed.

Full command paths and raw evidence remain in ignored current-plan SDD workspace
under integration checkout; logs ln01-task-make.log / ln01-task-examples.log.
Canonical CLI final-tree matrix and merged gates are recorded below after completion.

Final task-tree public CLI matrix passed all three pinned schema12 payload hashes,
two fresh runs per outcome, resume boundaries1/3/4 complete row equality, and
success/failure terminal zero-step continuation. Tick/outcomes remain success10,
stall5, failure13. Evidence: ln01-task-final-matrix/results.json and retained
scenario assets/checkpoint databases. No schema/version/dependency changes.

## Reviewed delivery and merged-tree validation

Delivery **5f64056** on preserved codex/live-npc-ln01-world-snapshot-codec is pushed.
Merged with --no-ff into codex/live-npc-runtime; no conflicts, owner-local master
plan text preserved uncommitted. Root merged `make` passed **1452 tests / 10 existing
skips**, lint/format and **39 examples**. Separate merged `make examples` passed
**39 examples**. Staged/unstaged whitespace passed. Final merged public CLI matrix
again preserved all3exact schema12 hashes, two fresh runs, resume1/3/4 complete
rows and terminal zero-step saves. Logs/evidence: ln01-merged-make.log,
ln01-merged-examples.log and ln01-merged-matrix/results.json in current-plan ignored
SDD workspace. No parked findings. Main/tag/milestone remain unchanged.

LN01 is complete after the integration commit containing this report; LN02 storage
contract follows from this reviewed head. This task adds a shared codec, not live
NPC inference, archive entrypoints, controls or durable runtime restart.
