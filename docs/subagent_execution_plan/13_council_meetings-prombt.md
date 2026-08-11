# Task 13 — Subagent Prompt

Implement the amended Task 13 plan exactly. Use strict Python 3.13 type hints,
frozen slots dataclasses for public values, Protocol abstractions where needed,
Ruff, Black, and pytest. Do not work outside Task 13.

Key requirements:

- Check `member_of` eligibility engine-side before any attendance context/model
  call. Caller and invitees never appear as IDs in NPC contexts or results.
- Invitation attendance is a filtered local-model proposal: `attend_council`
  or `decline_council`, validated through a dedicated no-mutation attendance
  handler and `NPCActionResolver`. Only an explicit accepted decline delegates
  to the attendee majority; errors/missing responses merely do not attend.
- A council may run below five attendees. Five differentiated,
  attendance-friendly NPC profiles are mandatory only in both opt-in manual
  Ollama and llama.cpp examples; they must never run from `make`.
- Extend conversation/meeting only enough to collect untrusted proposals for a
  council without immediately resolving them. Preserve existing default
  immediate-resolution semantics. Never expose speaker IDs; use safe display
  labels in collected proposal records.
- Tally the first valid agenda proposal per attendee deterministically as the
  plan specifies. Submit a strict-majority winner once to the normal resolver
  with caller as engine-side sponsor; no winner/rejected winner causes no
  mutation. Do not invent domain handlers.
- Update local LLM instructions for starting/running both manual five-NPC
  examples and expected output/failure behaviour.

Create the report, run `make`, `make examples`, `git diff --check`, do not
commit. Only touch Task 13 files, including amended plan/prompt/report, docs,
ADR, and explicitly named integration tests/files.
