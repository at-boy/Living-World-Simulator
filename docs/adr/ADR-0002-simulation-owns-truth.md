# Simulation Owns Truth

## Status

Accepted

## Context

The Living World engine is responsible for maintaining authoritative
simulation state.

Future integrations with language models require a clear separation
between deterministic simulation and probabilistic reasoning.

## Decision

The simulation owns all canonical world state.

Language models never create authoritative facts.

Instead, they reason over facts supplied by the engine and produce
decisions or interpretations based on that information.

## Consequences

Advantages:

- deterministic simulation
- reproducible world state
- easier debugging
- reliable persistence
- language models remain interchangeable

Trade-offs:

- all canonical state must originate from engine systems
- additional translation is required between engine state and language
  model prompts