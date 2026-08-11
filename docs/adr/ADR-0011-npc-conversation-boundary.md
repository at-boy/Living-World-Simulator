# ADR-0011: NPC Conversation Boundary

## Status

Accepted

## Context

NPC dialogue is useful as a visible social interaction, but a transcript can
become an accidental route for private cognition, entity identifiers, raw
state, or model-claimed actions to cross between participants.

## Decision

`ConversationService` receives internal participant identifiers only to
assemble separate, holder-scoped `NPCContext` values and to record recipient
observations. Before any model call it validates participants, topic, and turn
bound. The only conversation history made visible to a model is a validated
topic preamble followed by prior visible utterance prose.

Each utterance is boundary-validated before recording it as an observation for
the other participants. Observation evidence and metadata are empty. A
conversation does not directly create a memory, belief, experience,
relationship, event, or fact. Any model action proposal is still submitted to
the separate `NPCActionResolver` with the internal actor identifier; neither
the identifier nor its resolution is supplied to a model.

## Consequences

- Participants can later remember recorded speech through the normal
  consolidation path.
- Private cognition remains holder-scoped even during multi-participant turns.
- Dialogue stays non-authoritative until an explicit domain action handler
  accepts and applies a proposal.
