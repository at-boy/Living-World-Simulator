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

- make fix
- make check

---

### Batch 2

Add:

- automated tests
- examples

Validate:

- make fix
- make check

Run relevant examples.

---

### Batch 3

Update documentation.

Documentation includes:

- CHANGELOG
- core model
- engine glossary
- project journal

Architectural capabilities also receive an ADR.

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

## Long-Term Goal

The objective is not merely to build a simulation.

The objective is to build a reusable simulation engine that supports
many kinds of living worlds through generic architecture.