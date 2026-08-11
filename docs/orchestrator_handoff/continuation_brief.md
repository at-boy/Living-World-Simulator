# Continuation brief — August 2026

## Project position

- The repository started this effort at version `v0.2.3` and is progressing
  toward `v0.5 – AI Layer`.
- `VERSION` intentionally remains `v0.2.3` until the release-closeout task
  (Task 14). Do not bump it during ordinary feature tasks.
- `CHANGELOG.md` receives feature entries as tasks are completed; final release
  versioning is owned by Task 14.
- The implementation work through Task 13g is committed. The latest relevant
  commit is `3fd1cb2 Clarify local cognition response shape`.

At the completion of Task 13g, validation was:

| Command | Result |
| --- | --- |
| `make` | Passed: Ruff, Black, 339 pytest tests, numbered examples 001–022 |
| `make examples` | Passed: numbered examples 001–022 |
| `git diff --check` | Passed |

Always rerun suitable validation on the current worktree; these figures are a
baseline, not a substitute for review.

## Current worktree and planned pause

The following documentation artifacts were deliberately prepared but were not
implementation work. They describe the next council-quality tasks:

1. **Task 13h — deterministic council turn rotation**
   - Add an explicit, validated `CouncilCall.turn_order_offset: int = 0`.
   - Rotate only confirmed attendees deterministically; do not add randomness
     or LLM-controlled scheduling.
2. **Task 13i — NPC dialogue opening guidance**
   - Ensure an agenda is not represented as previous speech.
   - Give an opening speaker guidance to state a direct position rather than
     replying with phrases such as “I see” to nobody.
3. **Task 13j — manual council scenario and safe context tracing**
   - Improve the local Ollama/llama.cpp council demos with an opaque-ID
     scenario, at least three meaningful actions, longer discussion, and
     nonzero deterministic turn offset.
   - Add opt-in safe diagnostic context output only: filtered `NPCContext` and
     offered actions, never raw world state, IDs, hidden records, or provider
     secrets.
4. **Task 13k — settlement-wide council scenario**
   - Add a shared manual scenario catalog and a concern recognized as requiring
     a town decision rather than originating as the caller's personal issue.
   - Keep the caller as an engine-selected coordinator, not an authoritative
     representative of consensus or owner of the agenda.
5. **Task 13l — opposing-groups council scenario**
   - Demonstrate eligible NPCs with opposed and cross-cutting affiliations,
     several plausible actions, and no forced model decision.
   - Defer factions, voting weights, reputation effects, and political
     consequences.
6. **Task 13m — cognition-shaped council scenario**
   - Seed holder-scoped observations, memories, experiences, beliefs, and
     social knowledge through existing manager-owned interfaces.
   - Use the safe context trace to prove per-NPC isolation while allowing those
     interpretations to influence, but never predetermine, opinions.

The plan ordering in `docs/subagent_execution_plan/README.md` places 13h–13m
before the remaining Task 13a HTTP-inspection coverage and Task 14 release
closeout.

**The user explicitly requested that no task be started yet.** Wait for a new
instruction before delegating or implementing Tasks 13h–13m.

## Council decisions already established

- A council call has a caller, agenda, one or more decision points/actions, and
  invited NPCs. The caller automatically attends.
- A meeting may proceed with fewer than five attendees. Five distinct NPCs are
  a requirement for the manual local-model demonstrations, not a quorum rule.
- An NPC may belong to multiple organizations and have affiliations beyond its
  primary settlement. Eligibility is determined by membership in the target
  organization, not a single home settlement field.
- Invitees may decline. A non-attendee is considered to agree with the majority
  only when they explicitly decline; unavailable, malformed, and no-selection
  results are not delegation.
- Current v0.5 fallback: if every invitee explicitly declines, the caller may
  select one offered action through the normal action gateway. This is a narrow
  temporary policy, not durable governance. ADR-0014 documents it.
- Invitation feedback and diagnostics are transient operator/debug output. They
  are not NPC-visible context and are not persisted world history.
- Council actions remain structured gateway actions. Never put action keys or
  internal IDs into NPC prose merely to make prompting easier.

## Local-model manual example status

The manual examples are intentionally excluded from `make` because they need a
local Ollama or llama.cpp server. Task 13g improved the required structured
response instructions after models repeatedly returned invalid responses.

When the user next runs a manual example, inspect whether invitation feedback
now contains usable reasons/statements. Failures must be displayed as safe,
high-level diagnostics only; never print raw provider payloads, prompts with
hidden data, exception internals, or secrets.

The user wants the manual council output to be a useful debugging tool:

- attendance and caller/invitee roles;
- every invitee's attendance decision and private debug reason;
- debate dialogue and votes;
- eventually a safe opt-in view of exactly the filtered context/action choices
  sent to cognition.

The user also observed these limitations, which are the reason for 13h–13j:
fixed turn order, too-short debate, an unnatural caller opening, and an
underconstrained one-action scenario that makes votes predetermined.

The user additionally requested a small manual scenario suite. Tasks 13k–13m
separate a settlement-origin issue, opposing group interests, and opinions
shaped by private cognitive histories so each can be reviewed as an isolated
task without expanding Task 13j silently.

## Orchestration preferences

- The user prefers task plans and prompts to be saved in the repository so they
  can learn from and audit them.
- A subagent must produce a truthful `-report.md`: exact files changed, public
  interfaces, tests/validation commands and results, boundaries, and blockers.
- Do not claim `make` passes when it does not. Pre-existing out-of-boundary
  failures must be reported and handled by a documented corrective task.
- If a task boundary conflicts with required persistence, tests, or architecture,
  stop and amend the plan/prompt before code is changed.
- The user authorizes the orchestrator to review, request corrections, delegate
  the next documented task, and commit only reviewed, ready work.

## Next work after the pause is lifted

Read the task specifications and saved prompts before action. The anticipated
sequence is 13h -> 13i -> 13j -> 13k -> 13l -> 13m -> 13a -> 14, subject to
user direction and any needed plan amendments.
