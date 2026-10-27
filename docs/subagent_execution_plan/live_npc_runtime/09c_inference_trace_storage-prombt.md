# Saved worker prompt — LN09c exact trace storage

Read AGENTS.md and 09c_inference_trace_storage.md in this directory first. The task is
your complete requirements, exact interfaces, scope and tests; do not reconstruct the
milestone/roadmap/history or read the owner master plan. Implement only seven worker paths
listed there, using TDD. Root owns architectural decisions and follow-on capture/admin
contracts. New storage must not claim those consumers are implemented.

Use existing task24 VENV and scoped tests/style. No Git mutations, index, commits,
subagents, full make/examples, real providers, downloads or other checkout changes.
If a required producer or architectural ambiguity is outside scope, report it before
editing. Preserve every existing edit. Record RED/GREEN, commands/results/counts, scope,
limitations and concerns in 09c_inference_trace_storage-report.md. Return only status,
one-line test summary, changed paths and concerns; root handles review/full gates/VCS.

Root correction before implementation: Ollama uses existing /api/generate endpoint,
not /api/chat; preserve actual current client protocol and exact payload behavior.

Root scope amendment: tests/test_run_archive_store.py may change ONLY existing future-
format corruption fixture from format2 to format3; format2 is now deliberately supported.
