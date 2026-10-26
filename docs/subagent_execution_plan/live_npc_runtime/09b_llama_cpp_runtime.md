# LN09b — Both local backends through the persistent runtime

Status: AUTHORIZED after reviewed LN09a integration6321306; owner explicitly requires
both providers. This is the exact bounded backend prerequisite, not final acceptance. This prerequisite precedes original LN09 acceptance.
Spec: approved live-runtime design plus user's explicit Ollama/llama.cpp requirement.
No server management, downloads or GPU controls inside product/runtime.

## Architecture and scope

Retain archive mode ollama as legacy LIVE storage mode; provider.kind chooses ollama
(default omitted) or llama_cpp. Existing model-free/recorded behavior stays exact.
Share RuntimeService, controller, broker/process transport, driver, gateways, filtered
feedback, archives/restart/fork/replay and browser. No second driver/lifecycle owner.

Exactly12workerpaths: src/living_world/cognition/llama_cpp_cognition_client.py;
src/living_world/runtime/broker.py; src/living_world/runtime/preflight.py;
src/living_world/archives/model.py; src/living_world/archives/catalog.py;
src/living_world/runtime/ollama_driver.py; src/living_world/runtime/entrypoints.py;
src/living_world/cli.py; NEW tests/test_runtime_llama_cpp.py;
docs/npc_information_boundary.md (newflowonly); docs/local_llm_setup.md (backendflowonly);
own docs/subagent_execution_plan/live_npc_runtime/09b_llama_cpp_runtime-report.md.
Root owns task/prombt/common4. No launch/service/controller/journal-replay/schema-file/
version/dependency/recorded/domain/API asset changes; report missing producer before
scope expansion. Python>=3.11 strict hints/protocols. Worker no VCS/index/subagents/
fullmake/examples/realmodels/downloads/serverruns/othercheckout edits.

## Provider config and old compatibility

ProviderConfig adds kind:Literal[ollama,llama_cpp]=ollama and model_file:str|None=None.
Keep existing model/base_url/timeout/token/response/temp/seed/digest fields and defaults.
Direct ProviderConfig llama callers explicitly supply URL; CLI supplies127.0.0.1:8080
for fresh llama; Ollama defaults11434 unchanged. Reject unknown kind; Ollama rejects
nonNone model_file. llama requires absolute nonempty no-NUL/control local GGUF path
(max4096chars); validation does not touch filesystem until bounded preflight. Source
operator metadata only, never NPC prompt/context. AttemptConfig grammar allows only
these2newproviderkeys with strict types/closed values; old configs remain readable.

provider_document(config:ProviderConfig)->dict[str,object] is canonical serialization:
asdict legacy fields EXACTLY old contents for Ollama, omitting kind/model_file; llama
includes kind and model_file. Use everywhere config is effectively serialized including
preflight settings and effective_config_fingerprint. Do not silently hash new default
fields. Exact known historical no-disturbance and active-schedule Ollama hashes retained.
Provider selection/path/digest binds llama effective fingerprint, requests/cursors/reuse.
Changing provider/file/model invalidates prior response reuse; no weakening equality.

## Shared bounded cognition

Broker client_for returns a typed protocol providing decide(context,actions)->NPCDecision
and build_payload(context,actions)->dict[str,object]. Ollama branch unchanged.
LlamaCppCognitionClient adds keyword max_output_tokens=512,temperature=0.0,seed=None,
finite positive timeout and strict integer/output/finite nonnegative temp validation
matching Ollama. build_payload extracts existing inline chat payload and adds max_tokens,
temperature, optional seed, chat_template_kwargs:{enable_thinking:false}. Keep response
schema/system/serializer/parser and /v1/chat/completions route/streamfalse. Use existing
loopback JsonHttpTransport. Both parent/spawn child measure COMPLETE actual provider
payload against16000characters; same bounded response reads/reaping/errorcodes. Model
file is never opened by inference or serialized into HTTP prompts/payload.

## Trustworthy explicit local file identity

llama preflight uses bounded spawned worker and same parent wall deadline/cancel/reap.
GET /v1/models and GET /props through existing no-proxy/no-redirect bounded transport.
Require exactly one matching requested model ID and props.model_alias exactly matches;
no Ollama ':latest' normalization. props.model_path must be absolute and resolve to
same local file as configured model_file; this runtime supports local native servers
or same-path mounts only. Other topology is explicit invalid_preflight, not fabricated
identity. Do not trust llama's dummy empty digest in /api/tags.

Open configured resolved path read-only/nonblocking; verify regular file and GGUF magic,
then stream SHA256 without retaining model bytes. fstat before/after dev/ino/size/mtime_ns/
ctime_ns must agree; ensure path still resolves to same identity afterhash. Repeat GET
/props afterhash; alias/path must remain same. Configured pinned model_digest ifprovided
must equal canonical64lowerhex SHA256. Result frame retains only exactselected model and
canonicaldigest under existing bounded child frame; parent independently validates closed
frame/types/model match/pin with provider-specific checks, never hashes model in parent
or follows child-supplied paths. Parent deadline/cancel covers file reads/hash/HTTP.

