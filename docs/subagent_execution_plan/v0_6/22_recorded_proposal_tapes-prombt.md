# Task 22 subagent prompt — deterministic recorded proposal tapes

Work only on `task/22-recorded-proposals` after Task 21 merges. Implement the
strict tape loader, proposal-only cognition adapter, replay cursor policy, safe
diagnostics, and runtime hooks in the binding plan. Tapes receive filtered
context/actions and remain untrusted; never read raw state, expose IDs, bypass
the gateway, or determine outcomes.

Stay inside allowed files, add tests/example/docs and the truthful report, run
`make`, `make examples`, and `git diff --check`, and do not commit, merge, push,
or change branches.
