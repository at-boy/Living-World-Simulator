# Principal Architect and Orchestrator handoff

This directory lets a fresh Codex session resume orchestration without relying
on the prior chat history.

Start the new session by providing
[`principal_architect_orchestrator-prombt.md`](principal_architect_orchestrator-prombt.md).
It directs the session to read
[`continuation_brief.md`](continuation_brief.md) before it acts.

The task specifications in `docs/subagent_execution_plan/` remain the
authoritative plans for implementation. This handoff records the current
orchestration state and decisions that are not otherwise captured completely in
the repository documentation.
