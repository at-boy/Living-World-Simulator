# Saved prompt — LN08e shared prepared archived launch

Work only in .worktrees/live-npc-ln08e on codex/live-npc-ln08e-prepared-launch.
Read AGENTS.md, then 08e_prepared_launch.md in this directory FIRST: it is your
requirements and exact decisions. Root approved the bounded producer contract under
the already approved LN07/LN08 execution. Base e990961 source is fully validated.
Do not read milestone history, full master plan/backlog/roadmap or continuation brief.

Implement only the four worker paths named in the task. Start from existing
runtime.entrypoints.run_archived and service/launch/LegacyArchiveSession public
interfaces plus directly relevant tests. Root decisions in the contract are binding;
raise concrete missing decisions before choosing architecture or expanding files.
Preserve headless policy and recorded legacy routing. This task exposes a shared
one-shot producer; HTTP serving, CLI parser, token files, signals and real Ollama are
later tasks. All world writes remain RuntimeService-owned.

Use meaningful TDD with fake providers and bounded event synchronization. Run focused
validation and scoped style only; no VCS/index/subagents/fullmake/examples/dependency
or model installs, other-checkout edits or normal attempts in temporary storage.
Write 08e_prepared_launch-report.md with changed paths, RED/GREEN evidence, exact
command/result/counts/warnings, architecture/limitations and root gates pending.
No success-output dumps. Return only status, one-line validation and concerns;
root independently reviews, validates, commits and integrates. Preserve owner edits.
