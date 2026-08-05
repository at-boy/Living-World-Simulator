# Living World Simulator – Project Journal

This document records the evolution of the project.

Unlike the CHANGELOG, this journal focuses on architectural decisions,
engineering milestones and lessons learned.

---

# 2026-08-05

## Commit 0010

### Property Graph

The runtime model was simplified into a property graph consisting of
Definitions, Entities and Relationships.

The vocabulary of the engine was aligned around:

- Definition
- Entity
- Relationship
- attributes
- definition_key
- initial_attributes

This established a common language for future development.

---

## Commit 0011

### Entity Lifecycle

Entity creation became the responsibility of `EntityManager`.

Runtime entities now have a single creation path, allowing validation,
identifier generation and initial attribute application to be
centralized.

This was the first major lifecycle manager implemented in the engine.

---

## Commit 0012

### Relationship Lifecycle

Relationship creation became the responsibility of
`RelationshipManager`.

Managers are now the exclusive mutation boundary of `WorldState`.

This completed the core lifecycle architecture of the runtime.

The next milestone is recording world history through an
`EventManager`.

## Commit 0013

### World History

The engine gained immutable world history through `Event` and
`EventManager`.

Unlike entities and relationships, events are append-only records.

This completed the four fundamental runtime concepts:

- Definition
- Entity
- Relationship
- Event

The next milestone is executing simulation systems on top of this
runtime.

## Commit 0014

### The World Begins to Evolve

This commit introduced deterministic execution of simulation systems.

The first production system, `ProgressSystem`, demonstrates state
changing over time.

A scheduler now executes registered systems and advances the simulation
tick.

This marks the transition from a static runtime to an evolving
simulation.