Trust statement: this verifies local file bytes plus server-reported alias/backing path,
not cryptographic proof of resident GPU memory. Acceptance starts owned server against
pinned unchanged file; no claim stronger than evidence. No automatic GGUF archive copy.
Archive retains digest/path as engine-only reproducibility metadata; replay requires no
file/server/provider because it uses retained safe decisions and exact source config.
Missingfile/model =>model_missing; malformed/path/changedfile =>invalid_preflight;
pin mismatch =>model_digest_mismatch; safe existing codes only, never raw errors/path.
Tests may use tiny GGUF-prefixed fixtures for identity mechanics only, not validmodels.

validate_setup_config compares provider_document or equivalent effective normalized
values, preserves all settings except installed identity, exact llama model and path;
Ollama ':latest' behavior and raw absent-kind defaults unchanged.

## Public launch paths

run and serve --driver choices ollama|llama.cpp, add --model-file. Public llama spelling
maps to legacy modeollama/provider.kind llama_cpp; no newarchive/API mode. Existing
--driverollama commands/options/exits/defaults byte-compatible. Fresh llama requires
explicit model+file; defaultloopback8080. Ollama rejects --model-file, recorded/replay
reject providerflags before allocation. All namespace/default validation paths handle
new optionalfield without breaking old callers/tests.

Resume defaultinherits exactsourcekind/file/model/effective config. Explicitsamevalue
allowed; changingkind/model/file/URL/budgets rejects before allocation under existing
resume rules. Same-provider fork can change model/file/config through normal preflight;
provider switch fork requires explicit model and (forllama) model-file, clears stale
digest, picks newbackend defaultURL unless explicitlyoverridden. Switching toOllama
removes oldkind/model_file, picks11434, and retains no stale GGUF pin. Changed samekind
model/file clears digest. Model name equivalence uses ':latest' ONLY Ollama. Disturbance
schedule inheritance guard stays exact. No parser flag expansion in recorded modes.
Both headless run and public paused-default serve use SAME prepared launcher. Update
cli legacy helper paths only as necessary to prevent bypass/inconsistent config.

## Tests and execution

TDD RED actual missingbackend support beforecode; new central tests cover exactclient
payload and invalid values, real spawned fakeHTTP broker both formats/cancellation/
responsebounds/request-bodylimit, providerpreflight correct/wrongalias/path/GGUFpin/
filemutation/missingfile/malformedframe/timeout/cancel/noresourcesleftover. Prove every
newsetupfailure retains truthful normal attempt whereallocationalreadyhappened.
Historical Ollama effective hash exact; llama distinct; crossprovider/file reuse rejected.
Use normal RuntimeService fakeHTTP llama responses through genuine gateways, not a
stub alternative runtime. Exact pause/durableACK/coldrestart/reusedresponses/no duplicate
charges/fork, bothdisturbances and exact offline source replay with forbiddentransport
and missingGGUF file. Public run+serve factory/namespace/options beforeeffects, actual
paused-default HTTP single-step/resume/shutdown and historicalinspection forllama.
No raw world/IDs/path/digest/provider response leaks to serialized NPC payload.

Focused newmodule + test_llama_cpp_cognition_client.py + runtime broker/preflight/
ollama_driver/journal_replay/launch_request/serve owning modules. Scoped Ruff/Black.
Report RED/GREEN/counts/warnings/paths/sourceidentity/trust/NPC evidence/rootpending.
Independent highreview then rootfull task+merged make/separateexamples/whitespace,
canonical26/CLI7/sourceServe4/wheel11+actualServe4, source unchangedafterformatters.
Root realprovider acceptance AFTER integration (original9, after required trace tasks): both Ollama and
llama.cpp actual baseline/decisions/disturbances/browser/pause/coldrestart/offlinereplay,
Python3.11 installedcompatibility, finalwholebranchreview. Allattempts preserved. Existing
Qwen3.5 GGUF and llama-server work; download is permitted to owner's specified folder
only if needed, never implicitly install drivers. No main/tag actions.

## Owner updates and dependency boundary

Exact per-inference privileged rawrequest/response/backend/model/timings logging is now
a REQUIRED separate prerequisite before final acceptance; do not claim existingparsed
responses satisfy it. User explicit logging requirement supersedes prior raw-invalid
nonretention, but this provider task does not implement traces or expand that boundary.
Afterthis task activate bounded trace-storage/capture/admin-inspection contracts, then
original fullacceptance (renumberasneeded). Keep currenterrorhandling exceptionssafe.
Normal native llama acceptance uses AMD Vulkan0, per owner's clarification. Configurable
GPU/model/backendprofiles are futurebacklogonly, no productserver/GPUlauncher now.

## Execution gates

- [ ] Reproduce missing runtime llama dispatch/preflight with focused behavioral RED.
- [ ] Implement only specified provider/client/config/CLI boundaries and production-path tests.
- [ ] Run named focused tests plus scoped style; record command/result/counts/warnings.
- [ ] Freeze/report for root independent spec and quality review; correct scoped findings.
- [ ] Root fulltask checks, exact legacy/installed serving checks, documents and focused commit.
- [ ] Preserve/push taskbranch, integrate feature, repeatmerged gates before completion.

Root clarifications before worker dispatch: broker payload-client protocol extends
NPCCognitionClient including existing provider_name, plus build_payload. model_file
keeps configured absolute spelling in archived config/fingerprints; resolve only for
local identity comparisons. Preflight never rewrites configured path spelling.
