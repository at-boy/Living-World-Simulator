# ADR-0010: NPC Action Authority Gateway

## Status

Accepted

## Context

An NPC LLM can reason from a filtered `NPCContext` and propose an offered
action, but it cannot be trusted to decide whether that action is legal,
possible, or successful. Direct model access to actors, world state, managers,
or events would violate the simulation-authority and NPC-information
boundaries.

## Decision

`DecisionEngine` invokes an `NPCCognitionClient` with only `NPCContext` and
the explicitly offered `ActionOption` vocabulary. It validates the returned
`NPCDecision` again so a direct or fake client cannot bypass offered action-key
and target-label constraints.

`NPCActionResolver` receives an engine-only `actor_id` separately. It repeats
vocabulary validation, locates a domain `NPCActionHandler`, calls its
non-mutating `validate()` method, and calls `apply()` only after an accepted
validation result. The resolver has no default domain handlers and creates no
generic events. A handler owns any manager mutation and its single domain
event after successful application.

`SimulationEngine.resolve_npc_action()` is the narrow engine-owned delegation
entry point. It does not compose cognition or send its actor ID to an LLM.

## Consequences

Advantages:

- LLM output remains an untrusted proposal rather than world truth.
- Domain modules can add explicit handlers without expanding the LLM boundary.
- Rejected proposals cannot enter a handler mutation path or create a gateway
  event.

Trade-offs:

- A future domain action must supply its own handler, manager mutation, and
  event policy.
- A handler that rejects from `apply()` violates this protocol and raises a
  handler-contract error; handlers must validate before applying.
