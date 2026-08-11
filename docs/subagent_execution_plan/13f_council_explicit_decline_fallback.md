# 13f — Explicit-decline caller fallback

## Task Description

Add a narrow v0.5 council policy: when a council has at least one invited NPC
and **every** invitee explicitly selects `decline_council`, the caller may make
one fallback agenda proposal. That proposal remains non-authoritative until the
ordinary action gateway accepts it. This represents deliberate delegation, not
silence, provider failure, or an automatic right to rule.

## Context Needed

- Create: `docs/subagent_execution_plan/13f_council_explicit_decline_fallback-report.md`,
  `tests/test_council_explicit_decline_fallback.py`, and an ADR documenting the
  temporary v0.5 policy and its future replacement by organization-specific
  governance rules.
- Edit: `src/living_world/cognition/council.py`,
  `src/living_world/cognition/__init__.py`, `tests/test_council.py`,
  `tests/test_manual_council_examples.py`, both manual council examples,
  `docs/local_llm_setup.md`, `docs/core_model.md`, `docs/engine_glossary.md`,
  `docs/backlog.md`, `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: Task 13c invitation feedback, Task 13d action-selection guidance,
  Task 11 action gateway, and the strict NPC information boundary.

## Interface Contract

```python
class CouncilDecisionBasis(StrEnum):
    ATTENDEE_MAJORITY = "attendee_majority"
    EXPLICIT_DECLINE_CALLER_FALLBACK = "explicit_decline_caller_fallback"

@dataclass(frozen=True, slots=True)
class CouncilResult:
    attendance: tuple[CouncilAttendance, ...]
    conversation: ConversationResult
    majority_proposal: ActionRequest | None
    resolutions: tuple[ActionResolution, ...]
    invitation_feedback: tuple[CouncilInvitationFeedback, ...] = ()
    decision_basis: CouncilDecisionBasis | None = None
```

- Fallback is available only when `invited_participant_ids` is non-empty and
  every invitee has `CouncilInvitationStatus.DECLINED` plus
  `delegates_to_majority=True`. `UNAVAILABLE`, `NO_SELECTION`, malformed
  responses, mixed attendance, a caller-only call, or caller self-delegation
  never enable it.
- In that case only, the engine supplies the caller an NPC-safe aggregate
  policy fact: every invited participant explicitly declined and delegated;
  the caller may submit one offered agenda proposal, which is subject to normal
  simulation validation. It does not expose identities, rationales, IDs,
  scores, or raw responses.
- The fallback decision may be absent. No fallback action request means no
  resolution and no mutation. An accepted fallback action uses the caller as
  actor through the ordinary resolver exactly once; a rejected request has no
  state change.
- The invitation likewise states the true policy in safe prose: an explicit
  decline delegates only if all invitees explicitly decline; it does not state
  that an unavailable/no-selection NPC agreed.
- The result basis makes the operator-visible distinction clear in manual
  output. No new persistent council/governance record is created.

## Test Criteria

- All explicit declines enable exactly one caller fallback decision and normal
  gateway submission; tests show the caller sees only safe aggregate delegation
  context and its own permissible context.
- Mixed decline/no-selection, unavailable, any attendee, no invitees, and a
  caller fallback abstention create no fallback action or state change.
- Manual output identifies fallback basis without exposing individual invitee
  reasons as caller context.
- Full boundary, action-gateway, event/persistence, examples, and `make`
  validation pass.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13f_council_explicit_decline_fallback-report.md`.
Report explicit-decline policy proof, fallback action-gateway evidence, safe
caller/invitee context evidence, ADR decision, tests/commands/results, files,
boundary compliance, and deferred per-organization governance/deception work.

## Boundary

- Touch only stated council/export/tests/manual examples/docs/ADR/report files.
- Do not add persistent governance, relationship changes, votes, events,
  automatic approval, raw model output, internal IDs, per-organization rules,
  invitation auditing, deception mechanics, or settlement secession.
- Preserve normal action validation and all NPC information-boundary rules.
