# Agent Guide

This file is the concise operating contract for coding agents working in this
repository. Repository state and explicitly authorized task documents remain
authoritative whenever they conflict with summaries.

## Root orchestrator required reading

At the beginning of a new orchestration session, the root orchestrator reads:

1. `docs/orchestrator_handoff/continuation_brief.md`
2. `docs/subagent_execution_plan/v0_6.md`
3. `docs/development_rules.md`
4. `docs/npc_information_boundary.md`

Then inspect:

- `git status --short`
- current branch
- recent commit history
- the currently authorized task plan
- the matching saved `-prombt.md`

Read other architecture, roadmap, backlog, workflow, technical-debt, ADR, or
historical task documents only when the current task creates a concrete need
for them.

The continuation brief is compressed milestone context. Prefer it over
reconstructing completed work from historical task reports.

A documented roadmap item is not authorized merely because it exists.

## Subagent required reading

Subagents do not reconstruct milestone context independently.

Every subagent must read:

1. `AGENTS.md`
2. the exact task material named in its assignment, when applicable
3. only the code, tests, ADRs, and documentation necessary for its assigned
   question

Do not independently read the continuation brief, full roadmap, backlog,
technical-debt ledger, historical task reports, or unrelated ADRs unless the
root orchestrator explicitly asks you to.

The root orchestrator supplies milestone and architectural context required by
the assignment.

## Non-negotiable rules

- Support Python `>=3.11`; development currently uses Python 3.13.5.
- Preserve strict type hints. Prefer `dataclasses` for domain state and
  `typing.Protocol` for abstractions.
- Keep each change to one isolated, documented task and obey its allowed-file
  boundary. Amend the task and saved prompt before expanding that boundary.
- Every implementation task requires its milestone plan, saved prompt ending
  in `-prombt.md`, and orchestrator report ending in `-report.md`.
- Review delegated work independently. Require corrections for implementation,
  test, report, boundary, or validation deficiencies.
- Before approving or committing implementation work, run the repository's
  current required validation, including `make`, `make examples`, and
  `git diff --check` unless current authoritative task documents supersede it.
- Report failures truthfully. Do not paste successful command output; record
  command, result, counts, and meaningful warnings only.
- Follow `docs/development_rules.md` for changelog, journal, backlog, review,
  and commit requirements.
- Do not replace established architecture merely to simplify a new feature.
- Managers own mutation, systems own behavior, and events are immutable.
- Do not begin a milestone, task, branch, or implementation without explicit
  authorization.
- Never commit, merge, or push v0.6 work to `main`.

## NPC information and authority boundary

Preserve this flow:

```text
WorldState
  -> perception
  -> immutable cognitive records
  -> filtered NPC context
  -> cognition proposal
  -> action gateway
  -> world event/state change
```

NPC-facing prompts and contexts must never receive raw `WorldState`, internal
record or entity IDs, unrestricted attributes, hidden cognitive records owned
by other NPCs, or arbitrary runtime objects.

LLM output is untrusted and remains a proposal until the simulation validates
and executes it through the action gateway.

The simulation remains authoritative over world truth, goals, objective
completion, and settlement-stage progression.

## Codex orchestration strategy

The primary/root agent is the orchestrator and retains responsibility for:

- authorization
- architecture
- scope
- task-contract decisions
- integration
- reviewer-finding disposition
- validation
- branch/task transitions
- final completion decisions

Use subagents only when they improve confidence, parallel investigation,
independent review, or context efficiency.

Do not delegate trivial work merely to use agents.

Subagents provide evidence, implementation, and review findings. They do not
replace the root agent's architectural judgment or completion responsibility.

### Investigation before implementation

Do not perform broad repository exploration by default.

Before a non-trivial cross-subsystem implementation, use independent read-only
investigations only when they resolve concrete uncertainties.

Useful investigation angles include:

1. domain ownership, authoritative mutation paths, managers/systems, and
   scheduler ordering;
2. persistence, schema, migration, rollback, and inspection implications;
3. tests, examples, NPC-visible information boundaries, and LLM trust
   boundaries.

Do not delegate repository-wide exploration when the question can be
decomposed into narrower independent investigations.

Give each explorer a narrow question and ask for:

- conclusion
- concrete paths and symbols
- contract implications
- relevant tests
- risks
- unresolved questions

Do not ask explorers to summarize files or restate the task.

Explorer reports should normally stay under 800 words.

The root agent reconciles findings itself before implementation.

Subagent findings are evidence, not architectural decisions.

If findings conflict, resolve the conflict from repository evidence before
continuing.

