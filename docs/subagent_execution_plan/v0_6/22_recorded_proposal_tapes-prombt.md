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
