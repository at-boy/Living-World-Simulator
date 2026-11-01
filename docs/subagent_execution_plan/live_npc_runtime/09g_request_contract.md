# LN09g — Versioned founding-action request contract implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Steps use checkbox syntax.

**Status:** Independently reviewed; fulltask gatesPASS2872/10existing skips/allchecks, nativeprobe and featureintegration pending.
**Goal:** Offer both real backends an explicit empty-arguments contract for current founding actions, preserving legacy requests/replay and strict execution authority.
**Architecture:** Opt-in canonical provider request selection flows through the existing config/client factory, payload capture and source-selected replay seams. Only selected system instructions and response-schema arguments change; no domain/serializer/parser/gateway/driver/archive version changes.
**Tech Stack:** Python>=3.11, strict hints, current clients/broker/CLI/archive tests; no dependencies.
**Spec:** Approved live-runtime design and implementation execution; owner explicitly requires both Ollama and llama.cpp functional verification, exact request/response retention and unchanged recorded functionality. Root decomposition/rulings below implement these existing requirements.

## Global constraints and approaches

Managers mutate, systems own behavior, events immutable. RuntimeService sole worldwriter; LLM output untrusted until ordinary actiongateway executes. No coercion, argument stripping, fabricated acceptance, recorded tape changes, generic action/description/schema changes, hidden NPC data, WorldState/internalIDs/arbitrary runtime objects. Preserve old defaults, request bytes, effective/input hashes, sealedsource replay and domain rejection. No GPU profiles, model downloads, remote services, dependencies or world/export/browser changes.

Root considered provider request selector, driverformat2/composition policy, and per-offer argument metadata. Choose opt-in provider selector because payload construction and fingerprints already carry it; driverformat2 adds unrelated wiring, per-offer metadata changes strict archived action triples. New selector only supports canonical founding scenario whose WorkActionHandler and ExternalDispatchActionHandler already reject every nonempty arguments mapping. Generic clients/defaultcontract remain unchanged. This is root's implementation ruling under approved execution, not a newly user-selected design.

## NPC pathway before implementation

Engine truth/perception/cognitive records/memory/retrieval and filtered NPCContext unchanged. Current action triples/target labels unchanged. Transformation changes only selected system instructions and output arguments schema; no new world facts/IDs/config selector enter NPC-visible context. Requests remain NPC-readable context and qualitative offered vocabulary. Output remains inference/proposal, never execution or goal/stage truth. Target stays target_label; arguments stays an untrusted mapping passed intact to existing gateway. Backend configuration, request-contract selector, exact traces, source hashes/reuse and timing remain engine/admin evidence. Legacy contexts/bytes and source-selected replay retain original transformation.

## Exact worker boundary (12 paths)

1. src/living_world/cognition/local_llm_cognition_format.py — new selector/helper only; original constants/serializer/parser unchanged
2. src/living_world/cognition/ollama_cognition_client.py — optional keyword and selected instance format only
3. src/living_world/cognition/llama_cpp_cognition_client.py — same
4. src/living_world/runtime/broker.py — ProviderConfig/validation/canonical omission/factory only
5. src/living_world/archives/model.py — provider allowlist and closed canonical newselector validation only
6. src/living_world/runtime/entrypoints.py — new nullable flag validation/defaults/fresh/resume/fork provider propagation/normalization only
7. src/living_world/cli.py — run+serve parser and legacy fresh execution propagation only
8. NEW tests/test_cognition_request_contract.py
9. NEW tests/test_runtime_request_contract.py
10. docs/operator_runbook.md — opt-in usage/compatibility/limits only
11. docs/subagent_execution_plan/live_npc_runtime/09g_request_contract-report.md

12. tests/test_runtime_llama_cpp.py — only canonical provider fixture in test_llama_provider_dispatch_and_archive_grammar: use provider_document(config) instead of asdict(config); preserve archive grammar assertions.

Root owns task/prombt/common docs/evidence/fullgates/VCS/native probes. Worker no otherfiles/subagents/index/commits/fullmake/examples/models/servers/downloads/dependencies/othercheckouts. Unit owned fixtures/subprocesses for fake broker tests only, cleanup finally. Missing seam requires root ruling/amended task+prombt before expansion.

## Contract representation and interfaces

Shared RequestContract = Literal['legacy_v1','founders_empty_arguments_v1']; NEW request_contract_format(request_contract:str)->tuple[str,dict[str,object]]. Strict str/knownenum runtime validation, unknown/null/bool fails. Legacy returns original constants unchanged. New returns isolated deepcopy of schema with action_request.properties.arguments exactly {'type':'object','properties':{},'additionalProperties':False}. All other schema values unchanged. New instructions derive from original constant by replacing the single example `"arguments": {"<argument name>": "<string value>"}` with `"arguments": {}` and appending exactly:

Every offered action in this request accepts no named arguments.
When proposing an action, arguments must be exactly {}. Put the chosen target
only in target_label; never duplicate it in arguments.

