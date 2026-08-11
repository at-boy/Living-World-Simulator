# ADR-0013: Bounded Council Coordination

## Status

Accepted

## Decision

Councils are ephemeral orchestrations of the meeting and action-gateway layers.
Membership is checked from the engine-side `member_of` graph before an NPC
context is assembled. Invitees receive only caller-label and agenda prose and
can propose attendance or decline. A decline delegates socially to an eventual
strict attendee majority; it never grants action authority.

The first valid agenda proposal per attendee is tallied by visible action
vocabulary, target label, and arguments. Only a strict attendee majority is
sent once through the ordinary action resolver with the caller as engine-side
sponsor. There is no council primitive, persistent vote, or governance power.

## Consequences

- Any non-empty attendee set can meet.
- A model cannot see IDs, membership scores, another invitee's response, or
  private perspectives.
- Factions, legitimacy, secession, and institutional rules remain future work.
