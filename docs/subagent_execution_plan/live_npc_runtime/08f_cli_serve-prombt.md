# Saved prompt — LN08f public local operator serving

Work only in .worktrees/live-npc-ln08f on codex/live-npc-ln08f-cli-serve.
Read AGENTS.md then 08f_cli_serve.md FIRST: it is your exact requirements and root
architecture decisions. Base b26ddf3 is reviewed, full task/merged validated source.
No milestone/roadmap/backlog/continuation reconstruction. Use only necessary code,
tests and existing sharedlaunch/service/operator/auth interfaces.

Implement exactly8 worker paths in the task. Shared preparedlaunch is available;
RuntimeService remains sole mutation/lease/settlement owner. Serving/signals/credentials
are one bounded consumer; no new gameplay/player/provider/schema/auth API behavior.
Default paused, public loopback HTTP during blocking setup, separate owner/launch/
server threads and truthful failure/cleanup. Root decided the lifecycle, failure
helpers and credential-file semantics; flag a concrete missing decision before code
or boundary expansion. No secrets in archive/log/URL/config/processarguments.

Use meaningful TDD including actual CLI subprocess/Chrome. Fake provider only; real
Ollama acceptance later. Python /home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python,
PYTHONPATH=src. No VCS/index/commit/subagent/fullmake/examples/installs/downloads/
othercheckout writes. Unittemp archives allowed; normalmanualattempts persist.
Root performs whitespace/boundary/review/fullgates/integration. Write exact ownreport
08f_cli_serve-report.md with RED/GREEN, changedpaths, commands/result/counts/warnings,
lifecycle/security evidence, limitations and rootgatespending. No successful output
dumps. Return concise status/testsummary/concerns; do not commit or expand scope.
