# 14b — Release version consistency

## Task Description

Resolve the sole Task 14 release blocker by making all authoritative package,
runtime, and HTTP version surfaces report `0.5.0`, with one runtime export used
by the health endpoint and a regression test that checks release metadata.

This is a focused release correction. It adds no simulation or AI capability.

## Context Needed

- Create:
  `docs/subagent_execution_plan/14b_release_version_consistency-prombt.md` and
  `docs/subagent_execution_plan/14b_release_version_consistency-report.md`.
- Edit: `VERSION`, `pyproject.toml`, `src/living_world/__init__.py`,
  `src/living_world/api/server.py`, `tests/test_inspection_api.py`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: Task 14's blocked report and `docs/release_checklist.md`.
- Do not edit any other production, test, example, documentation, or planning
  file.

## Interface Contract

- `VERSION` contains `0.5.0`.
- `pyproject.toml` declares project version `0.5.0`.
- `living_world.__version__` publicly reports `0.5.0`.
- `GET /health` obtains its version from `living_world.__version__`; the HTTP
  server must not retain an independent hard-coded release string.
- The health response remains otherwise unchanged:
  `{"status": "ok", "version": "0.5.0"}`.
- A regression test proves `VERSION`, project metadata, the runtime export, and
  the health response agree. Use Python 3.11-compatible standard-library APIs.
- Do not introduce generated version files, build-time rewriting, a dependency,
  or a fallback version that can conceal inconsistent metadata.

## Test Criteria

- Focused inspection/version tests cover the four version surfaces.
- Existing HTTP inspection behavior remains unchanged apart from the version.
- `make`, `make examples`, and `git diff --check` pass.

## Documentation

- Record the release-blocker correction in `CHANGELOG.md` and
  `docs/project_journal.md` without claiming Task 14 closeout is complete.

## Orchestrator Report

Create
`docs/subagent_execution_plan/14b_release_version_consistency-report.md`.
Report exact files and interfaces changed, focused and full validation, the
four consistency checks, boundary compliance, and any remaining blocker.

## Boundary

- Only the listed files may change.
- Do not perform the remaining Task 14 documentation reconciliation or tag a
  release.
- Do not start Task 14a or any v0.6 work.
- No unrelated refactoring or package-version mechanism redesign.
