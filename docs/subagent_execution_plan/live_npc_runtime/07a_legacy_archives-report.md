# LN07a implementation report

Status: complete; delivery cd5e40d independently reviewed and integrated by the merge
containing this report. Task and merged gates passed. Original Task7 incomplete.

## Implemented behavior

- Added the optional typed `RunObserver` seam around the original runner's exact
  prepared/complete-tick/finalized boundaries. The runner keeps its engine and
  mutable state references, stop ordering, mirror cadence and result output.
- Added same-thread `LegacyArchiveSession` ownership, immutable retained inputs,
  exact world snapshots, the closed legacy cursor, checkpoint deduplication,
  terminal settlement and cleanup that preserves original failures.
- CLI run attempts now reserve and announce independent archives before engine
  creation, execute retained inputs, preserve the injected repository/factory,
  and record metadata-only failures when scenario identity cannot load. Parser
  errors and inspection remain outside the archive producer.
- Added recorded-only strict optional `finalize_proposals` metadata; omission
  remains accepted for legacy recorded configuration. New CLI attempts record it
  explicitly. Added temporary per-test XDG roots and documented archive behavior.
- Applied the root's amended distinction: unfinished initialized candidates may
  emit `candidate_aborted`; a mirror failure after successful `finished` emits
  only failed `attempt_finished`, preserving the completed archived world.

## RED / GREEN and verification

Interpreter for all checks: `/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python`.
All pytest commands used `PYTHONPATH=src`.

- Initial `-m pytest tests/test_runtime_legacy.py -q`: RED, collection failed
  because the new legacy session module did not exist. The initial test file
  included session snapshots, observer validation and metadata boolean/mode
  expectations. After their implementation: GREEN, 3 passed.
- `-m pytest tests/test_runner_cli.py -q -k 'automatically_archives or metadata_attempt'`:
  RED, 2 failed because `--archive-root` was unrecognized. CLI producer integration
  subsequently passed those cases in the combined focused runs.
- Boundary-focused legacy tests: 10 passed, then 13 passed after generic tape,
  failed-enter and cleanup-audit coverage was added.
- An intermediate new factory test failed due to an incorrect test assumption
  that SQLiteRepository exposes `path`; corrected the assertion to inspect the
  actual resumed repository world. No production workaround was introduced.
- Earlier combined focused runs: 228 passed, then 231 passed. Final current-tree
  focused run is recorded below after completion.
- New custom-engine failure/default mirror/import/invalid-scenario cases:
  `-m pytest tests/test_runner_cli.py -q -k 'custom_engine_failures or uvicorn or invalid_scenario_is'`:
  4 passed, 28 deselected.
- Scoped `-m ruff check` across all 10 touched Python paths: passed. Initial
  import/style findings were corrected before the final check.
- Scoped `-m black --check` across the same 10 paths: passed, 10 unchanged.

## Regression evidence and boundaries

Tests pin all three canonical outcomes with complete tick checkpoints and exact
schema/payload equality against their SQLite mirrors; generic no-tape and taped
runs; raw database continuation starting above tick zero; checkpoint-only flags;
original engine/state/thread ownership and one factory call; setup and malformed
or missing scenario failures; partial ticks, terminal predicates and finalizers;
archive-before-mirror failure; cleanup and lease release; parser/inspect isolation;
existing stdout and exit codes; and no uvicorn import during run.

Worker changes are confined to the 12 authorized paths (the new session, runner
and exports, CLI, archive model allowlist, three focused test modules plus test
fixture, canonical documentation, and this report). No archive store/catalog/assets,
controller/driver/domain/schema, dependency or provider changes were made.
No worker VCS commands, commits, pushes, installs, full make or examples were run.
The root owns independent review, `git diff --check`, required full gates, exact
recorded acceptance matrices, final report disposition and integration.

## Final check record

- `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_legacy.py tests/test_runner_cli.py tests/test_founders_cli.py tests/test_recorded_proposal_tapes.py tests/test_canonical_founders.py -q`: passed, 235 tests; no warnings reported.
- Scoped Ruff and Black checks: passed across the 10 touched Python paths.
- Direct Python whitespace check over the 12 allowed worker paths: passed;
  no trailing whitespace or missing terminal newline. This is not a substitute
  for the root-owned `git diff --check`.
- No outstanding implementation failure observed. Independent review and root
  acceptance remain pending; LN07b capabilities remain outside this stage.

## Independent review correction round 1

