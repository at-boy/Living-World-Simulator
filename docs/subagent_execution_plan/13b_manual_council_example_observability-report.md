# Task 13b — Manual council-example observability report

## Delivered

Both opt-in council examples now export `format_council_result(result)` and
print its output. The first attendance result is explicitly rendered as the
`caller`; later entries are rendered as `invitee`s. A caller-only result now
states: “Only the caller attended; no invited NPC joined.” It does not infer
why an invitee is absent. Caller-only detection examines entries after the
caller and confirms that none is attending; it does not use the number of
attendance records, because the result includes absent invitees. The matching
empty-debate message says no debate was held because no invited NPC joined.
Existing safe attendance, delegation, dialogue, proposal, majority-proposal,
and gateway-resolution output remains visible.

`docs/local_llm_setup.md` now explains that identical successive outcomes are
valid: the examples submit equivalent constrained requests and rely on the
provider/model sampling defaults. No seed, temperature, or other sampling
control was added. The changelog and project journal record the clarification.

## Test evidence

`tests/test_manual_council_examples.py` loads each example with
`importlib.util` and never calls `main()` or `_run()`. It formats constructed
`CouncilResult` values only, so test collection and execution do not contact a
model provider. Coverage verifies the realistic caller-plus-absent-invitee
shape and caller-only wording, caller/invitee markers, visible invited-attendee
dialogue and proposal output, and `TypeError` for a non-`CouncilResult`
argument.

## Validation

- `PYTHONPATH=src .venv/bin/pytest tests/test_manual_council_examples.py`:
  passed, 6 tests in 0.06 seconds.
- `make`: passed; Ruff and Black checks passed, 305 tests passed, and the
  standard numbered examples passed. The manual examples were not run.
- `make examples`: passed; all standard numbered examples passed. The manual
  examples were not run.
- `git diff --check`: passed.

## Changed files

- `examples/manual/ollama_council_meeting.py`
- `examples/manual/llama_cpp_council_meeting.py`
- `tests/test_manual_council_examples.py`
- `docs/local_llm_setup.md`
- `CHANGELOG.md`
- `docs/project_journal.md`
- this report

## Boundary and deferred work

Only the Task 13b examples, documentation, test, and report are changed. No
council semantics, result types, provider clients, sampling controls, action
resolution, fixtures, or Makefile changed. No blockers or deferred work.
