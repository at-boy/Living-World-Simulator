# Project agent configuration path cleanup — October 19, 2026

Authorization: owner requested cleanup of the local agent-path edit after merging
and tagging v0.6, then explicitly authorized pushing main and the tag.
Work only in the isolated existing-main release checkout. Preserve milestone/v0.6
at 6bf4c63637584584a8dfce009d2d1d79987be570 and tag v0.6.0rc1 at merge092715c.

## Exact scope

Allowed files: .codex/config.toml; CHANGELOG.md; docs/project_journal.md;
docs/backlog.md; docs/subagent_execution_plan/maintenance/agent_config_paths.md;
the matching agent_config_paths-prombt.md and agent_config_paths-report.md;
docs/orchestrator_handoff/continuation_brief.md (current integration status only).
No simulation/runtime/package/version/role-content changes.

## Decision

Official OpenAI configuration reference resolves config_file from the declaring
config.toml directory. Committed .codex/agents/name.toml incorrectly repeats the
.codex segment; the owner's ../.codex/agents/name.toml workaround resolves to the
correct file. Use canonical agents/name.toml for explorer, worker and reviewer.
Preserve descriptions and all role-file contents. Back up the exact owner edit
before replacing its working-copy state with the committed equivalent main fix.

## Validation and completion

Reproduce all three missing committed targets, then validate new targets resolve
to the same files as the owner workaround and parse as TOML. Review exact diff;
run make, separate make examples and whitespace checks before committing. This is
a small root-owned configuration task; no worker or independent review required.
Commit/push the focused main followup without moving the release tag or milestone.
Switch the primary checkout to corrected main after backing up the local edit;
retain the isolated release checkout and all milestone/task branches/worktrees.
