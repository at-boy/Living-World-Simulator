# Task 15 subagent prompt — FastAPI-hosted World Inspector

Work only in the assigned isolated checkout on `task/15-world-inspector-ui`
after Task22 reviewed integration. Read `AGENTS.md`, the complete matching
15_world_inspector_ui.md contract and only directly relevant API, DTO, tests,
packaging and operator documents. Root supplies milestone context; do not read
historical reports, full roadmap/backlog or continuation brief independently.

Implement the exact packaged HTML/CSS/JavaScript inspector with no Node build,
framework, CDN, mutation controls or spatial view. The binding plan supplies
closed routes, sources, core-shape validation, deterministic rendering,
read-only snapshot semantics, errors, race handling, accessibility and allowed
files. Dynamic values must remain literal text. Definition-only resources
must not be presented as stocks: use explicit entity resource attributes.
Do not infer outcomes, reservations, quantities, hidden NPC interpretations,
or live synchronization between processes.

Use TDD with focused typed API tests and actual Playwright browser tests.
Use installed /usr/bin/google-chrome headless with isolated temporary profile
(or supported explicit executable override); root already verified this tool
can launch. Development environment installs dependencies and Playwright only,
not editable project; use PYTHONPATH=src for project imports. No new unexplained
browser skips on this host. Browser tests must exercise actual navigation,
entity/history drill-down, failure/empty/loading/race states, narrow viewport,
keyboard and literal HTML-shaped text. Capture GET-only requests and compare
engine state/events before/after. Document extension entry points for Task15c.

Stay inside exact allowed files. Notify root of concrete prerequisite defects;
do not widen scope or silently change DTO/domain/cognition/persistence code.
Update changelog/journal/backlog and required truthful report. Report focused
commands/results/counts/warnings and TDD red/green evidence without logs.
Do not run full repository gates: root owns final make, separate examples,
browser and installed-wheel checks after independent review. Do not stage,
commit, merge, push, change branches, or spawn agents. Hand stable uncommitted
changes and report to root for independent review.
