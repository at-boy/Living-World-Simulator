# LN09f5b — Offline historical-world inspection implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox tracking.

**Goal:** Inspect an explicitly chosen saved world checkpoint alongside saved LLM calls, without starting or claiming ownership of a simulation.
**Architecture:** An offline-only selected-world source reconstructs validated detached inspectors and keeps an eight-entry LRU. Authenticated historical routes reuse the existing inspector panels; the offline analysis parent embeds one immutable checkpoint using the established same-origin credential handshake.
**Tech Stack:** Python >=3.11, FastAPI, existing SQLite archives, vanilla JS, pytest/actual Chrome.
**Spec:** `docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md`, approved parent implementation plan, docs/trace_analysis.md; LN09f5a shared read-only guard is prerequisite.

## Global Constraints

- RuntimeService solewriter; managers mutate, systems own behavior, events immutable. NPC contexts stay filtered; LLM output remains an untrusted proposal through ordinary gateway.
- Offline app must not construct controllers/services/providers/preflights, reserve attempts, acquire or probe ownership locks, or start execution loops.
- Trace discovery/reading never reconstructs worlds. Historical world reconstruction occurs only after explicit authenticated checkpoint selection.
- Keep existing live/operator/ordinary inspector behavior, trace APIs/status DTOs, archive schemas, input validation and simulation architecture unchanged.
- Preserve all source bytes/mtimes, branches/worktrees and owner edit. Root owns contracts/common docs/Git/full validation/integration; never main/milestone/tag.

## Review Focus

- Unauthorized/malformed requests: no catalog/filesystem/world reads before authentication and canonical validation.
- One corrupt archive or absent world: selected-only safe error, other trace evidence remains usable.
- Selection/revision/logout races: stale HTML/messages must not restore an old frame or credential.
- Reconstruction cache: exact checkpoint pin, bounded LRU8, failures don't evict valid views; disclose detached cached semantics.
- Read-only offline operation and packaging: no simulation owner, no new archives, source bytes/mtimes unchanged, actual Chrome and installed package work.

## Task 1: Selected source, protected routes and offline parent viewer

**Worker allowed files (ten):**
- Create src/living_world/api/analysis_revision_source.py (selected-only loader/cache).
- Create src/living_world/api/analysis_inspection.py (fixed assets and authenticated historical routes).
- Modify src/living_world/api/trace_analysis.py: import/mount offline inspection router in create_analysis_app only.
- Modify src/living_world/api/static/analysis.html, analysis.js, analysis.css (existing parent resources).
- Create tests/test_analysis_inspection.py and tests/test_analysis_inspection_browser.py.
- Modify docs/trace_analysis.md (operator instructions and truthful integrity/cache scope).
- Create docs/subagent_execution_plan/live_npc_runtime/09f5b_offline_world_inspection-report.md.

