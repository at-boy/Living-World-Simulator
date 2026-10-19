# Task 22 worker prompt — deterministic recorded proposal tapes

Read AGENTS.md and the complete binding
22_recorded_proposal_tapes.md in this directory, then
../../adr/ADR-0025-deterministic-recorded-proposals.md. Work only in the isolated
already-pushed task/22-recorded-proposals branch. The plan is the exact source
of field names, interfaces, error codes, tick/cursor policies and allowed files.

Implement its strict proposal-only YAML tape and stateless cognition adapter,
manager-owned schema12 replay binding/cursor, persisted scenario public-label
mapping and lifecycle guards, one-entry-per-tick proposal phase, pure read-only
offer composition, ordinary action gateway, failed-tick step/run/save guard,
preparation/finalization hooks, checkpoint-only and tape CLI controls,
detached inspection and fail-closed NPC filtering. Never expose raw state,
identifiers, fingerprints, provider/handler objects or hidden records to client
or context; tape output cannot determine outcomes.

Use TDD and preserve strict annotations in production, helpers and tests. Run
all commands with PYTHONPATH=src where importing project code: this fresh
.venv contains dependencies but no editable project installation. Use focused
checks during implementation; run the binding focused matrix plus lint/format
and diff checks before return. Root owns independent review and final full
make/examples gate, superseding the old worker full-run requirement.

Add example038, required project documentation and truthful
22_recorded_proposal_tapes-report.md with red/green evidence, files, focused
counts, meaningful warnings and limitations. Do not paste successful logs or
claim review/integration. Raise architectural ambiguities to root before
choosing; do not broaden scope. No canonical founders content, inspector UI,
live provider or goal/stage terminal integration in this task.

No agents, branches, staging, commits, merges, pushes, config or main changes.

2026-10-14 amendment: the plan now permits only schema12 expectation updates
in existing tests/test_settlement_stages.py; preserve its stage behavior tests.
Direct engine advance/save also enforces missing replay preparation as a
configuration error distinct from failed-tick poisoning.

Resume clarification (2026-10-14): the binding plan now requires complete-state
replay cursor/event bijection validation and its corrupt-snapshot regressions.
Read that section before the narrow manager/test/report correction.

Root full-gate amendment: only the named failed-construction next-ID test in
`tests/test_work_execution.py` may change. Preserve all rollback/ID/completion
assertions, exercising `WorkExecutionSystem.step(engine.state)` directly for
phase-local retry rather than reusing a failed engine. No other work tests or
production work changes. Update report with root gate failure and focused fix.
