# Protected saved trace analysis

The existing privileged operator app mounts `/analysis`. Python callers can build
an inert standalone FastAPI app with `create_analysis_app(catalog, auth=auth)` from
`living_world.api.trace_analysis`, passing a `RunCatalog` and the existing
`AdminSession`. This factory owns no runtime, controller, model, provider, lease or
attempt allocation. The supported `living-world analyze` command serves this app on IPv4 loopback.
Use the existing loopback authentication and Origin policy. Raw evidence is privileged operator data, never NPC knowledge.

The public static shell `/analysis` and its two fixed assets contain no private
evidence or credentials. All evidence routes below are GET-only and require
`Authorization: Bearer <session token>`.
If supplied, Origin must match the session Origin. Responses include
`Cache-Control: no-store`; the standalone app exposes no docs/OpenAPI endpoints.
There is no CORS policy granting other sites access.

- `/analysis/status` reports live/offline mode, read-only access and call-evidence
  capabilities. Its unchanged `world_validation: not_performed` describes the
  `/analysis` call-evidence path, not explicit historical inspection in the
  separate `/archives` namespace below.
- `/analysis/attempts` lists shallow identities and reservation syntax status.
  `limit` defaults to 50 (maximum 100); use both `after_lineage_id` and
  `after_attempt_id` from `next_after` for another page. `listing: current` means
  a refresh can discover insertions before an earlier cursor. Missing, invalid,
  failed-initialization and no-checkpoint attempts can still appear. No absolute
  storage paths, settings or raw bodies are returned in this listing.
- `/analysis/attempts/{attempt_id}/traces` returns trace metadata, all call fields,
  and a sealed journal boundary. Optionally supply both `through_sequence` and
  `journal_digest`; sequence zero is valid. Use `after_sequence` and `limit` for
  pages and retain the returned boundary across appends. Unknown legacy timing
  and body metadata remain null; original elapsed integer/float values and
  reused source references retain their original meaning.
- `/analysis/attempts/{attempt_id}/bodies/{sha256}` requires the explicit boundary
  pair and verifies the entire selected body before returning exact bytes as an
  octet-stream attachment with a fixed digest-based filename and `nosniff`.
- The same body URL followed by `/preview` returns JSON containing a UTF-8 text
  preview of at most 65,536 source bytes. Invalid or split UTF-8 uses replacement
  characters and reports `replacement_used`; `truncated` records whether bytes
  were omitted. Text may contain unsafe HTML or invalid JSON: treat it as text.
  Exact empty, invalid, partial and error response bytes remain in the separate
  download when captured.

Discovery counts all inspected root/lineage entries (including ignored names),
with a default 10,000 entry budget. Only selected page headers are read, bounded
to 1 MiB each. No recursion through attempt contents, world/checkpoint loading,
provider preflight, owner lock probing, source repair or cache/index creation is
performed. Symlinks and non-independent files fail closed. The trace reader has
its own finite journal/body budgets. The trace reader and full-store
`AttemptArchive.open(..., read_only=True)` share a read-only SQLite precheck on
every connection: only existing regular non-symlink files with a complete SQLite
header declaring rollback read/write versions are accepted. External WAL-mode
databases are rejected even without sidecars; existing or dangling WAL/SHM
sidecars are also rejected before SQLite opens. Ordinary rollback `-journal`
files remain supported, including an active product writer transaction. Full-store
standalone references and hardlinks retain their existing support; trace analysis
retains its stricter catalog/path checks.

The precheck preserves source bytes and modification times for rejected sources;
source access times are outside this claim. It is not a snapshot protected against
hostile filesystem races and does not bound native SQLite parser memory. No
migration, recovery or conversion is performed. Product rollback writers and
the full store's default writable access retain their existing behavior.

Errors use fixed codes: 400 `invalid_query`, 401 `unauthorized`, 403 `forbidden`,
404 `not_found` for invalid/unknown/duplicate/unsafe attempt identity,
409 `trace_unavailable`, and 413 `analysis_limit_exceeded`. Framework scalar
query parsing may return 422. Responses never include internal exception text.

`reservation_metadata_checked` checks reservation syntax only.
`trace_metadata_checked` checks the selected trace prefix; `selected_body_verified`
additionally verifies the selected exact body. These labels do not certify a
complete world, lifecycle consistency, parent ancestry or model behavior. A
corrupt unrelated body is outside selected-body hash verification. Concurrent
filesystem changes can invalidate a request; this is not a sealed catalog
snapshot. Portable/forensic export remains separate work.

Run saved-trace analysis with the server extra installed:

```sh
living-world analyze --archive-root /path/to/runs --port 8000 \
  --admin-token-file /private/existing-directory/analysis-token
```

