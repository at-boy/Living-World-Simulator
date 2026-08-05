# ADR-0001: Immutable World History

## Status

Accepted

## Context

The Living World engine requires a mechanism for recording historical
facts.

Future capabilities including NPC memory, observations, beliefs,
debugging, replay and analytics all depend upon reliable history.

## Decision

World history is represented by immutable `Event` objects.

Events are created exclusively through `EventManager.record()`.

Once recorded, an event is never modified or removed.

Corrections are represented by recording new events rather than editing
existing history.

## Consequences

Advantages:

- deterministic history
- replayable simulations
- reliable debugging
- simpler persistence
- foundation for NPC memory

Trade-offs:

- history grows over time
- corrections require additional events instead of editing existing
  records