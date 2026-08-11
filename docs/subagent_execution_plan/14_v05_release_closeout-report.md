# Task 14 report — v0.5 release closeout

## Outcome

Release closeout is **blocked**. The audited v0.5 AI-layer capabilities are
implemented, tested, documented, and publicly importable, but the repository
cannot consistently report version `0.5.0` within Task 14's allowed-file
boundary.

No release version, changelog section, backlog completion state, or release
claim was changed. No tag was created. A focused corrective `14x` task is
required before Task 14 can resume.

## Release blocker

The release version is independently hard-coded in four places:

- `VERSION` contains `0.2.3` and is editable by Task 14.
- `pyproject.toml` declares `version="0.2.3"` and is editable by Task 14.
- `src/living_world/__init__.py:1` declares `__version__ = "0.2.3"`; production
  source is outside the Task 14 boundary.
- `src/living_world/api/server.py:17` returns `"version": "0.2.3"` from
  `/health`; production source is outside the Task 14 boundary.
- `tests/test_inspection_api.py:268` requires the old health response; tests are
  outside the Task 14 boundary.

Bumping only the two permitted metadata files would make the installed package
and health endpoint disagree with the release. The established Task 14
contract requires consistent `0.5.0` release metadata and explicitly forbids
fixing production defects forward. The corrective task should establish one
authoritative runtime version source, update the health endpoint and its test,
and prove consistency with `VERSION` and installed package metadata.

## v0.5 backlog audit

Every capability claim under `v0.5 – AI Layer` was traced to implementation,
tests, examples, and public imports:

| Backlog claim | Implementation evidence | Test/example evidence | Result |
| --- | --- | --- | --- |
| llama.cpp integration | `LlamaCppPerceptionClient`, `LlamaCppCognitionClient` | `test_llama_cpp_perception_client.py`, `test_llama_cpp_cognition_client.py`, opt-in llama.cpp examples | Complete |
| Local LLM client | loopback-only Ollama and llama.cpp perception/cognition clients | Ollama, llama.cpp, local HTTP, formatting, and engine tests | Complete |
| Decision engine and action gateway | `DecisionEngine`, `NPCActionResolver`, typed handler contract | decision, action-resolution, and engine-action tests | Complete |
| Council meetings | `CouncilService` and council value objects | council test suites and examples 022/manual examples | Complete |
| NPC conversations | `ConversationService` and immutable results/turns | conversation tests and example 020 | Complete |
| NPC meeting coordination | `MeetingService`, `MeetingRequest` | meeting tests and example 021 | Complete |
| NPC Cognition Protocol | `NPCCognitionClient`, `NPCContext`, structured decision/action values | cognition-client, format, decision, and context tests | Complete |
| NPC information boundary | `NPCInformationBoundary` and cognition request serializer | boundary and cognition-format tests | Complete |
| NPC-only context filtering | `NPCContextAssembler`, `DeterministicCognitiveRetriever`, perception boundary | retrieval, context, perception-boundary, and holder-isolation tests | Complete |
| LLMs lack world-truth authority | proposal-only cognition plus separately invoked resolver/handlers | decision and action-resolution rejection tests | Complete |
| Manual local council scenarios | shared settlement, opposing-interest, and cognition-shaped catalog | manual scenario/example tests and both opt-in provider entry points | Complete |

The public cognition interfaces are exported from
`living_world.cognition`. Provider-specific perception interfaces remain
importable from their documented modules. The HTTP guide's imports,
`living_world.api.server.create_app` and
`living_world.simulation.simulation_engine.SimulationEngine`, exist.

No incomplete v0.5 capability requires reclassification into v0.6. The
existing future RAG/vector retrieval, ranking/decay, governance, and other
future ideas remain correctly deferred.

## NPC information-boundary audit

The targeted search covered production cognition and perception assembly plus
all manual examples for `WorldState`, entity attributes, evidence, metadata,
holder/internal IDs, action keys, and target IDs.

- Engine-side perception is allowed to inspect `PerceptionContext`, raw
  attributes, and `WorldState`; `NPCPerceptionBoundary` validates the resulting
  visible description before cognition.
- `NPCContextAssembler` and deterministic retrieval use holder IDs only on the
  engine side and project qualitative, holder-scoped records.
- Local cognition serialization accepts only filtered `NPCContext` plus the
  engine-offered action vocabulary. It explicitly warns against invented IDs,
  evidence, metadata, hidden state, and claims of action success.
- Conversations convert visible speech into recipient observations with empty
  evidence and metadata. Councils keep membership, invitation identity, and
  scheduling engine-side.
- Manual cognition-shaped scenarios seed raw evidence, metadata, and
  provenance through manager-owned setup, but safe tracing serializes the
  filtered production cognition request rather than those records.
- Privileged HTTP inspection exposes authoritative records to operators but is
  not consumed by cognition.

No NPC-boundary release blocker was found.

## Documentation and debt reconciliation

The release checklist was corrected to use the actual `make examples` target
and expanded to cover clean installation, import verification, version-source
consistency, NPC-boundary audit, HTTP smoke testing, diff review, and the rule
that tagging waits for zero blockers.

The technical-debt register contains only resolved historical entries and no
unmet `Resolved when` criterion relevant to v0.5. It was left unchanged. The
backlog remains unchanged while the release is blocked so that v0.5 work is not
prematurely declared closed.

## Validation

- `make` — passed on Python 3.13.5: Ruff, Black, **392 tests**, and numbered
  examples **001–023**.
- `make examples` — passed independently for numbered examples **001–023**.
- Public-import inspection — documented imports exist; no missing public import
  was found.
- Targeted boundary search and manual inspection — passed with no leakage path
  found.
- `git diff --check` — passed.
- Clean-environment installation and final server/version smoke testing remain
  release-closeout steps after the version blocker is corrected. The existing
  HTTP test passed but correctly demonstrated the blocking `0.2.3` response.

## Files changed

- `docs/release_checklist.md`
- `docs/subagent_execution_plan/14_v05_release_closeout-report.md`

No production source, test, example, release metadata, or release-history file
was changed.
