# ADR-0012: NPC Meeting Coordination

## Status

Accepted

## Context

Multi-party dialogue needs a small engine-owned coordination layer before a
future council can define attendance, authority, or governance. The layer must
not accidentally turn an NPC request into a persistent social record or leak
participant identifiers and private perspectives into an NPC context.

## Decision

`MeetingRequest` is an immutable engine-side request containing internal
requester, invitee, and optional speaker-schedule identifiers. `MeetingService`
checks known requester/invitees, requester non-self-invitation, and distinct
invitees, then delegates its requester-first participant order to
`ConversationService`.

The optional speaker schedule is engine-only. An omitted schedule preserves
cyclic conversation order; a supplied schedule lists each model call and may
repeat an eligible participant. A participant's optional qualitative
perspective is validated through the existing information boundary and is
supplied only as that speaker's `NPCContext.self_knowledge`.

## Consequences

- Meetings have no persistent object, invitation, consent, availability,
  relationship, event, or policy result.
- The existing conversation observation and action-proposal boundaries apply
  unchanged to every meeting turn.
- Council attendance, agendas, voting, and governance remain separate work.
