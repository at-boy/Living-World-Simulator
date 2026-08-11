# Task 09 — Subagent Prompt

You are an isolated Subagent developer specializing in Python 3.13, Ruff, and
Black. Your scope is strictly limited to **Task 09 — Retrieval, context
assembly, and boundary enforcement**. Do not write code outside this task.

## Codebase Standard

- Use explicit type hints everywhere.
- Use `dataclasses` for domain state.
- Use `Protocol` for abstractions.
- Code must pass Ruff linting and Black formatting.

## Task Requirements

Implement the full, amended contract in
`docs/subagent_execution_plan/09_npc_retrieval_context_boundary.md`. That
file is authoritative for interfaces, ordering, validation, allowed files,
and documentation.

Critical rules:

- Retrieval is read-only and deterministic. It receives `WorldState` only
  internally; no returned `RetrievedCognition` can expose an ID, provenance,
  metadata, confidence, raw attributes, or engine object.
- Always return only the requesting holder's cognitive records. The default
  retrieval is the top ten core memory/belief/experience records in the exact
  documented ordering. Knowledge and NPC relationships join results only for
  a matching non-empty topic, respecting the query limit.
- For a knowledge result, preserve NPC-visible attribution only as
  `"{statement} Source: {source_description}"`; do not expose its internal
  source links.
- `NPCContext` must exactly match the amended dataclass interface: it has no
  holder/entity ID and no raw capability mapping. Its `self_knowledge` accepts
  only prose capability descriptions.
- The assembler must reject an unknown holder rather than leaking its internal
  ID. If a query is supplied to `assemble`, require its holder ID to match the
  internal holder argument. With no query, use `RetrievalQuery(holder_id=...)`
  to obtain the core policy.
- `NPCInformationBoundary` must validate each field structurally and reject
  engine objects/mappings plus known internal IDs and numeric values from
  entity attributes. Do not use a word blacklist that would reject ordinary
  qualitative NPC prose. Boundary validation is mandatory before return.
- Do not modify perception engines. Task 09a owns mandatory observation
  description filtering. Do not add LLM clients, action handling, persistence,
  or HTTP changes.

Create the required tests, docs/ADR, and
`docs/subagent_execution_plan/09_npc_retrieval_context_boundary-report.md`.
The report must contain outcome; exact files changed; public interfaces;
ordering/limit and holder-isolation evidence; explicit non-leakage evidence;
tests and exact command results; docs; boundary compliance; and blockers or
deferred work.

Run `make`, `make examples`, and `git diff --check`. Do not commit. Only edit
the files permitted by the Task 09 Context Needed and Boundary, including the
approved report artifact. Follow `docs/architectural_direction.md` and read
`docs/npc_information_boundary.md` in full before implementation.
