# 13g — Local cognition response-shape guidance

## Task Description

Improve local-model adherence to the existing strict NPC cognition JSON
contract. The manual council example repeatedly receives invalid structured
responses from a local Ollama model, so strengthen the shared system instruction
with an exact response-shape checklist and schema-compliant template. Do not
relax parsing, infer missing fields, or accept an unoffered action.

## Context Needed

- Create: `docs/subagent_execution_plan/13g_local_cognition_response_shape_guidance-report.md`
  and `tests/test_local_llm_cognition_format.py`.
- Edit: `src/living_world/cognition/local_llm_cognition_format.py`,
  `tests/test_npc_cognition_client.py`,
  `tests/test_ollama_cognition_client.py`,
  `tests/test_llama_cpp_cognition_client.py`, `docs/local_llm_setup.md`,
  `CHANGELOG.md`, and `docs/project_journal.md`.
- Know: `SYSTEM_INSTRUCTIONS`, `RESPONSE_SCHEMA`,
  `serialize_decision_request`, `parse_decision_response`, both local cognition
  clients, and the Task 13e invalid-structured-response diagnostic.

## Interface Contract

```python
SYSTEM_INSTRUCTIONS: str
RESPONSE_SCHEMA: dict[str, object]

def parse_decision_response(
    content: object,
    actions: tuple[ActionOption, ...],
) -> NPCDecision: ...
```

- Public function/type signatures and `RESPONSE_SCHEMA` semantics remain
  unchanged.
- The shared system instruction tells the model to return exactly one JSON
  object and no surrounding prose/Markdown. It explicitly requires both top
  level fields, `spoken_text` and `action_request`.
- If `action_request` is an object, the instruction explicitly requires all
  four fields: `action_key`, `target_label`, `rationale`, and `arguments`.
  It instructs the model to use `null` when no target is offered and `{}` when
  no arguments are needed. The template uses placeholders only; it must not
  embed world data, action-key literals, entity IDs, or numeric attributes.
- The instruction continues to allow `action_request: null` where an action is
  genuinely not proposed. It does not invent an action or claim success.
- `parse_decision_response` remains strict: missing/extra/wrongly typed fields,
  non-JSON content, and unoffered actions still raise
  `NPCCognitionInvalidResponseError`.

## Test Criteria

- Tests assert the system instruction contains the complete response-shape
  checklist/template, no internal-record-ID pattern, no world data, and no
  action vocabulary from a test world.
- Ollama and llama.cpp request tests prove both providers receive that same
  shared instruction and schema.
- Parser tests prove a compliant null-action response and a compliant
  action-request response remain accepted, while missing `arguments`, missing
  `target_label`, Markdown-wrapped JSON, and unoffered actions remain rejected.
- `make`, `make examples`, and `git diff --check` pass.

## Orchestrator Report

Create
`docs/subagent_execution_plan/13g_local_cognition_response_shape_guidance-report.md`.
Report exact instruction semantics/template, strict-parser preservation,
provider request evidence, validation commands/results, changed files, boundary
compliance, and the limitation that instruction tuning improves but cannot
guarantee local-model compliance.

## Boundary

- Touch only the listed format/client-test/docs/report files.
- Do not edit council policy, manual examples, local HTTP transport, response
  parsing acceptance logic, action resolution, information-boundary validation,
  persistence, HTTP APIs, or Makefile.
- Do not include raw provider outputs in tests, reports, or docs.
