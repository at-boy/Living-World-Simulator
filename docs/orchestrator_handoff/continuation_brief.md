# Continuation brief — August 2026

## Project position

- The repository started this effort at version `v0.2.3` and completed
  `v0.5 – AI Layer` in Task 14.
- The authoritative release surfaces now consistently report `0.5.0` after the
  focused Task 14b correction and Task 14 closeout.
- The complete Task 01–14, Task 14b, and Task 14a execution history is archived
  under
  `docs/subagent_execution_plan/initial_v0_2_3_to_v0_5/`; the root README is
  the cross-milestone index.
- Task 14a completed the milestone reorganization in commit `6dbf0ef`. The
  worktree was clean after that commit.

Current validation at the completion of Task 14a was:

| Command | Result |
| --- | --- |
| `make` | Passed: Ruff, Black, 393 pytest tests, numbered examples 001–023 |
| `make examples` | Passed: numbered examples 001–023 |
| `git diff --check` | Passed |

Always rerun suitable validation on the current worktree; these figures are a
baseline, not a substitute for review.

## Completed council-quality sequence

Tasks 13h–13m were implemented, independently reviewed, validated, reported,
and committed in sequence:

1. **Task 13h — deterministic council turn rotation**
   - Added an explicit, validated `CouncilCall.turn_order_offset: int = 0`.
   - Rotates only confirmed attendees deterministically; no randomness
     or LLM-controlled scheduling.
2. **Task 13i — NPC dialogue opening guidance**
   - Ensures an agenda is not represented as previous speech.
   - Gives an opening speaker guidance to state a direct position rather than
     replying with phrases such as “I see” to nobody.
3. **Task 13j — manual council scenario and safe context tracing**
   - Improved the local Ollama/llama.cpp council demos with an opaque-ID
     scenario, at least three meaningful actions, longer discussion, and
     nonzero deterministic turn offset.
   - Added opt-in safe diagnostic context output only: filtered `NPCContext` and
     offered actions, never raw world state, IDs, hidden records, or provider
     secrets.
4. **Task 13k — settlement-wide council scenario**
   - Added a shared manual scenario catalog and a concern recognized as requiring
     a town decision rather than originating as the caller's personal issue.
   - Keeps the caller as an engine-selected coordinator, not an authoritative
     representative of consensus or owner of the agenda.
5. **Task 13l — opposing-groups council scenario**
   - Demonstrates eligible NPCs with opposed and cross-cutting affiliations,
     several plausible actions, and no forced model decision.
   - Defers factions, voting weights, reputation effects, and political
     consequences.
6. **Task 13m — cognition-shaped council scenario**
   - Seeds holder-scoped observations, memories, experiences, beliefs, and
     social knowledge through existing manager-owned interfaces.
   - Uses the safe context trace to prove per-NPC isolation while allowing those
     interpretations to influence, but never predetermine, opinions.

Task 13m required a documented boundary amendment before implementation so the
manual provider entry points could invoke one shared manager-owned runtime
preparation path. Its first delivery then required one correction so the
holder-scoped NPC-relationship record actually reached Rhea's filtered context
through a manual-only retrieval adapter.

Task 13a HTTP-inspection coverage is implemented, reviewed, validated,
reported, and committed. A separate practical guide at
`docs/http_inspection_api.md` documents startup, integration, routes, and the
privileged information boundary. Task 14 release closeout and its Task 14b
version-consistency prerequisite are complete.

The user has also requested a post-v0.5 path toward launching an unattended
founding-settlement simulation that may grow into a town and beyond. The
proposed milestone sequence is documented in
`docs/post_v05_settlement_evolution_roadmap.md`. It includes engine-owned goals
and objective graphs, deliberately partial off-map homelands/markets, needs,
work execution, development stages, population continuity, governance, and
regional growth. These are roadmap candidates, not authorized implementation
tasks. Their milestone placement records intent and dependency order rather
than authorization.

Every future idea currently in `docs/backlog.md` is assigned to a roadmap
milestone or supporting track. After the v0.6 unattended founders scenario
passes its acceptance target, development changes from reviewed commits on
`main` to one `milestone/vX.Y` integration branch with short-lived
`task/<task>-<slug>` branches. `main` remains the stable release line. This
workflow decision is documented in `docs/development_workflow.md` and does not
authorize any roadmap task.

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
- a safe opt-in view of exactly the filtered context/action choices sent to
  cognition.

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

## Next work

Task 14a is complete and committed. No post-v0.5 implementation task or
milestone is currently authorized. Wait for the user to select and authorize
the next milestone or planning task. Before implementation, decompose the
authorized milestone into isolated numbered plans and saved prompts in its
milestone directory. Tasks 15 and 15a are documented v0.6 observability
candidates, not automatically authorized implementation.
