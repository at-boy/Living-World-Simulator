# Task 14b subagent prompt — release version consistency

You are an isolated Python release-correction subagent. Execute only Task 14b
from `docs/subagent_execution_plan/14b_release_version_consistency.md`.

Read that plan, Task 14's blocked report, the release checklist, relevant
version and HTTP source, and the existing inspection tests in full. Respect the
exact allowed-file boundary.

Set every specified package/metadata/runtime version surface to `0.5.0`. Keep
`living_world.__version__` as the public runtime export and make `/health`
consume that export rather than maintaining another hard-coded version. Add a
Python 3.11-compatible regression assertion that `VERSION`, `pyproject.toml`,
the runtime export, and the HTTP response agree.

Do not redesign packaging, add dependencies, change other HTTP behavior,
perform Task 14's remaining documentation closeout, tag a release, execute
Task 14a, or start v0.6 work.

Update the allowed changelog and journal files, create the required report,
run focused tests, `make`, `make examples`, and `git diff --check`, then return
the uncommitted delivery to the orchestrator for independent review.
