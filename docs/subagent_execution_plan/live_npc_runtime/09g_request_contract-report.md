# LN09g — implementation report

Status: implementation prepared; root independent review and authoritative full
validation/native provider verification remain outstanding. No completion of the
full live-runtime acceptance milestone is claimed.

## Scope and behavior

Implemented the root-selected opt-in `founders_empty_arguments_v1` provider
request contract. Legacy requests remain the default; the shared original prompt,
schema, serializer, parser and all gateway/domain behavior remain unchanged.
The selected helper copies only the arguments schema and adjusts the example plus
specified instructions. Selected client instances receive independent schemas.
Provider metadata canonically omits legacy, persists only the new selection, and
rejects noncanonical raw legacy/unknown/nonstring keys and non-live/non-founders
uses. Both client factories carry the selected contract. Public run/serve flags
support fresh selection, inherited/same resume, changed fork, and explicit legacy
normalization. Other command modes reject the flag.

NPC context, action vocabulary, target labels and hidden engine information remain
unchanged. The new schema remains an untrusted provider constraint: nonempty
arguments reach the ordinary gateway intact and are rejected there. No proposal
repair, argument stripping, invented acceptance, source-tape alteration, schema
version change or simulation authority change was introduced.

## Boundary

Changed the eleven original allowed paths only, plus the root-approved twelfth
path `tests/test_runtime_llama_cpp.py`. In that existing test file only the named
`test_llama_provider_dispatch_and_archive_grammar` fixture switched
`asdict(config)` to `provider_document(config)`, with obsolete import removal and
formatting of that assertion. This is necessary because raw explicit legacy is
now intentionally noncanonical. Root amended task and saved prompt before the
change. No other existing tests were edited.

The other ten changed implementation/documentation/test paths are:

- `src/living_world/cognition/local_llm_cognition_format.py`
- `src/living_world/cognition/ollama_cognition_client.py`
- `src/living_world/cognition/llama_cpp_cognition_client.py`
- `src/living_world/runtime/broker.py`
- `src/living_world/archives/model.py`
- `src/living_world/runtime/entrypoints.py`
- `src/living_world/cli.py`
- `tests/test_cognition_request_contract.py`
- `tests/test_runtime_request_contract.py`
- `docs/operator_runbook.md`

This report is the remaining allowed path. Worker used no Git/index operations,
commits, merges, pushes, other checkouts, dependencies, native model services,
downloads, full `make`, or examples. Unit-owned loopback fixtures and spawned
broker processes use finally cleanup; tests assert spawned child cleanup.

## Baseline fingerprints captured before product edits

Baseline supplied by root: `5a3b041`. Used existing clients/configs with model
`tiny`, seed 7, declared digest `b` repeated 64 times; llama.cpp additionally
used `/models/tiny.gguf` and loopback port 8080. Payload context was
`NPCContext('Erik', (), ('An oak is nearby.',), (), ())`, actions one `wait` /
`Wait and observe.` option. Encoded bodies use existing `encoded_body`; the input
fingerprint uses existing canonical shape with `feedback_input='a'*64` and the
actual provider payload. Effective configuration uses canonical founders, seed 7,
software revision `test` and canonical `provider_document`.

| Provider | Body bytes | Body SHA256 | Input SHA256 | Effective SHA256 |
| --- | ---: | --- | --- | --- |
| Ollama | 2814 | `3152d6ed472fec0b74f25d852052fe7313595d4edff025f59d3870e707ca7824` | `67f70f9bdc6b8a606eb3cc84efa6574a9baa7d122858cb4642d60538690aa143` | `f16d2e4140777e11e88a27d6ee5ba6cd224b6adfe4a072576a19d4a28fa22957` |
| llama.cpp | 2926 | `1a5e0d03ca2944fc64bed27d341afd729ca897bc213a0888f2311ad3ec169619` | `104a2a73c5492488d0debd66c7bd3dfb6c4c6abbbd0fbc7ffbd673cfff8ba2a8` | `f2237d6f0bbd2644c73e62462b52b1b792aaccff637f813cfca39ad40c4abf0d` |

The fixed expected constants in new tests came from that pre-edit run. Default
and explicit legacy retain them exactly; the new selection changes body, input
and effective identity. The original provider-document key/value/omission
behavior is retained, including absent old Ollama kind/model_file/selector.

## Tests and validation

All Python commands used `PYTHONPATH=src` and Python from
`/home/at-boy/Projects/codex/Living-World-Simulator/.worktrees/task24/.venv`.

TDD evidence:

