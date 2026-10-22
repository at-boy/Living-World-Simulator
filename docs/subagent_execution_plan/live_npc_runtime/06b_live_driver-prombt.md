# Saved LN06b implementation prompt

Implement exactly [the LN06b contract](06b_live_driver.md) on the isolated task
checkout supplied by root, based on reviewed integration9875d5e plus this contract.
Read AGENTS.md, that whole exact contract and this prompt first, then only directly
relevant source/tests. Do not independently read milestone/handoff/backlog/history.

LN01–LN06a are complete and independently reviewed. Existing protocols own lifecycle,
archive atomicity/seals/imports, exact world codec and filtered founders feedback.
Consume them without redesign. Root has resolved architecture/config/cursor/IPC/
recovery/replay decisions in the contract; raise concrete producer defects before
expanding boundaries. No public CLI/browser work, model download or real-provider
strategy claim. Actual Ollama acceptance remains LN09.

Follow focused TDD by coherent vertical slices, then final focused set, scoped
Ruff/Black/whitespace and self-review. Read tests/interfaces before each slice.
Use TASK_PY=/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv/bin/python,
PYTHONPATH=src in this checkout. Real local stubHTTP + spawned-process tests are
required; mocks alone cannot prove timeout/cleanup. No test weakens existing
contracts. Preserve recorded exact worlds and source archives.

Only the 13 worker files in the contract are allowed, including this task report.
Do not edit plan/prompt/common docs. No VCS commands, commits, pushes, subagents,
fullmake/examples, dependencies or edits to other checkouts. Root runs review and
all authoritative gates and commits. Record commands/results/counts/warnings, RED/
GREEN, boundaries, selfreview and limitations in 06b_live_driver-report.md.

Send concise progress at coherent slice boundaries; escalate architectural ambiguity
before choosing. If instructed to pause for usage, finish the current small edit,
update report with exact partial state and stop. No false DONE/acceptance claims.

Root consumer-seam amendment (October22, before implementation of this addition):
Replay constructors accept optional source_point:ForkPoint; composition exposes its
captured source_point. Service later passes the SAME point to driver, preventing
source advancement between constructors from selecting inconsistent horizons. Verify
supplied checkpoint/seal, load only through it, test inter-constructor append.
No new files, archive API or broad source changes are authorized by this amendment.

Root review clarification: transient private IPC transports schema/vocabulary-valid
UNTRUSTED proposal prose before parent current-world boundary validation. Raw provider
body/malformed output/CoT remain forbidden; parent validates before durable journal/
use and deletes IPC. Worker cannot validate world-dependent facts without receiving
forbidden world state. This clarifies transport, not additional model authority.
