# Saved LN08b local authenticated operator API prompt

Implement exact 08b_operator_api.md after reviewed LN08a integration in the isolated
task checkout. Read AGENTS.md, whole exact task and this saved prompt first; only
directly relevant code/tests afterwards. No handoff/backlog/roadmap/history/masterplan
reconstruction. Root owns architecture and task/plan/scope decisions.

Eight worker paths only. Keep AdminSession secrets memory-only and hidden from repr,
headers-only Bearer plus exact Origin/CSRF guard, arbitrary malformed header safety,
fixed errors/no-store and no CORS. New readonly service.controller getter verifies
service/controller identity; status is one immutable complete publication. HTTP never
constructs/steps/mutates engine/controller: submit Future through service, async wait
for durable admission, distinguish queued from applied ACK. Archive reads and existing
RevisionSource/router own fixed readonly revisions, failed attempts remain valuable.
Exact DTO/config-source/no-world/error/journal-limit/lifespan/client-helper decisions
are in task. No browser/CLI/serve/player/remote API or adjacent refactor here.

Genuine RED/GREEN, existing ASGIClient extension/reuse, fake provider plus actual
uvicorn loopback case, focused tests/style/whitespace/self-review and truthful own
report. No VCS/index/commits/worktrees/subagents/fullmake/examples/installs/realmodel/
othercheckout writes. Important gap ->root before choosing architecture or expanding.
Unit temp fixtures allowed; every normal manual simulation retains its archive.
Root independent SPEC/QUALITY review, corrections/re-review and authoritative full
checks before any implementation commit/integration. Honor usage checkpoint promptly;
stop before10%five-hour remaining as root directs.
