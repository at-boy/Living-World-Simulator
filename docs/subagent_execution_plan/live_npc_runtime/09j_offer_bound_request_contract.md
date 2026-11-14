# LN09j — Offer-bound request contract

Owner approved November 14, 2026, following the Nov 13 schema-only diagnostic.
Base `9b6dbee`. Deliver a separately selected, canonical-live-founders-only
provider request format, `founders_offer_bound_v1`. The parser, gateway,
world rules, work-interruption policy and native acceptance criteria are frozen.

## Exact contract

- Extend RequestContract Literal and both stock run/serve selector choices.
  Default and explicit legacy rules are unchanged. Persist both nonlegacy
  selectors only for canonical_founders_v1, mode ollama (both provider kinds).
  Reject unknown/type-invalid/raw explicit legacy just as before. Source
  selection drives resume/replay. Changed resume rejects; explicit fork can
  change selector per existing rules. No change to fingerprint logic.
- request_contract_format retains existing signature; new selector returns the
  exact same instructions and independent base empty-arguments schema as
  founders_empty_arguments_v1. New helper
  `offer_bound_response_schema(schema: dict[str, object], actions: tuple[ActionOption, ...]) -> dict[str, object]`
  performs a fresh deep copy, validates action tuple using existing structural
  validation, changes only properties.action_request. No offers -> {"type":"null"}.
  Otherwise {"anyOf":[{"type":"null"},...]} with one object branch for each key
  in supplied action order. Clone the original action schema into each branch;
  set type object (not nullable), retain required fields and closed extra
  fields, set action_key to {"type":"string","enum":[key]}, set target_label
  to {"type":"string","enum":[...labels in supplied order...]} or
  {"type":"null"} for targetless keys. Retain exact empty arguments schema
  and rationale field. Do not add any instruction, other request fields, prompt
  changes, response repair, retry, fallback or substitutions.
- Both clients store whether new selector picked and call helper per request
  only for that selection. Ollama format, llama.cpp response_format.schema.
  No mutation of shared/instance schema or offers. Keep bytes, digests and
  public defaults of both old modes unchanged. Replay reconstructs exact
  request through existing factory; size callbacks and existing request cap
  apply to the entire wire payload, including duplicated labels.
- Engine truth, perception, memory, inference inputs, hidden identifiers and
  selected qualitative descriptions are unchanged. Schema repeats only the
  already filtered public keys/labels. Model output remains untrusted;
  unchanged parser and authoritative domain gateway still apply. No archived
  bodies, archive/driver/world schema, disturbance, operator or work changes.

## Worker boundary

Production only: cognition/local_llm_cognition_format.py,
cognition/ollama_cognition_client.py, cognition/llama_cpp_cognition_client.py,
runtime/broker.py, archives/model.py, cli.py (all under src/living_world).
Tests only: tests/test_cognition_request_contract.py and
tests/test_runtime_request_contract.py. Docs: one short information-boundary
addition in docs/npc_information_boundary.md and own matching -report.md.
Root owns exact contract/prompt, common docs, user guide updates in
docs/live_npc_runtime.md, native evidence in the matching -report.md,
final gates, Git/integration.
Any missing seam must be raised before expanding these paths.

## Evidence checklist

- [x] TDD RED first; pin old empty-arguments payload bytes from base before edits
  (existing legacy goldens remain). Unit tests for both wire formats, zero offers,
  multiple keys with disjoint targets, targetless action, exact empty arguments,
  deterministic order and isolation of returned mutable schemas.
- [x] Runtime/config tests preserve old mode behavior, cover CLI run/serve new
  opt-in and persistence, canonical restrictions, resume/fork selection,
  unchanged parsing/rejection and unchanged no argument repair.
- [x] Exercise actual archive through existing fake HTTP/spawned broker test
  harness, both backends where viable using existing fixtures; new offer-bound
  body captured, cold resume + provider-offline sealed replay, exact snapshots/
  events/cursors/body source identity. Synthetic provider tests are not native
  acceptance; use full stock runtime paths and existing fixtures.
- [x] Focused GREEN, scoped Ruff/Black/whitespace and worker report. Freeze for
  independent review. No full gates, models, downloads or Git by worker.
- [x] Root native actual runtime and offline replay on both providers with exact
  retained request evidence and owned server cleanup. Unmet campaign/interruption
  criteria stay explicit in the matching report.
- [x] Full make, separate examples, whitespace, retained
  installed wheel/3.11/browser/CLI/canonical checks, task commit/push and repeated
  merged gates before feature push; preserve worktrees, edits and refs.
