# Task 13d — Council invitation action-selection report

## Result

Council invitation context now includes this validated, NPC-safe instruction:

> Council invitation from Erik: a careful route. In action_request, return
> exactly one offered attendance action. Include a short reason in that action
> request's rationale. A statement by itself is not an attendance selection.

The caller label and agenda topic vary per call. Action keys remain only in the
separate structured action vocabulary supplied to the cognition client, not in
validated invitation prose: `attend_council` includes the current world's
internal organization identifier, `council`. The prose is passed through
`NPCContextAssembler.validate_conversation_prose` before context assembly.

## Evidence

`test_council_invitation_action_selection.py` captures every invitee context
and proves the exact instruction reaches each one without internal entity IDs,
relationship identifiers, raw attributes, authoritative numbers, or action-key
literals. It also proves submitted attendance action requests use the ordinary
resolver and produce ATTENDING/DECLINED feedback with normal meeting flow.
Their safe rationales remain available only through the pre-existing, filtered
transient feedback field; they are not world state, persistence, events, or
downstream NPC context.

A statement with `action_request=None` remains `NO_SELECTION`, does not attend
or delegate, and produces no meeting. The engine does not infer an attendance
choice from that prose, retry a request, or fabricate a decision.

## Validation

Passed before handoff:

- `PYTHONPATH=src .venv/bin/pytest tests/test_council.py tests/test_council_invitation_action_selection.py tests/test_council_invitation_feedback.py tests/test_npc_information_boundary.py`
- `make`
- `make examples`
- `git diff --check`

The focused council and information-boundary suite, `make`, `make examples`,
and `git diff --check` pass. Literal action keys intentionally remain in the
structured action vocabulary rather than validated invitation prose, preserving
the mandatory internal-identifier boundary without changing it.

## Files and boundaries

Changed only the Task 13d council implementation, its specified tests and
documentation, plus this report. No cognition client, response schema,
decision engine, action resolver, feedback type, manual example, persistence,
HTTP API, Makefile, task plan, retry, inference, hidden prompt data, logging,
world mutation, or event behavior changed.

## Known limitation

Explicit local-model guidance improves compliance but cannot guarantee it.
Local model responses remain probabilistic; a missing, malformed, or
unavailable action request still remains non-authoritative.
