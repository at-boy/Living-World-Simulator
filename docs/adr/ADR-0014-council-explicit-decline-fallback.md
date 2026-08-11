# ADR-0014: Council Explicit-Decline Caller Fallback

## Status

Accepted

## Decision

As a temporary v0.5 council policy, a caller may submit one offered agenda
proposal only when a non-empty invitee set has unanimously and explicitly
selected the accepted `decline_council` action. The caller receives only the
aggregate NPC-safe statement that every invitee explicitly declined and
delegated. The request is submitted once with the caller as actor through the
ordinary action resolver; it remains non-authoritative until that resolver
accepts it.

Unavailable, malformed, no-selection, mixed attendance, caller-only calls, and
caller self-delegation do not enable fallback. No fallback proposal produces no
resolution or state mutation.

## Consequences

- The policy does not create a vote, governance record, event, relationship, or
  persistent delegation state.
- Invitee identities, rationales, IDs, scores, and raw model replies are not
  supplied to the caller.
- Organization-specific eligibility, quorum, delegation, and authority rules,
  plus deception and contested-participation mechanics, remain future work.
