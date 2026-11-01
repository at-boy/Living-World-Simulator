# LN09f4 — Saved LLM call browser implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Status:** COMPLETE; independent spec/qualityPASS after one P2 addressed/zeroopen; task and repeatedmerged gates2815/10existing skips/allchecksPASS. Delivery7d3f793 preserved/pushed.
**Goal:** Browse exact saved LLM call evidence in both live operator and inert offline analyzer.
**Architecture:** A public static shell router mounts alongside the unchanged protected evidence router in both apps. Browser evidence requests use a memory-only administrator credential and existing bounded read APIs; no runtime, archive, provider or domain ownership changes.
**Tech Stack:** Python>=3.11, FastAPI, packaged plain HTML/CSS/JavaScript, existing pytest/Playwright/Chrome. No dependencies.
**Spec:** docs/superpowers/specs/2026-10-19-live-npc-runtime-design.md (approved); subsequent owner exact-request/response/backend/timing retention and browser-analysis requirements. Parent plan already approved for continuous execution; no new design approval is required.

## Global constraints

Managers own mutation, systems own behavior, events are immutable. RuntimeService remains sole world writer. LLM output remains an untrusted proposal through action gateways. Raw world/IDs/hidden cognition/privileged trace evidence never enters NPC contexts or ordinary inspection. This page only reads already saved admin evidence. No new world, simulation, lease, attempt, checkpoint loading, model call, export, archive migration, prompt/schema/gateway/config/fingerprint/replay change. Historical-world selection and export are subsequent tasks. Preserve run/serve/inspect and legacy analyze status announcement, protected auth/Origin/error/no-store semantics and all prior request bytes.

## Exact worker file boundary (14 paths)

1. NEW src/living_world/api/trace_browser.py
2. src/living_world/api/trace_analysis.py — import/mount public router in create_analysis_app only
3. src/living_world/api/operator.py — import/mount public router only
4. NEW src/living_world/api/static/analysis.html
5. NEW src/living_world/api/static/analysis.css
6. NEW src/living_world/api/static/analysis.js
7. src/living_world/api/static/runtime.html — fixed /analysis link only, no credential transfer
8. src/living_world/api/analysis_serving.py — second ready announcement only
9. pyproject.toml — add three package-data entries only
10. tests/test_runtime_browser.py — exact package-resource expectation only
11. NEW tests/test_trace_browser.py
12. tests/test_trace_analysis_cli.py — assert extra browser URL and preserved existing URL only
13. docs/trace_analysis.md — page usage, labels and limits
14. docs/subagent_execution_plan/live_npc_runtime/09f4_trace_browser-report.md

Root owns task/prombt/common docs, helper evidence, full validation, VCS/integration. Worker no other paths, index/commits/subagents/full make/examples/dependencies/native servers. Tests may use owned temp fixtures, subprocess and loopback; always reap/close in finally. Report missing seam before expanding scope.

## Public shell and integration

NEW create_trace_browser_router()->APIRouter in api/trace_browser.py. Serve /analysis HTML and exactly /analysis/assets/analysis.css and /analysis/assets/analysis.js using importlib.resources packaged bytes and correct media. No arbitrary filenames/traversal. Public responses contain no evidence, catalog metadata, token or nonce. Set Cache-Control:no-store. Unknown asset404. Mount separately alongside create_trace_analysis_router in both apps; preserve that router's global Depends(authorize) and data route behavior verbatim. This explicit static-only exception supersedes the earlier blanket statement that every /analysis route requires authentication. No runtime import/owner in the shell/offline factory.

After existing analysis_url={origin}/analysis/status readiness announcement, print a second line analysis_browser_url={origin}/analysis. Preserve lifecycle, errors, cleanup and original announcement verbatim. Add fixed link from runtime page. No token in link/URL.

## Browser contract

Title/heading Saved LLM Calls. Responsive light UI consistent with runtime. Labelled Administrator token password field, Connect, Disconnect, mode/live/offline and read-only indication; attempts and calls tables in local horizontal overflow containers, no body overflow at360px. Controls labelled Refresh attempts, More attempts, Refresh calls, More calls; body controls labelled Preview request, Download request, Preview response, Download response. Use semantic buttons/labels/status/pre; no dependency/framework.

Credential remains in closure memory only. Clear input at submission and all private DOM/state on disconnect,401/403 or pagehide. No URL/query/hash/storage/cookie/global/log persistence. Authenticate against /analysis/status; require access=read_only and mode in live/offline. All evidence GET same-origin fixed paths, Authorization Bearer, cache:no-store, credentials:omit. No CSRF on read-only requests. Request timeout10seconds with tracked AbortControllers. Abort on disconnect/selection replacement; session generation and attempt/call/body selection guards before/after every await prevent late old401/403 from clearing a new login and old JSON/body bytes repainting or downloading after selection/refresh/disconnect. Timeout/network/malformed DTO gives fixed friendly error with no raw exceptions/response/token log. Show fixed distinct unavailable/not-found404, changed-or-invalid409, too-large413 errors. Never fabricate missing evidence.

