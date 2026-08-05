# ADR-0002: Deterministic Simulation Execution

## Status

Accepted

## Context

The simulation requires a predictable mechanism for executing systems
each tick.

Deterministic execution is essential for debugging, replay,
reproducibility, and testing.

## Decision

Simulation systems execute in the order they are registered.

After all systems have executed for the current tick, the scheduler
advances the world tick.

The scheduler is responsible only for execution order and tick
advancement.

Simulation systems own all simulation behavior.

## Consequences

Advantages:

- deterministic simulations
- reproducible debugging
- simpler replay
- predictable system interactions

Trade-offs:

- developers must consider registration order when composing
  simulations