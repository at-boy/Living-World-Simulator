# Agent Guide

This file is a concise entry point for coding agents working in this
repository. It does not replace the project documentation. The repository and
the authoritative documents listed below override this summary whenever they
conflict with it.

## Required reading

Before planning, editing, delegating, or committing, read these documents in
full:

1. `docs/orchestrator_handoff/continuation_brief.md`
2. `docs/subagent_execution_plan/README.md`
3. `docs/backlog.md`
4. `docs/architectural_direction.md`
5. `docs/development_rules.md`
6. `docs/npc_information_boundary.md`
7. `docs/technical_debt.md`
8. `docs/post_v05_settlement_evolution_roadmap.md`
9. `docs/development_workflow.md`
10. `docs/subagent_execution_plan/v0_6.md`

Also read the overview and task artifacts for whichever milestone and task the
user explicitly authorizes.

Then inspect `git status --short`, recent commit history, the active branch,
and the next explicitly authorized task. A documented task or roadmap item is
not authorized merely because it exists.

## Non-negotiable rules

- Support Python `>=3.11`; development currently uses Python 3.13.5.
- Preserve strict type hints. Prefer `dataclasses` for domain state and
  `typing.Protocol` for abstractions.
- Keep each change to one isolated, documented task and obey its allowed-file
  boundary. Amend the task and saved prompt before expanding that boundary.
- Every implementation task requires a milestone plan, a saved prompt ending
  in `-prombt.md`, and an orchestrator report ending in `-report.md`.
- Review delegated work independently. Require corrections for implementation,
  test, report, boundary, or validation deficiencies.
- Before approving or committing implementation work, run `make`,
  `make examples`, and `git diff --check`. Report failures truthfully.
- Follow `docs/development_rules.md` for changelog, journal, backlog, review,
  and commit requirements.
- Do not replace established architecture merely to simplify a new feature.
- Managers own mutation, systems own behavior, and events are immutable.
- Do not begin a milestone, task, branch, or implementation without explicit
  authorization. v0.6 is currently authorized only through its documented,
  dependency-ordered task sequence on `milestone/v0.6`; later milestones remain
  unauthorized. Never commit, merge, or push v0.6 work to `main`.

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
by other NPCs, or arbitrary runtime objects. LLM output is untrusted and
remains a proposal until the simulation validates and executes it through the
action gateway. The simulation remains authoritative over world truth, goals,
objective completion, and settlement-stage progression.

## Working practice

- Treat existing user changes as owned work; do not overwrite or discard them.
- Inspect current interfaces and tests before making architectural decisions.
- Keep persistence, lifecycle ownership, inspection, tests, examples, and
  documentation inside the approved task design rather than bolting them on
  later.
- If an NPC-visible pathway changes, document engine truth, perception,
  transformation, hidden fields, memory, inference, LLM context, and
  engine-only data before implementation.
- Commit only focused work that has passed independent review and the required
  validation.
