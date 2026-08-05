# ADR-0003: Simulation Engine as Runtime Façade

## Status

Accepted

## Context

The runtime had grown to include multiple managers, the simulation
scheduler and world state.

Applications required significant setup before a simulation could be
executed.

## Decision

Introduce `SimulationEngine` as the primary public entry point.

The engine composes runtime components and exposes a simplified API for
executing simulations.

Simulation behavior remains implemented by simulation systems rather
than the engine.

## Consequences

Advantages:

- simplified public API
- centralized runtime composition
- clear entry point for applications
- preserves separation of responsibilities

Trade-offs:

- introduces one additional abstraction layer
- advanced users may still need direct access to managers