The default archive root is the existing RunCatalog state location; port 8000 is
the default and port 0 selects an ephemeral port. The command binds only
`127.0.0.1` and announces `analysis_url=http://127.0.0.1:PORT/analysis/status`
after HTTP startup, then `analysis_browser_url=http://127.0.0.1:PORT/analysis`.
The original status URL remains an authenticated JSON endpoint.
Send the token as a Bearer authorization header, never in a URL. SIGINT and
SIGTERM stop the owned HTTP service. Startup and trace browsing load no world.
Only explicit historical checkpoint inspection reconstructs a detached world;
no runtime owner, attempt reservation, provider preflight, model call or source
repair occurs. An absent catalog remains
absent through startup, reads and shutdown. Unsafe roots are rejected.

The token file must be a new file in an existing safe directory outside the
catalog and its ancestors. Existing files, links and source overlap are refused.
The exclusive file has mode 0600 and is removed on shutdown only when its
identity, permissions and bytes remain owned and unchanged. Modified, replaced
or hardlinked files are preserved. Same-UID check/unlink races remain best effort.
Without a token file, both stdout and stderr must be terminals; the token is then
printed to stderr only. File mode never prints the token or source/token paths.

Startup errors are fixed and sanitized: exit 2 `invalid_configuration` or
`server_unavailable`, exit 4 `credential_file_failed`, and exit 5 `server_failed`
or `service_failed`. The first primary failure is preserved. Otherwise HTTP,
thread or socket cleanup failures take exit 5, and credential cleanup alone takes
exit 4. Shutdown requests exit and waits up to 12 seconds for the HTTP thread;
an uncooperative live Python thread cannot be forcibly terminated.


Open `/analysis` in either the live operator or offline analyzer to use **Saved
LLM Calls**. The runtime page also links there without transferring credentials.
Enter the administrator token and Connect. The password field clears immediately;
the credential stays in page memory only. Disconnect, authorization rejection and
pagehide clear private state. Re-enter the token on another page or after leaving.
The page identifies live/offline mode and read-only access; it never starts a
simulation or model call.

Refresh attempts restarts a current catalog listing; More attempts uses the exact
paired cursor. Missing or invalid reservation rows remain visible. Valid archive
identities with a database can be selected independently of reservation syntax;
rows with invalid identities or no database have disabled selection. Select a call
to inspect its saved backend (`request_trace.provider_kind`), model and opaque
model identity, request/response metadata, timing and source mapping. Archive mode
is not an inference backend. Null fields display `unavailable`; known zero timings
remain zero. Pending calls, legacy/unavailable bodies, incomplete captured prefixes
and complete saved bodies have distinct labels. Reused calls explicitly identify
original reused evidence/timing rather than a new latency measurement.

Calls retain their first journal boundary across More calls and all body reads,
even if the archive grows. Refresh calls discards call selection and previews and
captures a new prefix. There is no polling. Each request times out after ten
seconds; changing selection, refreshing or disconnecting aborts obsolete reads.
Session and selection guards also discard late completions. Fixed error messages
distinguish unavailable/not-found (404), changed/invalid (409), and too-large (413).
Malformed DTOs fail closed and dynamic data is rendered only as text.

Preview request/response explicitly fetch a bounded **UTF-8 preview**, displaying
byte length, preview byte length, truncation, replacement and integrity labels.
This decoded preview is not exact binary evidence. Download request/response saves
opaque original bytes as `inference-<validated body digest>.bin`; incomplete saved
prefixes and observed empty bodies are downloadable. Missing bodies remain
unavailable. No parsing, reserialization, inferred full response, generation rate,
or export is provided by the trace controls. Trace controls use only the bounded
call-evidence API and do not broaden its integrity guarantees. Tokens are never
put into URLs, browser storage, cookies, links or logs.


In the offline analyzer, select an attempt and use **Saved world checkpoint**.
Enter a nonnegative **Checkpoint revision** (default 0), then select **Inspect
checkpoint**. Login, listing attempts and selecting calls never reconstruct a
world. There is no latest-checkpoint discovery, checkpoint listing, polling or
simulation control. The live Saved LLM Calls page hides this offline entry point;
the existing operator inspector remains available through its ordinary UI.

The explicit historical namespace supports authenticated GET
`/archives/{attempt_id}/checkpoints/{revision}/inspector` and the existing
`/world`, `/world/tick`, entity, event, cognitive and other inspector panel
suffixes under the same checkpoint prefix. Only fixed `inspector.css` and
`inspector.js` assets are public under `/inspector/assets/`. Authentication and
Origin checks precede selection/storage reads. IDs must be canonical UUID4 hex;
revision strings contain 1–20 ASCII decimal digits with value no greater than
9007199254740991. Leading zeros canonicalize to the same checkpoint. Invalid,
unknown, duplicate or unsafe identities and absent/unpublished/out-of-range worlds
return 404 `not_found`. Selected invalid archives, retained inputs or failed
reconstruction return sanitized 409 `archive_invalid` without source paths.
Other attempts and saved call/body evidence remain independently usable.