Validate DTO containers/types before rendering: attempt/cursor identifiers lowercase32hex UUID4 (version4 and variant8/9/a/b); body/content/journal SHA256 digests lowercase64hex; model_digest is an opaque nonempty saved identity string (never interpreted as a path or hash); sequence/revision/tick/count lengths nonnegative safe integers, finite nonnegative durations; enum body states only complete/incomplete/unavailable, null metadata allowed as API defines. Reject malformed DTOs without unsafe path construction or privileged HTML rendering. Optional unknown metadata fields may be ignored. Render dynamic data only through textContent/DOM text nodes, including malicious model text. No innerHTML/HTML interpretation.

Attempts: GET /analysis/attempts?limit=50, preserve exact paired next_after cursor, More appends; refresh restarts. Keep invalid/missing/legacy rows visible and select available valid IDs; invalid row never requests fabricated evidence. Calls: GET /analysis/attempts/{attempt}/traces?limit=50; capture returned boundary {sequence,digest} once and reuse through_sequence+journal_digest on later pages and every body request. More uses next_after_sequence (zero is valid; use null checks). Refresh calls clears selected call/previews/download state then captures a new prefix. Attempt change clears old call/boundary/state. Preserve stable prefix while archive grows; no silent refresh/automatic polling.

Call table/details expose actor_label, source_tick, response_kind, outcome/error, elapsed_seconds, request_trace.provider_kind, model and model_digest, request_id/sequence/base_revision and integrity/boundary. Use request_trace.provider_kind for actual Ollama/llama_cpp backend; archive legacy mode is not backend. Show trace metadata including method/url/headers/prepared_at/timeout/maxresponse, body lengths/digests/http_status, all stored response timestamps/durations (raw values, known zero preserved). No fabricated generation rate. Distinguish pending, legacy/unavailable, incomplete captured prefix and complete bodies. Empty observed body (length0/digest present) is downloadable. response_reused and source mapping clearly say original reused evidence/timing, not a new latency measurement; show saved source mapping as text. Null means unavailable, never zero.

Preview only on explicit click via existing /preview endpoint with selected digest+boundary; display text in pre with textContent, label UTF-8 preview, byte_length/preview_byte_length/truncated/replacement_used and integrity. Preview is at most existing65536bytes, not exact binary. Download exact bytes via authenticated GET to Blob, fixed inference-{validated_digest}.bin (no server arbitrary filenames). Guard session/selection after bytes await before synchronous URL/click. Track/revoke object URLs after download dispatch and on replacement/disconnect/pagehide; no stale downloads. Controls disabled when selected metadata has no body digest, enabled for incomplete captured prefixes and zero-byte bodies. Downloads are exact saved opaque bodies; no decoding/re-encoding, reparsing/reserialization or fabricated full response.

## Review focus and test cycle (one coherent deliverable)

- [x] RED focused public route/package/announcement assertions fail before implementation. Record exact command and meaningful failure.
- [x] Implement static router/mount/package/URL tests: both apps public shell/assets no secrets/no-store/allowlist; evidence still401/foreignOrigin403/POST405; offline construction spies reject world/runtime/provider creation and source bytes+mtimes/catalog IDs unchanged.
- [x] Implement HTML/CSS/JS and actual Chrome tests for both live/offline mounts: login, catalog/call paging and refresh, stable boundary after actual journal append, sequence0 handling, actual backend/model/digest/timings zero/null, pending/legacy/incomplete/reused/source labels, emptybody download, malformed DTO rejection, hostile text inert, mobile360px and desktop no body overflow.
- [x] Actual Chrome preview truncation/replacement and download capture (page.expect_download/read actual file) compare exact bytes and SHA256 including invalidUTF8/NUL; no token in URLs/storage/cookies/publicshell/logs, body data rendered only as text.
- [x] Delayed response tests cover old login401/403 after reconnect, attempt/call/refresh preview replacement, late body download after disconnect/reconnect or selection change, and request timeout. No stale repaint/session loss/download; URL revocation observed. Every held route and owned browser/server/thread/socket is released/closed in finally.
- [x] Focused current tests then scoped Ruff/Black/whitespace. VENV=.worktrees/task24/.venv, PYTHONPATH=src. Run python -m pytest -q tests/test_trace_browser.py tests/test_trace_analysis_api.py tests/test_trace_analysis_cli.py tests/test_runtime_browser.py; python -m ruff check changed Python; python -m black --check changed Python; git diff --check. Actual Chrome needs loopback permission, may not claim skipped cases pass.
- [x] Write own report: RED/GREEN commands/results/counts/warnings, file boundary, exact behavior/limitations. Freeze for fresh independent spec+quality review. Root resolves findings, runs required full gates before any implementation commit.

Root full task and repeated merged gates: make, separate make examples, diffcheck, exactcanonical26/priorhash/read-only/CLI7/sourceServe4, installedwheel14resources+Serve4, savednative9archives30calls, offlineAPI8, analyzeCLI16/two actualsignals and NEW actualChrome installedwheel offline page/login/preview/exactdownload/sourceunchanged. Preserve ownerpatch, all branches/worktrees; never main/milestone/tag. No fullLN09/nativegrammar/export acceptance claim.
