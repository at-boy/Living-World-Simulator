# Protected saved trace analysis

The existing privileged operator app mounts `/analysis`. Python callers can build
an inert standalone FastAPI app with `create_analysis_app(catalog, auth=auth)` from
`living_world.api.trace_analysis`, passing a `RunCatalog` and the existing
`AdminSession`. This factory owns no runtime, controller, model, provider, lease or
attempt allocation. The supported `living-world analyze` command serves this app on IPv4 loopback.
Use the existing loopback authentication and Origin policy. Raw evidence is privileged operator data, never NPC knowledge.

All routes are GET-only and require `Authorization: Bearer <session token>`.
If supplied, Origin must match the session Origin. Responses include
`Cache-Control: no-store`; the standalone app exposes no docs/OpenAPI endpoints.
There is no CORS policy granting other sites access.

- `/analysis/status` reports live/offline mode, read-only access and capabilities.
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
its own finite journal/body budgets and supports rollback-journal SQLite only;
WAL/SHM sources are rejected to avoid coordination-file writes.

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
snapshot. Browser trace UI and portable/forensic export remain separate work.

Run saved-trace analysis with the server extra installed:

```sh
living-world analyze --archive-root /path/to/runs --port 8000 \
  --admin-token-file /private/existing-directory/analysis-token
```

The default archive root is the existing RunCatalog state location; port 8000 is
the default and port 0 selects an ephemeral port. The command binds only
`127.0.0.1` and announces `analysis_url=http://127.0.0.1:PORT/analysis/status`
after HTTP startup. This is an authenticated JSON endpoint, not a browser UI.
Send the token as a Bearer authorization header, never in a URL. SIGINT and
SIGTERM stop the owned HTTP service. No world, runtime owner, attempt reservation,
provider preflight, model call or source repair occurs. An absent catalog remains
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
