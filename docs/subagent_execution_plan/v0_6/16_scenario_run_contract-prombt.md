# Task 16 subagent prompt — scenario and deterministic run contract

Work only on `task/16-scenario-run-contract`, created from the reviewed
`milestone/v0.6`. Read `AGENTS.md`, all required documents, and
`16_scenario_run_contract.md` in full before editing. The task plan is binding.

Implement only the strict versioned scenario loader, deterministic initial
instantiation, durable run metadata, v0.5 snapshot compatibility, and detached
operator inspection described by Task 16. Preserve managers-own-mutation,
immutable events, strict dataclasses/protocol typing, and deterministic order.
Definitions must be reloaded and fingerprint-validated on resume; do not
silently persist them as arbitrary world attributes.

Never expose raw `WorldState`, internal IDs, scenario fingerprints, engine-only
metadata, or unrestricted configuration to NPC context. Do not implement the
Task 16a runner, goals, needs, work, external references, spatial state,
proposal tapes, or UI.

Stay inside the allowed-file boundary. If a required dependency falls outside
it, stop and request a documented plan amendment before editing. Add the
required tests, executable example, ADR/docs, changelog, journal, backlog, and
truthful `16_scenario_run_contract-report.md`. Run `make`, `make examples`, and
`git diff --check`. Do not commit, merge, push, or change branches; hand the
uncommitted delivery to the orchestrator for independent review.
