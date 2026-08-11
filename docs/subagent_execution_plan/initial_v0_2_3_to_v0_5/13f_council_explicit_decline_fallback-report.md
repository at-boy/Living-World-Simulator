# Task 13f Report — Explicit-Decline Caller Fallback

## Policy proof

`CouncilService` enables the fallback only for a non-empty invitation set whose
feedback is unanimously `DECLINED` and whose accepted attendance selections
delegate. Council calls retain their non-empty-invitee contract. `UNAVAILABLE`,
`NO_SELECTION`, attendees, mixed results, and fallback abstention produce no
fallback action.

The focused unavailable case supplies a genuine `NPCCognitionClientError` for
one invitee and an explicit decline for another. It verifies `UNAVAILABLE` plus
`DECLINED` feedback, exactly two invitee decisions, no caller decision, no
proposal or resolution, no handler application, and no event mutation.

## Gateway and boundary evidence

The sole fallback proposal is obtained from the caller with the ordinary agenda
vocabulary and submitted once to the existing `NPCActionResolver` using the
caller as actor. The caller receives only a boundary-validated aggregate notice
that every invitee explicitly declined and delegated, plus its own permissible
context; identities, reasons, IDs, scores, and raw replies are absent.
Manual output calls this a `Caller fallback proposal`, never a majority proposal.

## ADR and deferrals

ADR-0014 records this temporary v0.5 policy. Per-organization governance,
auditable records, contested invitation/deception work, and persistent social
effects remain deferred.

## Validation

`make` passed with 330 tests; `make examples` passed all examples twice (the
target's two configured runs); `git diff --check` passed. Ruff and Black pass
through `make`. No persistent governance, relationship, event, or state
mutation was introduced by this task.

## Changed files

- `CHANGELOG.md`
- `docs/adr/ADR-0014-council-explicit-decline-fallback.md`
- `docs/backlog.md`
- `docs/core_model.md`
- `docs/engine_glossary.md`
- `docs/local_llm_setup.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13f_council_explicit_decline_fallback-report.md`
- `examples/manual/llama_cpp_council_meeting.py`
- `examples/manual/ollama_council_meeting.py`
- `src/living_world/cognition/__init__.py`
- `src/living_world/cognition/council.py`
- `tests/test_council_explicit_decline_fallback.py`
- `tests/test_council_invitation_action_selection.py`
- `tests/test_manual_council_examples.py`
