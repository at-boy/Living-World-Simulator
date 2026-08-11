# Task 10 — Local LLM Cognition Client Report

## Outcome

Implemented loopback-only Ollama and llama.cpp adapters for structured,
proposal-only NPC cognition. They accept only an `NPCContext` plus caller
offered `ActionOption` vocabulary and return an untrusted `NPCDecision`; they
do not access or mutate simulation state.

## Files Changed

- Created `src/living_world/cognition/npc_cognition_client.py`.
- Created `src/living_world/cognition/local_llm_cognition_format.py`.
- Created `src/living_world/cognition/ollama_cognition_client.py`.
- Created `src/living_world/cognition/llama_cpp_cognition_client.py`.
- Updated `src/living_world/cognition/__init__.py` exports.
- Created `tests/test_npc_cognition_client.py`.
- Created `tests/test_ollama_cognition_client.py`.
- Created `tests/test_llama_cpp_cognition_client.py`.
- Updated `docs/local_llm_setup.md`, `CHANGELOG.md`, and
  `docs/project_journal.md`.
- Updated `docs/subagent_execution_plan/10_local_llm_cognition_client.md`.
- Created `docs/subagent_execution_plan/10_local_llm_cognition_client-prombt.md`.
- Created `docs/subagent_execution_plan/10_local_llm_cognition_client-correction-prombt.md`.
- Created this report.

## Public Interfaces

- Frozen `ActionOption`, `ActionRequest`, and `NPCDecision` value objects.
  They validate non-empty visible strings, unique target labels, and a
  defensively copied read-only action-arguments mapping.
- `NPCCognitionClient` protocol, `NPCCognitionClientError`, and
  `NPCCognitionInvalidResponseError`.
- `serialize_decision_request(context, actions)` and
  `parse_decision_response(content, actions)`.
- `OllamaCognitionClient` and `LlamaCppCognitionClient`, each exposing
  `provider_name` and `decide(context, actions)`.

## Provider Request and Response Contracts

- Ollama posts to `POST /api/generate` with model, system instructions, a
  JSON-safe prompt, `stream: false`, `think: false`, and a JSON schema.
- llama.cpp posts to `POST /v1/chat/completions` with system/user messages,
  `stream: false`, and its structured JSON response format.
- The prompt contains only `NPCContext` fields (identity, qualitative
  self-knowledge, current perceptions, and retrieved cognition projections)
  and the offered action keys, descriptions, and target labels.
- A response must be an exact JSON object with `spoken_text` and
  `action_request`. The latter is `null` or an exact action-request object;
  its key and target label must be in the vocabulary offered for that call.

## Boundary and Error Evidence

- Both clients reuse the unchanged local HTTP transport and loopback URL
  validation. Non-loopback URLs are rejected before requests are made.
- Serialization tests assert that `WorldState`, IDs, raw attributes, evidence,
  metadata, provenance, and raw capability names do not appear in the prompt.
- Format-level validation rejects conventional internal record IDs
  (`entity_<digits>`, `relationship_<digits>`, `event_<digits>`,
  `observation_<digits>`, `belief_<digits>`, `experience_<digits>`,
  `memory_<digits>`, `knowledge_<digits>`, and
  `npc_relationship_<digits>`) in all action-option/request/decision visible
  values. This preserves the proposal-vocabulary boundary without accessing
  `WorldState`.
- Parsing rejects invalid JSON, unknown fields, empty decisions, malformed
  action requests, and unoffered action keys or targets with
  `NPCCognitionInvalidResponseError`; parsed provider IDs are therefore never
  accepted as a decision.
- Local HTTP transport failures are translated to `NPCCognitionClientError`.
- No manager, event, repository, simulation-engine, tool, or action-application
  interface was added or invoked. Task 11 remains the sole action authority.

## Tests and Validation

- Focused tests cover strict value-object validation and immutable arguments,
  client-visible internal-ID rejection, prompt filtering, valid structured
  decisions, malformed provider output, vocabulary enforcement, loopback
  rejection, and translated transport errors.
- Post-correction `make` passed: Ruff, Black, 260 pytest tests, and numbered
  examples 001–019.
- `make examples` passed: numbered examples 001–019.
- `git diff --check` passed.

## Documentation

`docs/local_llm_setup.md` now distinguishes the perception and cognition
clients and documents the latter's proposal-only boundary. The changelog and
project journal record the structured, loopback-only cognition integration.

## Boundary Compliance and Deferred Work

Only Task 10 cognition-client modules, their tests, allowed documentation, and
this report were modified. `perception/local_llm_http.py` was reused unchanged;
no perception client or action application code was modified. Task 11 must
still validate and apply any accepted proposal through the engine action
gateway.

## Blockers

None.