A cache miss resolves only the selected identity, validates its complete
publication through the existing read-only archive/loader path and reconstructs
that exact checkpoint. It does not enumerate full archive summaries or probe
ownership locks. This is stronger selected-world validation than trace metadata
inspection, but does not certify model behavior or imply ownership of a live
simulation. The same read-only SQLite guard and source-integrity limits above
apply: bytes and modification times remain unchanged; access times and hostile
filesystem races are outside that guarantee.

Each offline app serializes reconstruction and retains an eight-entry least
recently used cache of detached historical inspectors. Every panel uses the same
exact cached checkpoint. Failed misses neither insert nor evict valid views.
Previously loaded views deliberately survive later source changes without
revalidation until evicted or the app restarts. Opening the same revision is not
a fresh source-integrity check, and restarting is necessary to discard all cached
views immediately.

The parent fetches protected inspector HTML and embeds it in a same-origin frame
with an immutable historical prefix. Credentials remain in closure memory and
cross to the current frame only after its exact ready-message handshake; they
are never interpolated into HTML, URLs or storage. Changing attempt or revision,
refreshing calls/attempts, disconnecting, login/authentication failure and leaving
the page clear the frame. Obsolete HTML, ready messages and old authorization
rejections cannot restore it or clear a newer session. Failed world selection
clears its previous frame and shows a fixed error while preserving the selected
call and body preview.

## Saved evidence ZIP

Export one saved attempt without opening a world, starting a provider or acquiring
an attempt lease:

```console
living-world export-traces --archive-root /path/to/runs --attempt-id UUID4HEX --output /path/to/evidence.zip
```

`--archive-root` defaults to the ordinary local catalog. The output parent must
already exist. The destination must be new, outside the source catalog and free
of symlinks or `..` traversal. Existing files, directories and links are never
overwritten. The ZIP is private (0600), staged in its destination directory,
verified, synchronized and published exclusively. No HTTP export route exists.

Members are `calls.jsonl`, sorted `bodies/<sha256>.bin`, then `manifest.json`.
Calls use canonical JSON in request order and retain every saved call field,
including backend/model metadata, timestamps, zero and missing timings, reuse
provenance, pending responses and incomplete body states. Bodies are deduplicated
by their actual body digest and retain exact opaque bytes, including invalid
UTF-8, NUL and observed empty bodies. Unavailable or legacy evidence stays absent.
Nothing is parsed, redacted, repaired or synthesized from model output.

The canonical manifest format is `living-world-trace-evidence-v1`. It records
lineage/attempt identity, archive format, the captured journal sequence/digest,
call/body counts, and sorted member names, byte lengths and SHA256 hashes.
`manifest.json` does not hash itself. Fixed ZIP timestamps, permissions and stored
compression make repeated exports of the same prefix byte-identical. ZIP CRCs
and every member length/hash are independently checked before publication.

Integrity scope is `local_trace_prefix_and_selected_bodies`. All pages and body
reads use the first authenticated journal boundary, which is checked again
before publication. Later ordinary appends are supported. This is not a global
multi-file or hostile-race-proof snapshot. Source bytes and modification times
remain unchanged; access times are outside this guarantee. The omitted list is
`world_validation`, `ancestor_closure`, `uncommitted_spool`, `model_weights`,
`session_credentials`: no world closure, uncommitted response spool, model weight
files or current administrator credentials/session state are added. Archived
model metadata and opaque evidence bytes remain exact. This ZIP is not a
portable reopenable world catalog or proof of real-provider acceptance.

`--max-calls` defaults to 1000 (range 1–10000); `--max-output-bytes` defaults to
134217728 (range 1024–1073741824). Existing reader budgets still apply. Declared
body sizes are checked against the remaining output budget before loading bytes;
chunks, entries and the completed ZIP are checked too. Temporary ZIP headers and
the bounded central directory may exceed the configured output cap during
failure cleanup; no oversized final file is published.

SIGINT and SIGTERM request cooperative cancellation between pages, bodies and
chunks and before publication. Success exits 0 with
`trace_export=complete calls=N bodies=N`. Closed errors contain no paths, body
content or underlying diagnostics: `export_invalid` (2) covers invalid arguments
or output preflight; `trace_unavailable` (4) covers missing, unsafe or corrupt
selected sources; `export_limit_exceeded` (4) covers reader/export budgets;
`export_cancelled` (130) covers cancellation; `export_failed` (4) covers output
I/O, verification or exclusive-publication races. Before publication, failures
leave no final file and attempt cleanup of owned temporary files. If cleanup is
refused, the command reports failure and may leave the private temporary file.
After successful publication, directory-sync or cleanup failures report
`export_published_uncertain` (4) and preserve the complete published ZIP: crash
durability or temporary cleanup is uncertain. Foreign replacement files are
preserved, and existing final destinations are never removed.
