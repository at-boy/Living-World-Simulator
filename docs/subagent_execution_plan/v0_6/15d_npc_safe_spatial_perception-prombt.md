# Task 15d subagent prompt — NPC-safe spatial perception translation

Work only on `task/15d-npc-spatial-perception` after the planning amendments
land on `milestone/v0.6`. Implement the binding Task 15d plan: translate only
the explicitly supplied observer, subject, placements, and caller-filtered
direct road into deterministic qualitative `Observation` prose.

Preserve the NPC boundary. Exact coordinates/dimensions, placement records,
inspection DTOs, internal IDs, arbitrary `WorldState`, and hidden relationships
must never enter NPC-facing prose or context. Strengthen both perception-time
and final context checks, including the documented stored-observation
coordinate-leak regression. Do not add visibility inference, distance bands,
pathfinding, movement, terrain, travel cost/time, persistence, HTTP, UI, work,
or action behavior.

Stay within the exact allowed-file boundary, add the numbered example and a
truthful Task 15d report, run focused tests, `make`, separate `make examples`,
and `git diff --check`, and do not commit, merge, push, or change branches.
Amend both this prompt and the plan before expanding the boundary.
