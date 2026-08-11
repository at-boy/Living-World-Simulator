# Principal Architect and Orchestrator handoff

This directory lets a fresh Codex session resume orchestration without relying
on the prior chat history.

Start the new session by providing
[`principal_architect_orchestrator-prombt.md`](principal_architect_orchestrator-prombt.md).
It directs the session to read
[`continuation_brief.md`](continuation_brief.md) before it acts.

The cross-milestone task index is
[`docs/subagent_execution_plan/README.md`](../subagent_execution_plan/README.md).
Completed initial-program artifacts are archived under its initial milestone
directory; future plans belong to their applicable milestone directory. The
task specifications remain authoritative for implementation.

This handoff records the current orchestration state, validation baseline,
authorization boundary, and decisions that are not otherwise captured
completely in the repository documentation. A fresh session must still inspect
the worktree and recent commit history before acting.
