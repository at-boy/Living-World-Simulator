# Living World Development Workflow

## Purpose

This document describes how the Living World engine is engineered.

The goal is to keep the architecture simple, coherent and maintainable
as the project grows.

---

## Core Philosophy

The engine is developed incrementally.

Each commit introduces exactly one new capability.

Capabilities are discussed before implementation and validated through
tests and examples before being committed.

Large architectural changes are intentionally divided into small,
reviewable steps.

---

## Milestone and Task Branch Workflow

Beginning with the authorized v0.6 autonomous-founding-settlement milestone,
development uses a two-level branch workflow:

```text
main
  └── milestone/v0.6
        ├── task/16-scenario-run-contract
        ├── task/16a-runner-checkpoint-resume
        └── task/17-external-world-references
```

- `main` is the stable reviewed release line. Normal feature work is not
  committed directly to it.
- One `milestone/vX.Y` integration branch owns each active roadmap milestone.
  “Milestone” is used instead of “major version” because `v0.6`, `v0.7`, and
  similar releases are minor-version milestones.
- Every isolated implementation task uses a short-lived `task/<task>-<slug>`
  branch created from the active milestone branch. Its correction cycles stay
  on that same task branch.
- A task branch returns to the milestone branch only after independent review,
  its report, boundary audit, `make`, `make examples`, and `git diff --check`
  pass. The milestone branch must remain usable between merges.
- Dependent tasks are merged in documented order. A task branch must not use an
  unmerged sibling branch as an informal dependency; amend the plan and merge
  the prerequisite first.
- Release closeout runs on the milestone branch. Once accepted, the milestone
  is merged into `main` and tagged. The next milestone branch starts from that
  reviewed `main` state.
- Urgent release fixes branch from `main` as `fix/<slug>` and are also brought
  into any active milestone branch when applicable.
- Planning documents may describe future branches but creating a branch does
  not authorize its task or broaden its allowed-file boundary.
- For v0.6, the user authorizes the orchestrator to push the milestone and task
  branches and to merge reviewed task branches into `milestone/v0.6`. The
  orchestrator must not commit, merge, or push to `main`; final milestone
  integration remains a separately authorized owner action.

Only one milestone integration branch should normally be active. This avoids
long-lived version branches drifting apart while still isolating individual
features and their review history.

---

## Engineering Principles

### The engine understands structure, not meaning.

Generic engine components understand structural concepts such as
entities, relationships, events and simulation systems.

Domain concepts such as farms, kingdoms, bridges and NPCs are built on
top of those generic structures.

---

### Infrastructure before specialization.

Reusable infrastructure is implemented before domain-specific behavior.

Examples:

- Entity before NPC
- Relationship before Road
- ProgressSystem before Farming
- SimulationScheduler before Weather

---

### Managers own mutation.

World state is modified only through managers.

Simulation systems use managers rather than mutating world state
directly.

---

### Systems own behavior.

Simulation behavior belongs inside simulation systems.

The scheduler executes systems but never implements simulation logic.

The engine composes the runtime but does not contain simulation rules.

---

### Events are immutable.

History is append-only.

Corrections are represented by new events rather than modifying existing
history.

---

### Generic systems change state.

Specialized systems interpret state.

For example, ProgressSystem advances progress values.

Construction, farming and decay interpret what those values mean.

---

## Capability Development

Every capability is developed in three batches.

### Batch 1

Implement the capability.

Validate:

- `make`

---

### Batch 2

Add:

- automated tests
- examples

Validate:

- `make`

---

### Batch 3

Update documentation.

Documentation includes:

- CHANGELOG
- core model
- engine glossary
- project journal

Architectural capabilities also receive an ADR.

Validate:

- `make`

---

## Architecture Decision Records

ADRs document architectural decisions that have already been implemented.

Every ADR follows the same structure:

- Status
- Context
- Decision
- Consequences

ADRs describe decisions.

They do not describe implementation details.

---

## Repository Review

Before beginning a new architectural capability, review the current
repository.

Architectural decisions should be based upon the current implementation
rather than memory.

Repository snapshots should exclude generated files and caches.

---

## Testing

Every manager receives dedicated unit tests.

Every simulation component receives dedicated unit tests.

Examples serve as executable documentation.

---

## Executable Documentation

Examples are maintained as executable documentation.

Every example must execute successfully as part of the normal development
workflow.

The `make` target executes all examples after formatting and testing,
providing an additional validation step for the public API.

---

## Long-Term Goal

The objective is not merely to build a simulation.

The objective is to build a reusable simulation engine that supports
many kinds of living worlds through generic architecture.