Clients gain optional keyword request_contract:RequestContract='legacy_v1'. Validate via helper; only new selection assigns isolated instance SYSTEM_INSTRUCTIONS/RESPONSE_SCHEMA, leaving default/class constants/build_payload/decide/serializer/parser behavior unchanged. Never mutate shared constants or another client instance. Schema is a provider request constraint, not trusted validation: a transport ignoring it can still return nonempty arguments; preserve them for unchanged gateway rejection.

ProviderConfig gains defaulted RequestContract field request_contract='legacy_v1', runtime type/enum check. provider_document removes request_contract iff legacy, preserving every prior key/value/omission (including old Ollama kind/model_file omission). New selection is retained. client_for passes selected keyword to both clients; existing prepare_inference/spawn/restart/replay consume factory/config unchanged.

Canonical persisted provider optional request_contract key WHEN PRESENT accepts ONLY string founders_empty_arguments_v1, only config.mode='ollama' and scenario_key='canonical_founders_v1'. Legacy is represented by absence; explicit legacy in raw AttemptConfig provider is rejected as noncanonical before setup/IO. Unknown/null/bool values reject. Broker provider_config enforces scenario restriction too. This avoids validate_setup_config's raw requestedkey comparison against omitted effective legacy default; no catalog change. ProviderConfig legacy direct construction is valid and canonicalizes to absence.

New --request-contract {legacy_v1,founders_empty_arguments_v1} for run/serve, argparse defaultNone. Fresh absent/explicitlegacy produces original no-selector provider document. Fresh new persists newkey. Absence on resume/fork inherits source; explicitlegacy strips key, new sets key. Changed resume rejects before provider preflight/newreservation, same selection allowed. Fork can change selection; revision0 inherited-cursor accommodation works but incompatible parent requests never reused. Recorded/inspect/analyze/replay cannot use selector even explicitlegacy (reject rather than ignore). Add to _PROVIDER_FLAGS/_CONFIG_FLAGS and compatibility Namespace defaults; getattr safe for existing callers. Serve prepared launches propagate existing config path, no UI changes.

No launch/replay/driver/trace/storageformat changes: source-selected provider config drives offline replay; unknown selectors fail closed. New canonical provider key changes effective hash; selected new payload changes input/body hashes. Legacy hashes/bytes remain exact. Legacy parser continues to accept structurally valid nonempty args; ordinary gateway rejects them. No action correction or schema-only success claim.

## Review focus and one task TDD cycle

- [x] RED missing selector/flag/helper/new payload schema before product changes. Capture deterministic legacy payload-byte SHA256/providerdoc/effective+input hashes from baseline before edits; expected constants must not be generated from new implementation.
- [x] Both provider clients legacy/default/explicitlegacy exact baseline bytes and unchanged shared constants; selected schema emptyargs/prompt without generic argument example; two clients don't mutate each other; unknown/null/bool reject; generic arbitrary-string argument parsing remains intact and domain gateway rejects nonemptyargs unchanged.
- [x] Config canonical omission/new persistence/type/scenario restrictions, raw explicitlegacy rejection, exact legacy fingerprints/new fingerprint difference; actual CLI help/run/serve parse and recorded/inspect/analyze/replay rejection; no ignored selector.
- [x] Fake transport/broker actual prepared body+stored trace uses new schema and filtered context, no hidden/raw data; accepted ordinary work proposal with {} executes, nonempty remains rejected without stripping. No new real provider calls by worker.
- [x] Actual archived deterministic fakeprovider run: new-selector fresh -> coldrestart -> sealed offline replay with provider unavailable and exact checkpoint/cursors; replay descendants use sealed source selector despite current defaults. Explicit old-to-new/new-to-old forks have changed fingerprints/new payloads and no incompatible parent reuse; source bytes+mtimes unchanged. Same-selector sealed reuse remains valid. Default old replay/hash/payload regressions unchanged.
- [x] Focused new tests plus existing cognition client/format, runtime_llama_cpp/journal_replay/cli, inference_trace_storage, work_action_gateway/external_dispatch tests. VENV=.worktrees/task24/.venv PYTHONPATH=src; scoped Ruff/Black/whitespace. Report commands/results/counts/warnings/allowedpaths/limits and freeze for independentreview.

Root afterreview: required fulltask+repeatedmerged make/examples/diffcheck/canonical26/CLI7/Serve4/wheel14+Serve4/native9archive30calls/API8+actualwheelChrome/CLI16+signals. Native root probe of both providers follows only with allowance headroom; all normal attempts retained automatically, exact new requests/responses/timings and provider-offline replay verified. Actual accepted work required for compatibility evidence; null/stall/failure recorded truthfully. No fullLN09acceptance claim from prompt/schema/unit code alone. Preserve branches/ownerpatch; no main/milestone/tag. Pause before owner10% floor, no reset.
