# Task 13l — Opposing-groups council scenario report

## Outcome

Added the named `opposing-interests` setup to the immutable manual council
scenario catalog. The existing `journey` scenario remains the default, and
both Ollama and llama.cpp entry points discover and select the new setup through
their existing shared `--scenario` interface.

The scenario places five independently eligible Town Council members around a
damaged-market-road decision. Their NPC-visible self-knowledge describes
riverside traders and carriers, hillside growers, one participant who works
across both interests, and an independent healer with cross-cutting concerns.
This prose contains no entity, organization, or relationship identifiers,
numeric relationship scores, raw attributes, or hidden state.

## Alternatives and model freedom

The offered alternatives are:

- commit communal labour to immediate market-road repair;
- preserve communal labour for harvest and defer repair; or
- split work crews between a limited repair and harvest preparation.

No participant is assigned an action key, proposal, vote, majority, attendance
decision, or dialogue. Affiliation is qualitative filtered context only, and
live provider behavior remains variable. Offline tests therefore assert the
setup and safety contract rather than any model choice.

## Eligibility and gateway evidence

Every participant has a distinct opaque NPC identifier. Both existing manual
entry points iterate over every scenario participant and add an independent
`member_of` relationship to the scenario's convening organization before the
council call. Trader, grower, carrier, and independent descriptions neither
grant nor replace this eligibility.

No manual entry-point or gateway code changed. Consequently the Task 13j safe
filtered-request trace and result formatter remain intact, and every accepted
alternative still passes through the existing demonstration handler that
reports acceptance without mutating world state.

## Tests and validation

`tests/test_manual_council_scenarios.py` now proves:

- deterministic catalog order and offline selection in both provider entry
  points while retaining `journey` as the default;
- five distinct participants and per-participant membership construction;
- opposed, cross-cutting, independent, and identifier-safe visible context;
- three meaningful unique alternatives with no setup-level proposal or
  majority field and no action key embedded in participant self-knowledge; and
- provider-free `--help` discovery of the complete scenario catalog.

Commands and results:

- `.venv/bin/pytest tests/test_manual_council_scenarios.py`: 13 passed.
- `.venv/bin/ruff check examples/manual/council_scenarios.py tests/test_manual_council_scenarios.py`: passed.
- `.venv/bin/black --check examples/manual/council_scenarios.py tests/test_manual_council_scenarios.py`: passed before `make`; `make` applied the expected test formatting and its final Black check passed.
- `make`: Ruff and Black passed; 380 tests passed; all 22 examples passed.
- `make examples`: all 22 examples passed.
- `git diff --check`: passed.

No live provider run was made, and no deterministic claim is made about local
model attendance, dialogue, proposals, votes, or resolution.

## Files changed

- `examples/manual/council_scenarios.py`
- `tests/test_manual_council_scenarios.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- `docs/subagent_execution_plan/13l_opposing_groups_council_scenario-report.md`

## Boundary compliance and deferred work

Changes stayed within Task 13l's six allowed files. No production council,
cognition, relationship, action-gateway, persistence, HTTP, provider-client,
or world-state interface changed. The task adds no durable faction, voting
weight, institutional seat, delegate, authoritative alignment, secession,
reputation consequence, governance policy, or political persistence. Those
systems remain explicitly deferred.
