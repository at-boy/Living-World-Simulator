# Agent Guide

This file is a concise entry point for coding agents working in this
repository. It does not replace the project documentation. The
repository and the authoritative documents listed below override this
summary whenever they conflict with it.

## Required reading

Before planning, editing, delegating, or committing, read these
documents in full:

1.  `docs/orchestrator_handoff/continuation_brief.md`
2.  `docs/subagent_execution_plan/README.md`
3.  `docs/backlog.md`
4.  `docs/architectural_direction.md`
5.  `docs/development_rules.md`
6.  `docs/npc_information_boundary.md`
7.  `docs/technical_debt.md`
8.  `docs/post_v05_settlement_evolution_roadmap.md`
9.  `docs/development_workflow.md`
10. `docs/subagent_execution_plan/v0_6.md`

Also read the overview and task artifacts for whichever milestone and
task the user explicitly authorizes.

Then inspect `git status --short`, recent commit history, the active
branch, and the next explicitly authorized task. A documented task or
roadmap item is not authorized merely because it exists.

## Non-negotiable rules

-   Support Python `>=3.11`; development currently uses Python 3.13.5.
-   Preserve strict type hints. Prefer `dataclasses` for domain state
    and `typing.Protocol` for abstractions.
-   Keep each change to one isolated, documented task and obey its
    allowed-file boundary. Amend the task and saved prompt before
    expanding that boundary.
-   Every implementation task requires a milestone plan, a saved prompt
    ending in `-prombt.md`, and an orchestrator report ending in
    `-report.md`.
-   Review delegated work independently. Require corrections for
    implementation, test, report, boundary, or validation deficiencies.
-   Before approving or committing implementation work, run `make`,
    `make examples`, and `git diff --check`. Report failures truthfully.
-   Follow `docs/development_rules.md` for changelog, journal, backlog,
    review, and commit requirements.
-   Do not replace established architecture merely to simplify a new
    feature.
-   Managers own mutation, systems own behavior, and events are
    immutable.
-   Do not begin a milestone, task, branch, or implementation without
    explicit authorization. v0.6 is currently authorized only through
    its documented, dependency-ordered task sequence on
    `milestone/v0.6`; later milestones remain unauthorized. Never
    commit, merge, or push v0.6 work to `main`.

## NPC information and authority boundary

Preserve this flow:

``` text
WorldState
  -> perception
  -> immutable cognitive records
  -> filtered NPC context
  -> cognition proposal
  -> action gateway
  -> world event/state change
```

NPC-facing prompts and contexts must never receive raw `WorldState`,
internal record or entity IDs, unrestricted attributes, hidden cognitive
records owned by other NPCs, or arbitrary runtime objects. LLM output is
untrusted and remains a proposal until the simulation validates and
executes it through the action gateway. The simulation remains
authoritative over world truth, goals, objective completion, and
settlement-stage progression.

## Codex orchestration strategy

The primary/root agent is the orchestrator and retains responsibility
for architecture, scope, authorization, integration, validation, and the
final result.

Use subagents when they improve confidence, parallel investigation,
independent review, or context efficiency. Do not delegate trivial work
merely to use agents.

Subagents provide evidence, implementation, and review findings. They do
not replace the root agent's architectural judgment or completion
responsibility.

### Investigation before implementation

Before a non-trivial cross-subsystem implementation, use independent
read-only investigations when they can resolve separate questions in
parallel.

Useful investigation angles include:

1.  Domain ownership, authoritative mutation paths, managers/systems,
    and scheduler ordering.
2.  Persistence, schema, migration, rollback, and inspection
    implications.
3.  Tests, examples, NPC-visible information boundaries, and LLM trust
    boundaries.

Do not delegate repository-wide exploration when the question can be
decomposed into narrower independent investigations.

Give each explorer a narrow question and ask for concrete paths,
symbols, ownership, relevant tests, risks, and unresolved questions
rather than broad repository summaries.

The root agent must reconcile subagent findings itself before
implementation. Subagent findings are evidence, not architectural
decisions.

If findings conflict, resolve the conflict from repository evidence
before continuing.

### Decision-complete task contracts

Delegate implementation only after the explicitly authorized task
contract is decision-complete.

Where applicable, the task contract should make the following explicit:

-   intended behavior and non-goals;
-   authoritative owner of state and mutation path;
-   manager and system responsibilities;
-   scheduler or phase ordering;
-   event contracts;
-   deterministic arithmetic or ordering rules;
-   validation, failure, and rollback semantics;
-   persistence, schema, and migration implications;
-   inspection/API implications;
-   NPC-visible translation and hidden engine-only information;
-   required tests, examples, and documentation;
-   allowed-file and ownership boundaries.

If an important architectural choice remains implicit, investigate and
amend the authorized task artifacts before implementation rather than
allowing a worker to choose the architecture independently.

### Implementation delegation

Prefer one worker for one coherent bounded task.

Give each worker a specific objective, relevant architectural decisions,
explicit scope boundaries, required invariants, expected validation, and
non-goals.

Multiple implementation workers may run concurrently only when their
work has clearly non-overlapping file and ownership boundaries.

Avoid multiple workers modifying the same files concurrently.

Workers must not expand scope merely because they discover adjacent
improvements. Record unrelated discoveries for later rather than
silently implementing them.

The root agent retains responsibility for architecture and integration.

### Independent review

Non-trivial delegated implementation requires independent read-only
review.

Review against the authorized task contract, saved prompt,
implementation report, actual diff, and repository architectural
invariants, not merely code style or passing tests.

Review should check, where relevant:

-   task-contract and allowed-file compliance;
-   manager/system ownership and immutable event semantics;
-   deterministic behavior and scheduler ordering;
-   persistence, schema, migration, validation, and rollback
    correctness;
-   NPC information and simulation-authority boundaries;
-   LLM trust boundaries;
-   regression-test quality;
-   report and documentation accuracy.

If review finds substantive issues, resolve them with narrowly scoped
corrections and review the resulting diff again.

### Task sizing

For small tasks:

-   the root agent normally handles the task directly;
-   use focused validation;
-   no subagent is required.

For medium tasks:

-   use 1-2 explorers when useful;
-   the root agent synthesizes a decision-complete contract;
-   use one implementation worker;
-   use one independent reviewer.

For large or architectural tasks:

-   use parallel independent explorers where useful;
-   the root agent synthesizes the architecture and task contract;
-   use bounded workers only when their ownership/file scopes do not
    overlap;
-   require independent review;
-   the root agent resolves findings and performs authoritative final
    validation.

### Context discipline

Protect the root orchestrator's context window.

Delegate broad searching and bounded investigation when useful, but
request concise reports rather than large file dumps. Prefer concrete
paths, symbols, behavior, tests, risks, and unresolved questions.

Use the root context primarily for architectural reasoning,
task-contract decisions, integration, review findings, validation, and
final decisions.

### Completion responsibility

Workers and reviewers report evidence and findings.

The root agent alone is responsible for deciding that an authorized task
is complete, independently reviewed, fully validated, and truthfully
reported.

## Working practice

-   Treat existing user changes as owned work; do not overwrite or
    discard them.
-   Inspect current interfaces and tests before making architectural
    decisions.
-   Keep persistence, lifecycle ownership, inspection, tests, examples,
    and documentation inside the approved task design rather than
    bolting them on later.
-   If an NPC-visible pathway changes, document engine truth,
    perception, transformation, hidden fields, memory, inference, LLM
    context, and engine-only data before implementation.
-   Commit only focused work that has passed independent review and the
    required validation.
