# Saved LN07a implementation prompt

Implement exactly 07a_legacy_archives.md in the root-supplied isolated task checkout,
based on reviewed LN06 integration2da047f plus this contract. Read AGENTS.md and the
whole exact contract/prompt first, then only directly relevant source/tests.

Root decision: preserve ScenarioRunner and injected engine/state-reference semantics;
add optional typed archive observer instead of copying/replacing runner loop. New
controller-owned live service/entrypoints are LN07b. Every legacy CLI run attempt is
archived (including setup/provider-independent failure), unit roots explicitly temporary,
mirrors retain old cadence and exact world bytes. Scope/invariants/closed cursor/
metadata/failure semantics are decision-complete in contract; ask root about concrete
producer defects before expanding. No source outside12allowedpaths, no task/common
docs except own report, no main/tag/milestone/owner-plan edits.

TDD focused vertical slices, true RED then GREEN. TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python,
PYTHONPATH=src. No VCS commands/commits/pushes/subagents/fullmake/examples/installs.
Root owns architecture/review/gates/integration. Selfreview scoped Ruff/Black/whitespace
and truthful 07a_legacy_archives-report.md before stable handoff. Concise progress;
raise architecture uncertainty before guessing. On usage pause finish current small
edit, save exact partial report and stop. Never claim original LN07 complete here.

Root clarification: candidate_aborted is only for initialized unfinished runner
candidates. After successful observer.finished, mirror failure records failed attempt
but no candidate_aborted: final archived world is already complete. Pin distinction.
