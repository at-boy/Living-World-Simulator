# Task 16a subagent prompt — runner, checkpointing, and resume

Work only on `task/16a-runner-checkpoint-resume`, created after reviewed Task 16
is merged into `milestone/v0.6`. Read `AGENTS.md`, all required documents,
Task 16's report, and `16a_runner_checkpoint_resume.md` in full. The plan and
allowed-file boundary are binding.

Implement the typed runner and `living-world run` CLI with bounded default,
explicit continuous mode, atomic checkpoint/final saving, compatible resume,
injected/testable stop controls, stable summaries, and documented exit codes.
Keep CLI parsing separate from run behavior. Do not use wall-clock sleeps in
tests and do not overwrite a valid snapshot after a failed tick.

Do not implement goals, needs, work, external references, spatial state,
proposal tapes, domain terminal conditions, or UI. Do not add any route from
operator configuration or inspection into NPC context or cognition.

Stay inside the allowed files. Stop for a documented amendment if an interface
dependency requires expansion. Add focused tests, a numbered example,
operator docs, changelog, journal, backlog, and a truthful
`16a_runner_checkpoint_resume-report.md`. Run `make`, `make examples`, and
`git diff --check`. Do not commit, merge, push, or change branches; hand the
uncommitted delivery to the orchestrator for independent review.
