# Release Checklist

- Confirm the supported Python version from `pyproject.toml`.
- Create a clean virtual environment and run `make install`.
- Run `make` (formatting, lint, tests, and all numbered examples).
- Run `make examples` independently.
- Verify every documented public import in the installed package.
- Audit NPC prompt and context assembly against
  `docs/npc_information_boundary.md`.
- Confirm `VERSION`, package metadata, runtime `__version__`, and the HTTP
  health response report the same release version.
- Run `git diff --check` and review the complete release diff.
- Smoke-test `make serve` and the `/health` endpoint.
- Confirm the changelog, backlog, technical-debt register, and project journal
  match the release contents.
- Tag only after every checklist item passes and no release blocker remains.