### Decision-complete task contracts

Delegate implementation only after the explicitly authorized task contract is
decision-complete.

Where applicable, the task contract should make explicit:

- intended behavior and non-goals
- authoritative owner of state and mutation path
- manager and system responsibilities
- scheduler or phase ordering
- event contracts
- deterministic arithmetic or ordering rules
- validation, failure, and rollback semantics
- persistence, schema, and migration implications
- inspection/API implications
- NPC-visible translation and hidden engine-only information
- required tests, examples, and documentation
- allowed-file and ownership boundaries

If an important architectural choice remains implicit, investigate and amend
the authorized task artifacts before implementation rather than allowing a
worker to choose architecture independently.

### Implementation delegation

Prefer one worker for one coherent bounded task.

Give the worker only the context necessary to execute it:

- exact objective
- architectural decisions already made
- allowed scope/files
- required invariants
- relevant starting paths/symbols
- focused tests
- non-goals

Multiple implementation workers may run concurrently only when file and
ownership boundaries are clearly non-overlapping.

Avoid concurrent writers touching the same files.

Workers must not expand scope merely because they discover adjacent
improvements. Record unrelated discoveries for later.

The root agent retains responsibility for architecture and integration.

### Independent review

Non-trivial delegated implementation requires independent read-only review.

The reviewer should inspect only:

- `AGENTS.md`
- the authorized task contract
- the saved task prompt
- the actual diff
- the implementation report
- directly relevant code/tests

The reviewer does not reconstruct milestone history.

Review against the task contract and repository invariants, not merely code
style or passing tests.

Check where relevant:

- allowed-file compliance
- manager/system ownership
- immutable event semantics
- deterministic behavior and scheduler ordering
- persistence/schema/migration correctness
- validation and rollback behavior
- NPC information boundaries
- simulation authority
- LLM trust boundaries
- regression-test quality
- report/documentation accuracy

If there are no substantive findings, report a concise
`NO SUBSTANTIVE FINDINGS` conclusion rather than narrating correct code.

If review finds substantive issues, resolve them with narrowly scoped
corrections and review the resulting diff again.

### Task sizing

For small tasks:

- the root agent normally handles the task directly
- use focused validation
- no subagent is required

For medium tasks:

- use 0-1 explorers when useful
- the root agent synthesizes a decision-complete contract
- use one implementation worker
- use one independent reviewer

For large or architectural tasks:

- use only the minimum number of parallel independent explorers needed
- the root agent synthesizes architecture and the task contract
- use bounded workers only when ownership/file scopes do not overlap
- require independent review
- the root agent resolves findings and performs authoritative final validation

### Validation strategy

During implementation and corrections, use the smallest relevant focused test
set for rapid feedback.

Run the full repository validation only after implementation and independent
review are otherwise ready.

Do not paste successful test output into reports or conversation.

Record only:

- command
- result
- counts
- meaningful warnings/failures

### Context discipline

Protect the root orchestrator's context window.

Prefer targeted searches over reading whole directories.

Prefer symbols and paths over file dumps.

Do not repeatedly reread:

- completed task plans/reports
- full backlog
- full roadmap
- technical-debt history
- historical milestone archives

Read them only when a current decision depends on them.

After a task is reviewed, validated, and merged, treat:

- its reviewed `-report.md`
- merge commit
- updated continuation brief

as compressed canonical history.

Do not carry detailed implementation discussion from completed tasks into the
next task unless the next contract requires it.

### Session checkpointing

Do not keep one root session alive merely to preserve history.

Use the continuation brief as a context-compression artifact.

Prefer fresh root-orchestrator sessions at major task boundaries when context
has accumulated significantly.

Recommended remaining v0.6 grouping:

- one session for Task 20b
- one session for Tasks 21-22
- one session for Tasks 15-15c
- one session for Task 23
- one session for Task 24

The current repository state determines the actual authorized task sequence.

### Completion responsibility

Workers and reviewers report evidence and findings.

The root agent alone decides that an authorized task is complete,
independently reviewed, fully validated, truthfully reported, and ready for the
next authorized transition.

## Working practice

- Treat existing user changes as owned work; do not overwrite or discard them.
- Inspect current interfaces and tests before making architectural decisions.
- Keep persistence, lifecycle ownership, inspection, tests, examples, and
  documentation inside the approved task design rather than bolting them on
  later.
- If an NPC-visible pathway changes, document engine truth, perception,
  transformation, hidden fields, memory, inference, LLM context, and
  engine-only data before implementation.
- Commit only focused work that has passed independent review and required
  validation.