Two Important compatibility findings were confirmed: loader-valid relative
source definition declarations were rejected by archive manifest path validation,
and invalid definition schemas were incorrectly classified as persistence failure.
Root amended the task and saved prompt before corrections, adding only
`src/living_world/archives/assets.py` and `tests/test_run_archive_catalog.py` to the
worker scope (14 paths total). The previous 12-path statement describes the initial
implementation round; this amendment is the current boundary.

The capture path now walks original relative source components before normalizing
only the destination definition role. It rejects any escaping prefix, absolute or
backslash declaration and every symlink component, including one later cancelled
by `..`. The final file still passes existing regular-file and hardlink checks.
Archived manifest names remain strict. Exact original scenario and definition bytes,
SHA256 hashes, scenario fingerprint and retained-loader role identity are preserved.
CLI definition schemas now pass the existing `YAMLWorldDefinitionLoader` after
reservation and before capture; existing policy/tape precedence is retained.

Correction evidence:

- `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runner_cli.py tests/test_run_archive_catalog.py -q -k 'relative_definition_declarations or invalid_definitions_remain or safe_source_declarations'`:
  true RED, 7 failed (both review cases reproduced); GREEN, 7 passed and 81 deselected
  after the correction.
- `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_run_archive_catalog.py tests/test_runner_cli.py -q -k 'normaliz or manifest_roles_stay or archive_failures_remain'`:
  10 passed, 88 deselected. Checks escape prefixes, backslashes, cancelled symlinks,
  hardlinks, retained-byte tamper, strict manifest roles, and archive IO/corruption
  remaining persistence exit 4. The final suite also repeats these cases after
  ensuring the backslash fixture itself contains valid quoted YAML.
- Expanded final focused suite includes `tests/test_run_archive_catalog.py` in
  addition to the original five task modules; final result recorded below.
- No VCS/index operations, full gates, dependency operations or additional scope.
  Root independent scoped re-review remains required before approval or commit.

Round 1 final current-tree checks:

- `PYTHONPATH=src "$TASK_PY" -m pytest tests/test_runtime_legacy.py tests/test_runner_cli.py tests/test_founders_cli.py tests/test_recorded_proposal_tapes.py tests/test_canonical_founders.py tests/test_run_archive_catalog.py -q`: passed, 301 tests; no warnings reported.
- Scoped Ruff: passed across all 12 touched Python paths.
- Scoped Black check: passed, 12 files unchanged.
- Direct whitespace check: passed over all 14 allowed worker paths. Root-owned
  `git diff --check`, independent re-review and required full gates remain pending.

## Root task acceptance

Independent review's2Important compatibility findings were confirmed, corrected by
the original worker and scoped re-reviewed: SPEC PASS/QUALITY PASS,2addressed/0open,
NO SUBSTANTIVE FINDINGS. No source changed after re-review.

- Full taskmake with existing task24VENV: passed1,800tests/10existing skips,
  lint/format/actualChrome and39examples.
- Separatemakeexamples: passed39. Staged/unstagedgitdiff--check passed.
- Exact canonical matrix: all3payload hashes, duplicatefresh runs, resume1/3/4,
  terminalzero-step passed. All26normalCLI invocations retained complete independent
  archives in matrix/state/living-world/runs forlateranalysis; none were deleted.
- Fullmake left reviewed correction byte-identical.

Evidence in current-plan ignored SDDworkspace: ln07a-task-make.log,
ln07a-task-examples.log, ln07a-task-matrix/results.json and retainedstate,
ln07a-review-1.diff,ln07a-fix-1.diff,ln07a-review-final.md. Taskbranch delivery and
mergedgates follow; no live/service/restart/browser capability claimed here.

## Root merged acceptance

Delivery cd5e40d source remains unchanged after independent re-review. Integration
with reviewed LN06c resolved only root-owned documentation conflicts.

- Merged `make` using task24 VENV: passed 1,809 tests / 10 existing skips,
  lint/format, actual Chrome and 39 examples.
- Separate merged `make examples`: passed all 39 examples.
- Merged canonical matrix: all three exact payload hashes, duplicate fresh runs,
  resume boundaries 1/3/4 and terminal zero-step checks passed. All 26 normal CLI
  invocations have readable persisted archives with complete checkpoints.
- Staged/unstaged `git diff --check`: passed. Owner-local master-plan edit preserved.

Evidence: ln07a-merged-make.log and ln07a-merged-matrix/results.json plus retained
state in the current-plan ignored SDD workspace. LN07b setup/preflight and LN07c
service/entrypoints remain upcoming; no browser or installed-model acceptance claimed.