**Interfaces and root decisions:**
1. New AnalysisRevisionSource(catalog: RunCatalog), open(attempt_id: str, revision: int) -> WorldInspector. Reuse RevisionSourceError codes. Validate canonical UUID and exact nonnegative int before storage. Lock serializes cache/reconstruction; LRU8 keyed(attempt,revision), cached view survives source changes deliberately; failed miss doesn't insert/evict. On miss use resolve_trace_attempt for shallow safe/unique selected identity; absent database lstat FileNotFound=>not_found, other malformed entry=>archive_invalid. Call catalog.open_attempt(...,read_only=True) for full selected publication/input validation, latest None or requested>latest=>not_found; load_archived_inspection then EngineWorldInspector. Do not call catalog.attempts or weaken loader. No global RevisionSource changes. Importing existing types is allowed; constructing forbidden runtime objects isn't.
2. New create_analysis_inspection_router(catalog:RunCatalog, *, auth:AdminSession)->APIRouter. Expose only fixed public /inspector/assets/inspector.css and inspector.js bytes/media (same packaged assets); arbitrary names404. Protected GET /archives/{attempt_id}/checkpoints/{revision}/inspector and existing world-panel suffixes via create_inspection_router unchanged. All protected requests authenticate before resolving source or accessing storage. Revision parameter string parsed after auth: ASCII decimal digits, length1..20, <=9007199254740991, leading zeros accepted/canonicalized, invalid=>404not_found. ID invalid/unknown/unsafe/duplicate=>404not_found per shallow resolver. Selected corrupt archive/inputs/reconstruction=>409archive_invalid fixed sanitized. Unpublished or out-of-range checkpoint=>404not_found. Source errors never expose paths/exception text.
3. Protected HTML validates exact source first, then injects canonical data-inspection-prefix and data-inspection-kind=historical into existing inspector.html exactly once, matching operator pattern. No arbitrary queryprefix/token bootstrap; no new control routes, openAPI or live route. Factory mount onlyoffline; public static helpers never touch catalog. Existing no-store applies all responses. All panels resolve same cached exact inspector.
4. Extend parent analysis assets: authenticated existingstatus.mode offline reveals a saved-world section for selectedattempt; live mode hides it. Keep existingstatus DTO unchanged: create_trace_analysis_router status describes its call-evidence path, not the separate /archives historical namespace; document that distinction. Replace shell paragraph claiming no world validation with plain copy: Browse saved calls without loading a world. In offline mode, inspect a chosen saved checkpoint. Explicit labeled checkpoint revision number input default0, safe nonnegativeinteger validation before fetch; button 'Inspect checkpoint'; input id world-revision, status id world-status, container id world-preview and iframe title 'Saved World Inspector'. Never auto-reconstruct upon listing/call selection/login. No latest/checkpoint-list API. User-facing text identifies detached historical checkpoint and that previously loaded cached views aren't revalidated against later file changes. Failed world selection clears old frame and shows fixed friendly error but preserves calls/body evidence.
5. Credential stays closurememory; never URLs/storage/DOM/srcdoc interpolation. Reuse authenticated fetch helper with html mode, all existingtrace behavior retained. Frame from authenticated protectedHTML in iframe.srcdoc; exact event origin/source and single-key ready schema before connect postMessage. Historical HTML owns fixedpin; send token only on exact ready from currentframe, no repinning. Generation/attemptselection/frame tickets and AbortControllers reject late HTML and ready events. Clear/remove frame on attemptchange, revisioninputchange, refreshreset, disconnect, login/authfail and failed selection. Late old response/401 must not clear a newlogin. No polling, controls or background worldload.
6. No new assets or pyproject packaging changes; count14 remains. Public shell may keep existing Saved LLM Calls title, add offline-only section. Existing live/operator/ordinary viewer tests remain unchanged.

- [ ] Write meaningful RED source/API tests before implementation: actual retained two-checkpoint world exact panels; selected-only load with unrelated corruption; auth-before-filesystem spies; bad IDs/revisions and absent root create nothing; unavailable404/corrupt409 sanitized; cache pinning/LRU8/failure preservation/concurrency and source inventory.
- [ ] Implement source and router; mount only offline; keep source reads within existing guard/loader and no ownership probes/runtime constructors.
- [ ] Add parent controls with exact handshake/race rules and actual Chrome regression tests: login, explicit revision0/1 and real iframe panel content, malformed local revision nofetch, attempt/revision/disconnect/auth clears, staleHTML/ready rejected, credential not persisted/interpolated, failedworld leaves actual callpreview usable, live mode controls hidden/no offline route. Use real HTTP app and project browser fixtures/patterns with finally cleanup; no fake success-only page tests.
- [ ] Focused tests: new suites + tests/test_trace_browser.py tests/test_trace_analysis_api.py tests/test_runtime_revision_source.py tests/test_runtime_inspector_browser.py tests/test_world_inspector_ui.py. Use task24venv/PYTHONPATH=src; Chrome tests require root-authorized loopback/headless execution (ask root to run if sandbox blocks). Scoped Ruff/Black and whitespace. Report commands/counts/warnings, RED/GREEN, files, limits and self-review; freeze. No Git/full gates/models/dependencyinstall/helpers.
- [ ] Root independent review and corrections; full task gates with existing native evidence/installed wheel/browser, plus explicit installed-wheel historical inspection proof. Commit validated delivery, noff feature integration, repeated full gates before featurepush. Full both-provider behavioral acceptance remains separate.

Root preflight: selected-only source intentionally does not reuse RevisionSource.open, which enumerates unrelated archives and probes ownership. HTML prefixes match inspector.js; cache semantics match existing detachedviewer but are disclosed. Parent extends existingresources so packagingcounts don't change. No further architectural decisions delegated.
