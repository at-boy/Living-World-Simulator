# Task 14b report — release version consistency

## Outcome

The Task 14 version-consistency blocker is resolved. All four release surfaces
report `0.5.0`, and the HTTP health endpoint consumes the public runtime export
rather than retaining an independent version string.

Task 14 release closeout was not resumed, no tag was created, and no simulation
or AI behavior changed.

## Interfaces and files changed

- `VERSION` now contains `0.5.0`.
- `pyproject.toml` now declares project version `0.5.0`.
- `living_world.__version__` now publicly reports `0.5.0`.
- `GET /health` still returns `status` and `version`, but obtains its version
  from `living_world.__version__` and now reports `0.5.0`.
- `tests/test_inspection_api.py` checks the version file, TOML project metadata,
  runtime export, and HTTP response for exact agreement using `tomllib` and
  `pathlib`, both available on Python 3.11.
- `CHANGELOG.md` and `docs/project_journal.md` record the focused correction
  without claiming release closeout.

## Four-surface consistency evidence

| Surface | Value/source |
| --- | --- |
| `VERSION` | `0.5.0` |
| `project.version` | `0.5.0` |
| `living_world.__version__` | `0.5.0` |
| `GET /health` | imports and returns `living_world.__version__` |

The regression test also retains the response shape
`{"status": "ok", "version": "0.5.0"}`.

## Validation

- `PYTHONPATH=src .venv/bin/pytest tests/test_inspection_api.py` — passed,
  **7 tests**.
- `make` — passed: Ruff, Black, full pytest suite, and numbered examples.
- `make examples` — passed independently for all numbered examples.
- `git diff --check` — passed.

## Boundary compliance and blockers

Only the eight files allowed by Task 14b plus this required report changed. No
other production, test, example, documentation, or planning file was edited.
No dependency, generated version file, build-time rewrite, or fallback version
was introduced.

No Task 14b blocker remains. Task 14 still requires a separate orchestrator
decision to resume its remaining release documentation and validation work.
