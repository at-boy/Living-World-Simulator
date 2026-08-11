# Task 14a — Milestone plan reorganization report

## Outcome

Reorganized the execution-plan history into milestone-owned directories after
the completed v0.5 closeout. The root now provides cross-milestone navigation,
the initial program is an explicit archive, and the existing v0.6 candidates
are separated without being authorized or implemented.

## Exact moves

- Moved every existing Task 01 through Task 14 artifact, including Task 14b
  and all plans, saved prompts, correction instructions, and reports, into
  `docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/` with `git mv`.
- Moved the Task 14a plan, saved prompt, and this report into that same archive
  after the report was created.
- Moved the existing Task 15 and Task 15a plans into
  `docs/subagent_execution_plan/v0_6/` with `git mv`.
- Preserved every filename, globally unique task number, and historical
  `-prombt.md` spelling. No duplicate, redirect, or symlink was added.

## Overview and index changes

- Reworked `docs/subagent_execution_plan/README.md` into the complete
  cross-milestone index, with direct links to every archived artifact and each
  existing v0.6 candidate.
- Added `initial_v0_2_3_to_v0_5.md` with the initial baseline, completed
  milestone outcomes, historical order, release closeout, and immutable
  archive policy.
- Added `v0_6.md` with the autonomous-founding-settlement objective and
  acceptance target, future `milestone/v0.6` branch name, candidate status of
  Tasks 15/15a, and the authorization/review contract for later work.
- Updated repository references whose path or description changed because of
  the migration. Historical artifact prose was retained where it records the
  path that applied when the task was executed.

## Reference audit

- Confirmed no Task 01–15 artifact remains loose at the execution-plan root.
- Confirmed every moved artifact is represented by a working link in the root
  index.
- Audited local Markdown links under `docs/` against existing files and anchors.
- Searched non-archive repository Markdown for stale loose task paths.

There is no known external-link compatibility requirement. Because this is a
repository-internal documentation archive, old loose paths intentionally have
no redirects or symlinks.

## Validation

- `make`: passed Ruff, Black, 393 pytest tests, and numbered examples
  001–023.
- `make examples`: passed all numbered examples 001–023.
- `git diff --check`: passed.

## Boundary compliance

Only documentation paths and Markdown content changed. No production code,
tests, examples, package metadata, release version, or Git branch was changed.
Task 15, Task 15a, and other v0.6 implementation were not started.

## Blockers and deferred work

None. The milestone layout documents candidate work but grants no
implementation authorization.
