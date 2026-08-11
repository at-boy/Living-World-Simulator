# 13m — Cognition-shaped council scenario

## Task Description

Add a manual council scenario demonstrating that NPC-specific observations,
memories, experiences, beliefs, and social knowledge can shape different
opinions about the same agenda. Seed records through existing manager-owned
interfaces and make their effect inspectable through Task 13j's safe filtered
context trace without exposing cognitive records belonging to another NPC.

## Context Needed

- Create:
  `docs/subagent_execution_plan/13m_cognition_shaped_council_scenario-report.md`.
- Edit: `examples/manual/council_scenarios.py`, both manual council examples,
  `tests/test_manual_council_scenarios.py`,
  `tests/test_manual_council_examples.py`, `docs/local_llm_setup.md`,
  `docs/core_model.md`, `docs/engine_glossary.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Know: Task 13k's scenario catalog, Task 13j's `RecordingCognitionClient`,
  `NPCContextAssembler`, observation and cognitive-record managers,
  holder-scoped retrieval, cognitive lineage filtering, and the NPC
  information-boundary tests.

## Interface Contract

- Add one named scenario to the shared manual catalog; do not change the
  default or duplicate provider-specific setup.
- Add one shared, typed manual runtime-preparation path used by both provider
  entry points. It creates the scenario organization and participants through
  `SimulationEngine.definitions`/`entities`, creates eligibility relationships
  through `SimulationEngine.relationships`, returns the manager-generated
  opaque runtime IDs needed by `CouncilCall`, and applies optional
  scenario-specific cognitive seeding. Provider entry points must not contain
  duplicate seeding logic.
- All participants receive the same safe agenda and action vocabulary. Seed
  distinct holder-scoped cognitive histories that provide plausible reasons
  for different preferences, including at least one observation, memory,
  experience, belief, and NPC relationship/social-knowledge interpretation
  across the scenario.
- Create entities, relationships, observations, and cognitive records only
  through their existing engine/manager-owned lifecycle interfaces. Do not
  mutate runtime collections directly or invent a manual persistence path.
- Refactor the existing manual scenario setup to use that shared preparation
  path for every catalog scenario. Preserve the scenario names, default journey
  behavior, visible labels, safe tracing, and accepted no-mutation gateway;
  manager-generated opaque runtime IDs may replace catalog-fixed IDs because
  they remain engine-only.
- A belief remains an NPC interpretation and may conflict with another NPC's
  belief or with engine truth. Scenario setup must not force an action choice,
  dialogue line, vote, or outcome.
- The opt-in safe trace may show only the already-filtered `NPCContext` and
  offered actions recorded before each call. It must never print raw
  `WorldState`, internal record/entity IDs, evidence, metadata, hidden records,
  another holder's cognition, provider payloads, exception internals, or
  secrets.

## Test Criteria

- Offline tests prove the common agenda/actions and distinct holder-scoped
  records are assembled through existing managers without provider calls.
- Tests prove both entry points use the same prepared runtime and no longer
  mutate `WorldState.entities` or `WorldState.relationships` directly.
- For every participant, tests inspect the assembled/recorded safe context and
  prove it contains only that NPC's permitted cognitive material, with no
  other holder's hidden records, internal IDs, evidence, or metadata.
- Tests demonstrate that conflicting beliefs remain interpretations rather
  than assertions or mutations of authoritative world state.
- Tests prove scenario setup supplies reasons for differing opinions but does
  not predetermine proposals, votes, majority, or gateway resolution.
- `make`, `make examples`, and `git diff --check` pass. Live local-model output
  remains variable and the manual examples remain opt-in.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13m_cognition_shaped_council_scenario-report.md`.
Report the seeded cognitive categories and manager paths, per-holder isolation
evidence, safe-trace behavior, tests/commands/results, exact files changed,
boundary compliance, and any deferred cognition/retrieval work.

## Boundary

- Touch only the listed shared manual scenario, provider entry points, tests,
  documentation, and report files. The provider entry points are included
  because they own runtime construction and must invoke the shared preparation
  path for cognitive records to reach actual `NPCContext` assembly.
- Do not change production cognition/context/retrieval/council/action APIs,
  persistence, provider clients, HTTP APIs, numbered examples, or Makefile.
- Do not directly mutate manager-owned state, expose cross-holder cognition or
  engine evidence, equate beliefs with facts, or force local-model behavior.
