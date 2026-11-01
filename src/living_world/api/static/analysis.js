(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const uuid = v => typeof v === "string" && /^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$/.test(v);
  const digest = v => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
  const obj = v => v !== null && typeof v === "object" && !Array.isArray(v);
  const text = v => typeof v === "string";
  const uint = v => Number.isSafeInteger(v) && v >= 0;
  const duration = v => typeof v === "number" && Number.isFinite(v) && v >= 0;
  const nullable = (v, check) => v === null || check(v);
  const boundaryOK = v => obj(v) && uint(v.sequence) && digest(v.digest);
  const show = v => v === null || v === undefined ? "unavailable" : typeof v === "object" ? JSON.stringify(v, null, 2) : String(v);
  let token = "", generation = 0, attemptsVersion = 0, callsVersion = 0, bodyVersion = 0;
  let attempt = null, selected = null, boundary = null, attemptCursor = null, callCursor = null;
  const pending = new Set(), urls = new Set();
  const stale = Symbol("stale");
  const messages = {
    404: "Saved evidence unavailable or not found (404).",
    409: "Saved evidence changed or is invalid (409).",
    413: "Saved evidence exceeds the read limit (413)."
  };
  const notice = message => { $("notice").textContent = message; };
  const revoke = () => { for (const url of urls) URL.revokeObjectURL(url); urls.clear(); };
  function abort(scope) {
    for (const job of pending) if (!scope || job.scope === scope) job.controller.abort();
  }
  function clearBody() {
    bodyVersion++; abort("body"); revoke();
    $("preview").textContent = ""; $("preview-meta").textContent = "";
  }
  function clearCall() {
    clearBody(); selected = null;
    $("detail-panel").hidden = true; $("details").textContent = "";
    for (const side of ["request", "response"]) for (const op of ["preview", "download"]) $(op + "-" + side).disabled = true;
  }
  function clearCalls() {
    callsVersion++; abort("calls"); clearCall(); boundary = null; callCursor = null;
    $("calls").replaceChildren(); $("boundary").textContent = ""; $("more-calls").disabled = true;
  }
  function disconnect(message = "Disconnected.") {
    generation++; attemptsVersion++; abort(); token = ""; attempt = null; attemptCursor = null;
    clearCalls(); $("attempts").replaceChildren(); $("attempt-status").textContent = "";
    $("selected-attempt").textContent = ""; $("mode").textContent = "";
    $("token").value = ""; $("session").hidden = true; $("call-panel").hidden = true;
    $("disconnect").hidden = true; $("login").hidden = false; $("more-attempts").disabled = true;
    notice(message);
  }
  // A guard belongs to a specific session AND operation. It is checked after
  // every asynchronous boundary, including before interpreting HTTP rejection.
  async function read(path, scope, valid, binary = false) {
    if (!valid()) throw stale;
    const controller = new AbortController(), job = {controller, scope};
    pending.add(job);
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 10000);
    try {
      const response = await fetch(path, {
        method: "GET", headers: {Authorization: "Bearer " + token},
        cache: "no-store", credentials: "omit", signal: controller.signal
      });
      if (!valid()) throw stale;
      if (response.status === 401 || response.status === 403) {
        disconnect("Connection rejected. Enter the administrator token again.");
        throw stale;
      }
      if (!response.ok) throw new Error(messages[response.status] || "Saved evidence could not be read.");
      const value = binary ? await response.blob() : await response.json();
      if (!valid()) throw stale;
      return value;
    } catch (error) {
      if (!valid() || error === stale) throw stale;
      if (timedOut) throw new Error("Request timed out. Try again.");
      if (error instanceof Error && Object.values(messages).includes(error.message)) throw error;
      throw new Error("Saved evidence could not be read. Try again.");
    } finally { clearTimeout(timeout); pending.delete(job); }
  }
  function failure(error, valid) {
    if (error !== stale && valid()) notice(error instanceof Error ? error.message : "Saved evidence is invalid.");
  }
  const malformed = () => { throw new Error("Saved evidence is invalid."); };
  function cursorOK(v) { return v === null || obj(v) && uuid(v.lineage_id) && uuid(v.attempt_id); }
  function attemptOK(v) {
    return obj(v) && text(v.lineage_id) && text(v.attempt_id) &&
      ["available", "missing", "invalid"].includes(v.metadata_state) && typeof v.has_database === "boolean" &&
      ["mode", "scenario_key", "reserved_at", "reservation_error"].every(k => nullable(v[k], text)) &&
      (v.parent === null || Array.isArray(v.parent) && v.parent.length === 2 && uuid(v.parent[0]) && uint(v.parent[1]));
  }
  function requestOK(v) {
    return v === null || obj(v) && uint(v.format) && ["ollama", "llama_cpp"].includes(v.provider_kind) &&
      text(v.model) && nullable(v.model_digest, x => text(x) && x.trim().length > 0) && text(v.method) && text(v.url) &&
      obj(v.headers) && Object.values(v.headers).every(text) && digest(v.body_digest) &&
      uint(v.body_length) && v.body_length > 0 && text(v.prepared_at) && duration(v.timeout_seconds) && uint(v.max_response_bytes);
  }
  const timestampNames = ["dispatch_started_at", "worker_started_at", "http_started_at", "headers_received_at", "first_body_byte_at", "read_finished_at", "settled_at"];
  const durationNames = ["broker_seconds", "worker_seconds", "http_seconds", "headers_seconds", "first_byte_seconds", "body_read_seconds"];
  function responseOK(v) {
    return v === null || obj(v) && uint(v.format) && ["complete", "incomplete", "unavailable"].includes(v.body_state) &&
      (v.body_state === "unavailable" ? v.body_digest === null && v.body_length === null : digest(v.body_digest) && uint(v.body_length)) && nullable(v.http_status, uint) &&
      obj(v.timestamps) && timestampNames.every(k => nullable(v.timestamps[k], text)) &&
      obj(v.durations) && durationNames.every(k => nullable(v.durations[k], duration));
  }
  function callOK(v) {
    return obj(v) && text(v.request_id) && uint(v.sequence) && uint(v.base_revision) && uint(v.source_tick) && text(v.actor_label) &&
      nullable(v.response_kind, x => ["response_validated", "response_failed", "response_reused"].includes(x)) &&
      nullable(v.error_code, text) && nullable(v.outcome, text) && requestOK(v.request_trace) && responseOK(v.response_trace) &&
      nullable(v.content_digest, digest) && nullable(v.elapsed_seconds, duration) &&
      (v.source === null || obj(v.source) && uuid(v.source.attempt_id) && text(v.source.request_id) && boundaryOK(v.source.boundary));
  }
  function cell(row, value) { const td = document.createElement("td"); td.textContent = show(value); row.append(td); return td; }
  function buttonCell(row, label, action, enabled = true) {
    const td = document.createElement("td"), button = document.createElement("button");
    button.type = "button"; button.textContent = label; button.disabled = !enabled;
    button.addEventListener("click", action); td.append(button); row.append(td);
  }
  async function attempts(more = false) {
    if (!token) return;
    const session = generation, version = ++attemptsVersion;
    abort("attempts");
    const valid = () => session === generation && version === attemptsVersion && !!token;
    let query = "?limit=50";
    if (more) {
      if (attemptCursor === null) return;
      query += "&after_lineage_id=" + attemptCursor.lineage_id + "&after_attempt_id=" + attemptCursor.attempt_id;
    } else {
      attempt = null; $("call-panel").hidden = true; $("selected-attempt").textContent = "";
      clearCalls(); $("attempts").replaceChildren(); attemptCursor = null;
    }
    $("more-attempts").disabled = true;
    try {
      const page = await read("/analysis/attempts" + query, "attempts", valid);
      if (!valid()) return;
      if (!obj(page) || !Array.isArray(page.attempts) || !page.attempts.every(attemptOK) || !cursorOK(page.next_after) ||
          page.integrity !== "reservation_metadata_checked" || page.listing !== "current") malformed();
      for (const item of page.attempts) {
        const row = document.createElement("tr");
        buttonCell(row, item.attempt_id, () => selectAttempt(item.attempt_id), uuid(item.attempt_id) && uuid(item.lineage_id) && item.has_database);
        cell(row, item.lineage_id); cell(row, item.metadata_state); cell(row, show(item.mode) + " / " + show(item.scenario_key));
        cell(row, item.reserved_at); cell(row, item.has_database ? "available" : "unavailable");
        $("attempts").append(row);
      }
      attemptCursor = page.next_after; $("more-attempts").disabled = attemptCursor === null;
      $("attempt-status").textContent = "Current listing · " + page.integrity + ". Refresh restarts the listing.";
    } catch (error) { failure(error, valid); }
  }
  function selectAttempt(id) {
    if (!uuid(id) || !token) return;
    attempt = id; clearCalls(); $("call-panel").hidden = false;
    $("selected-attempt").textContent = id; calls();
  }
  const boundaryQuery = b => "through_sequence=" + b.sequence + "&journal_digest=" + b.digest;
  async function calls(more = false) {
    if (!attempt || !token) return;
    if (!more) clearCalls();
    const session = generation, version = ++callsVersion, id = attempt;
    abort("calls");
    const valid = () => session === generation && version === callsVersion && id === attempt && !!token;
    let query = "?limit=50";
    if (more) {
      if (callCursor === null || boundary === null) return;
      query += "&after_sequence=" + callCursor + "&" + boundaryQuery(boundary);
    }
    $("more-calls").disabled = true;
    try {
      const page = await read("/analysis/attempts/" + id + "/traces" + query, "calls", valid);
      if (!valid()) return;
      if (!obj(page) || !uint(page.archive_format) || !boundaryOK(page.boundary) || !Array.isArray(page.calls) || !page.calls.every(callOK) ||
          !nullable(page.next_after_sequence, uint) || page.integrity !== "trace_metadata_checked" ||
          (boundary !== null && (boundary.sequence !== page.boundary.sequence || boundary.digest !== page.boundary.digest))) malformed();
      if (boundary === null) boundary = page.boundary;
      $("boundary").textContent = "Integrity: " + page.integrity + "\nArchive format: " + page.archive_format +
        "\nBoundary sequence: " + boundary.sequence + "\nBoundary digest: " + boundary.digest;
      for (const call of page.calls) {
        const row = document.createElement("tr");
        buttonCell(row, call.request_id, () => selectCall(call));
        for (const v of [call.actor_label, call.source_tick, call.response_kind ?? "pending", call.outcome ?? call.error_code,
          call.elapsed_seconds, call.request_trace?.provider_kind, call.request_trace?.model]) cell(row, v);
        $("calls").append(row);
      }
      callCursor = page.next_after_sequence; $("more-calls").disabled = callCursor === null;
    } catch (error) { failure(error, valid); }
  }
  function selectCall(call) {
    clearCall(); selected = call; $("detail-panel").hidden = false;
    const lines = [];
    const line = (key, value) => lines.push(key + ": " + show(value));
    for (const key of ["request_id", "sequence", "base_revision", "source_tick", "actor_label", "response_kind", "outcome", "error_code", "elapsed_seconds", "content_digest"]) line(key, call[key]);
    if (call.response_kind === null) lines.push("Response: pending");
    if (call.response_kind === "response_reused") lines.push("Original reused evidence/timing; not a new latency measurement.");
    line("Saved source mapping", call.source);
    for (const side of ["request", "response"]) {
      const trace = call[side + "_trace"];
      lines.push("\n" + side + " trace:");
      if (trace === null) lines.push("legacy/unavailable");
      else {
        if (side === "response") lines.push(trace.body_state === "incomplete" ? "incomplete captured prefix" : trace.body_state === "complete" ? "complete saved body" : "body unavailable");
        for (const [key, value] of Object.entries(trace)) {
          if ((key === "timestamps" || key === "durations") && obj(value)) {
            for (const [name, item] of Object.entries(value)) line(name, item);
          } else line(key, value);
        }
      }
      for (const op of ["preview", "download"]) $(op + "-" + side).disabled = !digest(trace?.body_digest);
    }
    $("details").textContent = lines.join("\n");
  }
  async function body(side, download) {
    const sha = selected?.[side + "_trace"]?.body_digest;
    if (!digest(sha) || !attempt || !boundary || !token) return;
    clearBody();
    const session = generation, version = bodyVersion, call = selected, id = attempt, prefix = boundary;
    const valid = () => generation === session && bodyVersion === version && selected === call && attempt === id && boundary === prefix && !!token;
    const path = "/analysis/attempts/" + id + "/bodies/" + sha + (download ? "" : "/preview") + "?" + boundaryQuery(prefix);
    try {
      const value = await read(path, "body", valid, download);
      if (!valid()) return;
      if (download) {
        const url = URL.createObjectURL(value); urls.add(url);
        const anchor = document.createElement("a"); anchor.href = url; anchor.download = "inference-" + sha + ".bin";
        document.body.append(anchor); anchor.click(); anchor.remove(); notice("Download dispatched.");
        setTimeout(() => { if (urls.delete(url)) URL.revokeObjectURL(url); }, 0);
      } else {
        if (!obj(value) || value.sha256 !== sha || !uint(value.byte_length) || !uint(value.preview_byte_length) || value.preview_byte_length > 65536 ||
            value.preview_byte_length > value.byte_length || !text(value.text) || typeof value.truncated !== "boolean" || typeof value.replacement_used !== "boolean" ||
            value.preview_kind !== "utf8_text" || value.integrity !== "selected_body_verified") malformed();
        $("preview").textContent = value.text;
        $("preview-meta").textContent = "UTF-8 preview · " + side + " · byte_length: " + value.byte_length +
          " · preview_byte_length: " + value.preview_byte_length + " · truncated: " + value.truncated +
          " · replacement_used: " + value.replacement_used + " · integrity: " + value.integrity;
      }
    } catch (error) { failure(error, valid); }
  }
  $("login").addEventListener("submit", async event => {
    event.preventDefault();
    const submitted = $("token").value;
    disconnect(""); token = submitted; $("token").value = "";
    const session = generation, valid = () => session === generation && !!token;
    notice("Connecting…");
    try {
      const status = await read("/analysis/status", "login", valid);
      if (!valid()) return;
      if (!obj(status) || status.access !== "read_only" || !["live", "offline"].includes(status.mode)) malformed();
      $("login").hidden = true; $("disconnect").hidden = false; $("session").hidden = false;
      $("mode").textContent = status.mode + " · read-only · saved evidence only";
      notice("Connected."); attempts();
    } catch (error) { if (error !== stale && valid()) disconnect("Connection failed. Check the token and try again."); }
  });
  $("disconnect").addEventListener("click", () => disconnect());
  $("refresh-attempts").addEventListener("click", () => attempts());
  $("more-attempts").addEventListener("click", () => attempts(true));
  $("refresh-calls").addEventListener("click", () => calls());
  $("more-calls").addEventListener("click", () => calls(true));
  for (const side of ["request", "response"]) {
    $("preview-" + side).addEventListener("click", () => body(side, false));
    $("download-" + side).addEventListener("click", () => body(side, true));
  }
  window.addEventListener("pagehide", () => disconnect());
})();
