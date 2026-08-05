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

## Commit 0015

### Public Engine API

This commit introduced `SimulationEngine`, the primary entry point for
applications using the Living World engine.

The engine composes the runtime and exposes a simplified API while
keeping simulation behavior inside simulation systems.

With this commit the core runtime architecture reached its first stable
public interface.

## Commit 0016

### Engineering the Engine

This commit documents how the Living World engine is developed.

The development workflow, architectural decision process and engineering
principles are now documented alongside the codebase.

Existing ADRs were standardized into a consistent format and naming
scheme.

This establishes the project's long-term engineering conventions before
continuing implementation of new simulation capabilities.

## Commit 0017

### Improving the Developer Experience

This commit focused on the project's development workflow rather than the
simulation engine itself.

The default `make` target now performs the complete validation pipeline,
including formatting, static analysis, unit tests and execution of all
examples.

Examples are now treated as executable documentation, ensuring the
public API remains validated alongside the implementation.

Developer tooling was expanded with a snapshot helper to simplify
sharing repository snapshots during architectural reviews.

## Commit 0018

### Generic Bounded Progress

The generic ProgressSystem now supports optional inclusive lower and
upper bounds.

This allows a single reusable mechanism to represent many different
processes including construction, growth, decay and healing without
introducing domain-specific systems.

Dedicated tests verify progression with and without bounds, while the
examples now demonstrate bounded progression through the public
SimulationEngine API.

## Commit 0019

### Resource Definitions

The engine now maintains a registry of resource definitions.

Resources are introduced as part of the simulation vocabulary rather
than as standalone runtime objects. Runtime entities will later reference
registered resource definitions through namespaced attributes such as
`resource.water` and `resource.wood`.

This mirrors the existing separation between entity definitions and
runtime entities and establishes the foundation for future resource
systems.

## Commit 0020

### Entity Resources

Entities can now hold structured resource quantities through the
`resources` attribute.

Resource definitions establish the simulation vocabulary while entities
store the runtime quantities they currently possess.

This provides the foundation for future systems such as production,
consumption, transfer, decay and trade.