- `python -m pytest -q tests/test_cognition_request_contract.py` before product
  changes: 10 failed, 1 passed. Missing client keyword/helper caused the expected
  failures; the unchanged parser control passed. After implementation: 11 passed.
- `python -m pytest -q tests/test_runtime_request_contract.py` before config/CLI
  changes: 7 failed, 23 passed. Missing config field, missing CLI flag and closed
  archive provider grammar caused the expected failures. After implementation:
  the then-current two new files together passed 41 tests.
- Added integration tests initially exposed test fixture errors, corrected without
  product changes: replay-of-replay used the public replay operation rather than
  supported descendant resume; a world assertion named nonexistent `work_orders`
  rather than `work_states`. That run: 3 failed, 36 passed; corrected run: 39 passed.
- The additional four spawned broker tests initially assumed a nonexistent
  `BrokerResult.request_body`, then assumed response capture without binding a
  trace, then used a noncanonical short spool job ID. Corrected tests use the
  existing `bind_trace` interface with a 32-digit job ID and compare transport
  bodies against preparation and captured response bytes. Final targeted command
  `python -m pytest -q tests/test_runtime_request_contract.py -k spawned_selected`:
  4 passed, 39 deselected.
- An intermediate broader run while correcting the broker fixtures completed
  with 339 passed, 4 failed; failures were the four missing trace-binding fixture
  assertions above. Final broader result is recorded below.

Final new-suite command:

`python -m pytest -q tests/test_cognition_request_contract.py tests/test_runtime_request_contract.py`

Result: 57 passed. Coverage includes exact legacy fingerprints, selected-instance
isolation, invalid helper/client/config selectors, canonical persisted restrictions,
public help and fresh run/serve normalization, rejection on recorded/inspection/
analysis/replay, same/changed resume/fork selection, both spawned provider request
and response retention, real work gateway acceptance/rejection, selected archived
fresh/cold restart, sealed source-selected offline replay and replay descendant
resume, exact checkpoint/cursor equality, source bytes/mtime preservation, and
both directions of incompatible fork reuse prevention plus same-selector reuse.

Final focused regression command:

`python -m pytest -q tests/test_cognition_request_contract.py tests/test_runtime_request_contract.py tests/test_local_llm_cognition_format.py tests/test_ollama_cognition_client.py tests/test_llama_cpp_cognition_client.py tests/test_runtime_llama_cpp.py tests/test_runtime_journal_replay.py tests/test_runtime_cli.py tests/test_inference_trace_storage.py tests/test_work_action_gateway.py tests/test_external_dispatch.py`

Result: 346 passed in 88.95 seconds; no warnings, failures or skips reported.

Scoped Ruff/Black commands covered the seven changed product Python files, both
new test files and the amended existing test file: `ruff check <10 paths>` passed;
`black --check <10 paths>` passed, all 10 unchanged. Initial style checks found
11 fixable import ordering issues and six formatting changes; applied only inside
allowed paths and reran cleanly. A separate optional `mypy <7 product paths>`
attempt could not run because the supplied venv has no mypy executable (exit 127).
The repository Makefile has no mypy gate; no dependency was installed.
A final manual trailing-whitespace/final-newline scan of all 12 allowed changed
paths found no issues. Root retains the authoritative `git diff --check` gate.

## Limits and root handoff

No real model/backend compatibility claim follows from these fixtures. Root owns
independent review, full current-tree `make`/examples/whitespace and task-specific
acceptance gates, native Ollama and llama.cpp verification, exact native trace
retention and provider-offline replay, integration and VCS transitions. Ordinary
fake broker actions prove unchanged gateway execution/rejection, not model
reliability, successful settlement progression or full LN09 acceptance.


## Root task validation

Independent spec+qualityPASS/NO SUBSTANTIVE FINDINGS, including canonicalprovider
serialization check. `make VENV=<task24venv>`PASS2872tests/10existing deliberate skips
718.03s, actualChrome/39examples; separateexamples39/whitespacePASS. Exactcanonical26/
priorhash/read-only/CLI7/sourceServe4/wheel14+Serve4/41normalattempts/native-reader
9archives30localcalls/installedwheelAPI8+actualChrome exactdownload/CLI16+twoactual
signals/custodycleanup/sourcebytes+mtimesunchanged allPASS. Alljobs0 prefixln09g-task/
session85924. Reviewedsourceac9987f39532b33e97ffc8425d52fb563e0a3f4bb852f7ee90b831b211d9306f/302files unchanged.
Taskdelivery ready; nativecompatibility probes and featureintegration/repeatedgates
stillpending. No fullLN09acceptance claim. Ownerpatch/branches/worktrees retained.
