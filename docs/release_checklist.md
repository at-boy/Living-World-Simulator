# Release Checklist

For `0.6.0rc1`, record evidence in the [Task 24 report](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).
A pending or unavailable gate cannot be marked passed.

- Confirm Python >=3.11 and consistent VERSION, project metadata, runtime version,
  installed metadata and HTTP health version.
- Independently review the whole milestone and final closeout diff; resolve any
  defect under a bounded plan/prompt/report and re-review it.
- Run root-owned `make`, independent `make examples`, and `git diff --check`.
- Run each public canonical CLI outcome: success10, stall5, failure13; compare
  two fresh final `(schema_version,payload)` rows and resumes at1/3/4 without
  excluding IDs, events, charges or replay progress. Check terminal zero-step resumes.
- Inspect all three saved outcomes in an actual browser, including Needs, Work,
  Goals, Stages, External connections, History and Spatial drill-down. Verify
  GET-only traffic and unchanged complete engine state and physical database bytes.
- Build an isolated wheel; install it into a fresh environment with validation
  tools external to the artifact. Verify site-packages imports and all documented
  public imports, five founders YAML files and three inspector assets.
- Exercise installed module and entry-point CLI, the canonical fresh/resume matrix,
  saved snapshot loading, optional-server behavior and real loopback inspect/GET.
- Run isolated installed import/health/canonical CLI checks on minimum Python3.11;
  use Python3.13.5 for full primary gates. Record failures and meaningful warnings.
- Audit NPC context/proposal authority against the [boundary](npc_information_boundary.md).
- Check local document links, task plan/prompt/reviewed-report coverage and merge
  provenance; align release notes, README, journal, changelog, backlog and handoff.
- After review/integration, repeat required merged-tree make/examples/whitespace
  and release/package/CLI smoke where integration could affect it. Verify live
  remote milestone tip, unchanged main and the separate user configuration edit.
- Leave a clean release task checkout and durable final handoff. Only the owner
  may separately authorize main integration, a release tag or publication; passing
  this checklist does not itself authorize those actions.
