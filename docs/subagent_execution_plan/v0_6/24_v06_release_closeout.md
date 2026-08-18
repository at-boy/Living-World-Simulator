# 24 — v0.6 release-readiness closeout

## Status and dependencies

Authorized only after every prior v0.6 task is reviewed, reported, merged, and
pushed. Execute on `task/24-v06-closeout` from `milestone/v0.6`.

## Task description

Audit the complete milestone against its acceptance target and prepare the
version branch for owner integration. This task may correct documentation and
release metadata; implementation defects require isolated correction tasks.

## Closeout requirements

- Audit every plan/prompt/report, branch merge, public export, ADR, migration,
  API/UI route, example, and NPC/authority boundary.
- Re-run success/stall/failure and replay/resume comparisons; verify the
  inspector explains each outcome and contains no mutation channel.
- Update version surfaces to the approved v0.6 release version, changelog,
  journal, backlog, roadmap, handoff, README/API/operator docs, and release
  notes consistently.
- Run `make`, `make examples`, `git diff --check`, and packaging/import smoke
  checks. Report exact counts/results and any unavailable tooling truthfully.
- Leave `milestone/v0.6` clean and pushed. Do not merge, commit, tag, or push to
  `main`; final integration/tagging requires separate owner action.

## Report

Create `docs/subagent_execution_plan/v0_6/24_v06_release_closeout-report.md`
with requirement-by-requirement evidence and unresolved blockers.
