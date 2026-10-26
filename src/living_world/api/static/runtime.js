/* Session credentials and command envelopes deliberately remain in this closure. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const obj = v => v !== null && typeof v === "object" && !Array.isArray(v) && Object.getPrototypeOf(v) === Object.prototype;
  const str = v => typeof v === "string", ns = v => v === null || str(v);
  const num = v => Number.isSafeInteger(v) && v >= 0, nn = v => v === null || num(v);
  const id = v => str(v) && /^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$/.test(v);
  const secret = v => str(v) && /^[A-Za-z0-9_-]{43}$/.test(v);
  const fields = (v, shape) => obj(v) && Object.entries(shape).every(([k, f]) => Object.hasOwn(v,k) && f(v[k]));
  const exact = (v, shape) => fields(v,shape) && Object.keys(v).length === Object.keys(shape).length;
  const json = v => v === null || str(v) || typeof v === "boolean" || (typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= Number.MAX_SAFE_INTEGER) || (Array.isArray(v) && v.every(json)) || (obj(v) && Object.values(v).every(json));
  const parent = v => v === null || exact(v,{attempt_id:id,revision:num});
  const summary = v => exact(v,{attempt_id:id,lineage_id:id,mode:ns,scenario:ns,parent,started_at:ns,ended_at:ns,lifecycle:str,last_revision:nn,tick:nn,error_code:ns}) && ((v.last_revision === null) === (v.tick === null));
  const detail = v => exact(v,{attempt:summary,configuration:v => obj(v) && json(v),configuration_source:s => ["archive","requested","reservation"].includes(s),outcome:ns,journal_total:num,recent_journal:v => Array.isArray(v) && v.length <= 50 && v.every(e => exact(e,{kind:str,payload:json}))}) && v.journal_total >= v.recent_journal.length;
  const allowed = {initializing:["pause","stop"],paused:["resume","step","stop"],running:["pause","stop"],awaiting_model:["pause","stop"],stepping:["pause"],provider_error_paused:["retry","stop"],pause_requested:[],completed:[],stopped:[],failed:[],interrupted:[]};
  const live = v => exact(v,{attempt_id:id,lineage_id:id,state:s => str(s) && Object.hasOwn(allowed,s),state_version:num,revision:nn,tick:nn,activity:ns,error_code:ns,mode:ns,scenario:ns,model:m => m === null || exact(m,{name:ns,digest:ns}),configuration_error:ns,inspection_prefix:ns}) && ((v.revision === null) === (v.tick === null)) && v.inspection_prefix === (v.revision === null ? null : `/live/checkpoints/${v.revision}`);
  const statusDTO = v => exact(v,{live:v => v === null || live(v)});
  const receipt = (v, command) => exact(v,{command_id:x => x === command.command_id,status:x => ["queued","applied","rejected"].includes(x),state_version:num,revision:num,reason:ns});
  let generation = 0, selection = 0, archiveGeneration = 0, token = null, nonce = null, connected = false, fresh = false, latest = null, lastRefresh = null, timer = null, source = "live", selectedAttempt = null;
  const requests = new Set(), pending = new Map(), cache = new Map();
  const detailJobs = new Map(), detailQueue = [];
  let activeDetails = 0;
  let frame = null, frameAttempt = null, framePrefix = null, frameReady = false, frameEpoch = 0, loadingFrame = null;
  const text = (key,value) => { $(key).textContent = value; };
  const pretty = v => JSON.stringify(v,null,2);
  const time = () => new Date().toLocaleTimeString();
  function clearFrame() {
    frameEpoch++; loadingFrame = null;
    if (frame) { frame.contentWindow?.postMessage({type:"living-world-inspector-clear"},window.origin); frame.remove(); }
    frame = null; frameAttempt = null; framePrefix = null; frameReady = false;
  }
  function clearSession(message = "Disconnected. The simulation may still be running.") {
    generation++; selection++; archiveGeneration++; connected = false; fresh = false; token = null; nonce = null; latest = null; lastRefresh = null;
    clearTimeout(timer); requests.forEach(c => c.abort()); requests.clear(); pending.clear(); cache.clear(); clearFrame();
    cancelQueuedDetails();
    source = "live"; selectedAttempt = null;
    for (const k of ["live","freshness","receipts","archives","archive-status","details","configuration","journal","source"]) $(k).replaceChildren();
    $("checkpoint").replaceChildren(new Option("Choose a checkpoint", ""));
    $("session").hidden = true; $("details-panel").hidden = true; $("disconnect").hidden = true; $("login").hidden = false; $("token").value = ""; renderControls(); text("notice",message);
  }
  async function request(path, options = {}, g = generation) {
    const controller = new AbortController(); requests.add(controller);
    try {
      const response = await fetch(path,{...options,cache:"no-store",signal:controller.signal,headers:{Authorization:`Bearer ${token}`,...options.headers}});
      if (g !== generation || !connected) throw new Error("obsolete");
      if ([401,403].includes(response.status)) { clearSession("Connection rejected. Enter a valid administrator token."); throw new Error("obsolete"); }
      const body = options.html ? await response.text() : await response.json();
      if (g !== generation || !connected) throw new Error("obsolete");
      return {response,body};
    } finally { requests.delete(controller); }
  }
  window.addEventListener("message",event => {
    if (!connected || !frame || frameReady || event.origin !== window.origin || event.source !== frame.contentWindow || !exact(event.data,{type:t => t === "living-world-inspector-ready"})) return;
    frameReady = true;
    frame.contentWindow.postMessage({type:"living-world-inspector-connect",token},window.origin);
    frame.contentWindow.postMessage({type:"living-world-inspector-pin",prefix:framePrefix},window.origin);
  });
  async function showFrame(prefix, attempt, epoch = selection) {
    const g = generation;
    if (frame && frameAttempt === attempt && source === "live") {
      if (framePrefix !== prefix) { framePrefix = prefix; if(frameReady) frame.contentWindow.postMessage({type:"living-world-inspector-pin",prefix},window.origin); }
      return;
    }
    const key = `${attempt}:${prefix}`;
    if(loadingFrame === key) return;
    clearFrame(); const ticket = frameEpoch; loadingFrame = key;
    try {
      const {response,body} = await request(prefix + "/inspector",{html:true},g);
      if (g !== generation || epoch !== selection || ticket !== frameEpoch) return;
      loadingFrame = null;
      if (!response.ok) throw new Error("unavailable");
      const next = document.createElement("iframe"); next.title = "World Inspector";
      frame = next; frameAttempt = attempt; framePrefix = prefix; frameReady = false;
      $("preview").replaceChildren(next); next.srcdoc = body;
    } catch { if(g === generation && epoch === selection && ticket === frameEpoch && connected) { loadingFrame = null; text("source","World preview unavailable."); } }
  }
  const commandButtons = new Map();
  function renderControls() {
    $("controls").hidden = source !== "live";
    for(const action of ["pause","resume","step","stop","retry"]) {
      let button = commandButtons.get(action);
      if(!button) {
        button = document.createElement("button"); button.textContent = action === "retry" ? "Retry model" : action[0].toUpperCase()+action.slice(1);
        button.addEventListener("click",() => command(action)); $("controls").append(button); commandButtons.set(action,button);
      }
      button.disabled = !connected || !fresh || source !== "live" || !latest || !allowed[latest.state].includes(action) || pending.has(action);
    }
  }
  function renderReceipts() {
    for(const row of [...$("receipts").children]) if(![...pending.values()].some(item => item.row === row)) row.remove();
    for(const item of pending.values()) {
      if(!item.row) {
        item.row = document.createElement("div"); item.label = document.createElement("p"); item.retry = document.createElement("button"); item.retry.textContent = "Retry delivery"; item.retry.addEventListener("click",() => deliver(item)); item.row.append(item.label,item.retry); $("receipts").append(item.row);
      }
      item.label.textContent = `${item.envelope.action}: ${item.message}`;
      item.retry.hidden = !item.uncertain; item.retry.disabled = item.sending || !fresh || source !== "live";
    }
  }
  function acceptReceipt(item,value) {
    if(pending.get(item.envelope.action) !== item) return;
    item.message = `${item.envelope.action === "pause" && value.status === "queued" ? "Pause requested; " : ""}${value.status}; revision ${value.revision ?? "none"}; ${value.reason ?? "No reason recorded"}`;
    item.uncertain = false;
    if(value.status !== "queued") { pending.delete(item.envelope.action); text("notice",`${item.envelope.action}: ${item.message}`); }
  }
  function markUncertain(item) {
    if(pending.get(item.envelope.action) !== item) return;
    item.uncertain = true; item.message = "Delivery uncertain. Receipt unknown; Retry delivery keeps the same command.";
  }
  async function deliver(item) {
    if(item.sending || !connected) return;
    const g = generation; item.sending = true; renderReceipts();
    try {
      const {response,body} = await request("/runtime/commands",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":nonce},body:JSON.stringify(item.envelope)},g);
      if(g !== generation || pending.get(item.envelope.action) !== item) return;
      if(receipt(body,item.envelope) && [200,202,409].includes(response.status)) acceptReceipt(item,body);
      else if ((response.status === 409 && exact(body,{detail:v => ["command_conflict","runtime_unavailable","archive_invalid"].includes(v)})) || (response.status === 422 && exact(body,{detail:v => v === "invalid_command"}))) {
        pending.delete(item.envelope.action); text("notice",`Command admission failed: ${body.detail}.`);
      } else throw new Error("uncertain");
    } catch { if(g === generation && connected) markUncertain(item); }
    finally { if(g === generation && connected) { item.sending = false; renderControls(); renderReceipts(); } }
  }
  function command(action) {
    if(!fresh || !latest || source !== "live" || pending.has(action) || !allowed[latest.state].includes(action)) return;
    const item = {envelope:Object.freeze({command_id:crypto.randomUUID(),action,expected_state_version:latest.state_version}),sending:false,uncertain:false,message:action === "pause" ? "Pause requested; awaiting durable receipt." : "Awaiting durable receipt."};
    pending.set(action,item); renderControls(); renderReceipts(); deliver(item);
  }
  async function poll() {
    const g = generation;
    try {
      const {response,body} = await request("/runtime/status",{},g);
      const nextNonce = response.headers.get("X-CSRF-Token");
      if(!response.ok) throw new Error("unavailable");
      if(!secret(nextNonce)) { clearSession("Connection rejected. Enter a valid administrator token."); return; }
      if(!statusDTO(body)) throw new Error("malformed");
      nonce = nextNonce; latest = body.live; fresh = true; lastRefresh = time();
      text("live",latest ? `Attempt: ${latest.attempt_id}\nLineage: ${latest.lineage_id}\nMode: ${latest.mode ?? "Unknown"}\nScenario: ${latest.scenario ?? "Unknown"}\nModel: ${latest.model?.name ?? "None"}\nModel digest: ${latest.model?.digest ?? "None"}\nState: ${latest.state}\nOperational version: ${latest.state_version}\nLast committed tick: ${latest.tick ?? "None"}\nLast committed revision: ${latest.revision ?? "None"}\nActivity: ${latest.activity ?? "None"}\nError: ${latest.error_code ?? "None"}\nConfiguration error: ${latest.configuration_error ?? "None"}` : "No live attempt yet. Saved attempts remain available.");
      text("freshness",`Last refresh: ${lastRefresh}. World preview shows the last committed checkpoint.`);
      if(source === "live") {
        if(latest?.inspection_prefix) { text("source",`Live attempt ${latest.attempt_id}; mode ${latest.mode}; checkpoint ${latest.revision}; tick ${latest.tick}.`); showFrame(latest.inspection_prefix,latest.attempt_id); }
        else { clearFrame(); text("source","No committed checkpoint."); }
      }
      for(const item of [...pending.values()]) {
        try {
          const result = await request(`/runtime/commands/${encodeURIComponent(item.envelope.command_id)}`,{},g);
          if(result.response.status === 404) continue;
          if(!result.response.ok || !receipt(result.body,item.envelope)) throw new Error("malformed");
          acceptReceipt(item,result.body);
        } catch { if(g !== generation) return; markUncertain(item); }
      }
    } catch { if(g === generation && connected) { fresh = false; text("freshness",`Last refresh: ${lastRefresh ?? "Never"}. Last data is stale. Controls are unavailable until status refresh succeeds.`); } }
    finally { if(g === generation && connected) { renderControls(); renderReceipts(); timer = setTimeout(poll,1000); } }
  }
  function cancelQueuedDetails() {
    for(const job of detailQueue.splice(0)) {
      detailJobs.delete(job.key); job.reject(new Error("obsolete"));
    }
  }
  function pumpDetails() {
    while(activeDetails < 2 && detailQueue.length) {
      const job = detailQueue.shift();
      if(!connected || job.g !== generation || job.ag !== archiveGeneration) {
        detailJobs.delete(job.key); job.reject(new Error("obsolete")); continue;
      }
      activeDetails++;
      // Slots belong to actual requests until their finally, across refresh/logout.
      (async () => {
        try {
          const result = await request(`/archives/${job.attempt}`,{},job.g);
          if(job.g !== generation || job.ag !== archiveGeneration) throw new Error("obsolete");
          if(!result.response.ok || !detail(result.body) || result.body.attempt.attempt_id !== job.attempt) throw new Error("unavailable");
          cache.set(job.attempt,result.body); job.resolve(result.body);
        } catch(error) { job.reject(error); }
        finally {
          activeDetails--; detailJobs.delete(job.key); pumpDetails();
        }
      })();
    }
  }
  function loadDetail(attempt,g,ag) {
    if(!connected || g !== generation || ag !== archiveGeneration) return Promise.reject(new Error("obsolete"));
    if(cache.has(attempt)) return Promise.resolve(cache.get(attempt));
    const key = `${g}:${ag}:${attempt}`;
    if(detailJobs.has(key)) return detailJobs.get(key).promise;
    const job = {key,attempt,g,ag};
    job.promise = new Promise((resolve,reject) => { job.resolve = resolve; job.reject = reject; });
    detailJobs.set(key,job); detailQueue.push(job); pumpDetails(); return job.promise;
  }
  async function archives() {
    const g = generation, ag = ++archiveGeneration; cache.clear(); cancelQueuedDetails(); text("archive-status","Loading saved attempts…"); $("archives").replaceChildren();
    try {
      const {response,body} = await request("/archives",{},g);
      if(ag !== archiveGeneration) return;
      if(!response.ok || !exact(body,{attempts:v => Array.isArray(v) && v.every(summary)})) throw new Error("malformed");
      const jobs = body.attempts.map(attempt => {
        const row = document.createElement("tr"), cell = document.createElement("td"), button = document.createElement("button"); button.textContent = attempt.attempt_id; button.addEventListener("click",() => selectArchive(attempt.attempt_id)); cell.append(button); row.append(cell);
        for(const value of [`${attempt.mode ?? "Unknown"} / ${attempt.scenario ?? "Unknown"}`,attempt.started_at ?? "Unknown",attempt.parent ? `${attempt.parent.attempt_id}; checkpoint ${attempt.parent.revision}` : "None",attempt.tick === null ? "No checkpoint" : `Tick ${attempt.tick}`,attempt.lifecycle,"Loading…"]) { const td = document.createElement("td"); td.textContent = value; row.append(td); } $("archives").append(row);
        return {attempt,cell:row.lastChild};
      });
      text("archive-status",`Archives refreshed: ${time()}. ${jobs.length} saved attempts.`);
      await Promise.all(jobs.map(async job => {
        try { const data = await loadDetail(job.attempt.attempt_id,g,ag); if(g === generation && ag === archiveGeneration) job.cell.textContent = data.outcome === null ? "No outcome recorded" : pretty(data.outcome); }
        catch { if(g === generation && ag === archiveGeneration) job.cell.textContent = "Unavailable"; }
      }));
    } catch { if(g === generation && ag === archiveGeneration && connected) text("archive-status","Saved attempts unavailable. Try Refresh archives."); }
  }
  async function selectArchive(attempt) {
    source = "history"; selectedAttempt = attempt; const epoch = ++selection, g = generation, ag = archiveGeneration;
    clearFrame(); renderControls(); renderReceipts(); $("details-panel").hidden = false;
    for(const key of ["details","configuration","journal"]) text(key,"Loading…");
    $("checkpoint").replaceChildren(new Option("Choose a checkpoint", "")); text("source",`Historical, read-only attempt ${attempt}.`);
    try {
      const data = await loadDetail(attempt,g,ag);
      if(g !== generation || epoch !== selection || ag !== archiveGeneration) return;
      const checkpoints = await request(`/archives/${attempt}/checkpoints`,{},g);
      if(g !== generation || epoch !== selection || ag !== archiveGeneration) return;
      if(!checkpoints.response.ok || !exact(checkpoints.body,{checkpoints:v => Array.isArray(v) && v.every(c => exact(c,{revision:num,tick:num}))})) throw new Error("malformed");
      text("details",pretty({...data.attempt,outcome:data.outcome,configuration_source:data.configuration_source})); text("configuration",pretty(data.configuration)); text("journal",`Latest ${data.recent_journal.length} entries; total ${data.journal_total}\n${pretty(data.recent_journal)}`);
      for(const c of checkpoints.body.checkpoints) $("checkpoint").append(new Option(`Checkpoint ${c.revision}; tick ${c.tick}`,String(c.revision)));
      if(!checkpoints.body.checkpoints.length) text("source",`Historical, read-only attempt ${attempt}. No committed checkpoint.`);
      $("checkpoint").focus();
    } catch { if(g === generation && epoch === selection && ag === archiveGeneration && connected) { text("details","Saved attempt details unavailable."); text("configuration",""); text("journal",""); } }
  }
  function historyLabel(revision) {
    const a = cache.get(selectedAttempt)?.attempt;
    return `Historical, read-only attempt ${selectedAttempt}; mode ${a?.mode ?? "Unknown"}; started ${a?.started_at ?? "Unknown"}; ended ${a?.ended_at ?? "None"}; parent ${a?.parent ? `${a.parent.attempt_id} checkpoint ${a.parent.revision}` : "None"}; checkpoint ${revision}.`;
  }
  $("checkpoint").addEventListener("change",() => { const revision = $("checkpoint").value; if(source !== "history" || !id(selectedAttempt) || !/^(0|[1-9][0-9]*)$/.test(revision) || !num(Number(revision))) return; const epoch = ++selection; clearFrame(); text("source",historyLabel(revision)); showFrame(`/archives/${selectedAttempt}/checkpoints/${revision}`,selectedAttempt,epoch); });
  $("return-live").addEventListener("click",() => { source = "live"; selectedAttempt = null; selection++; clearFrame(); $("details-panel").hidden = true; renderControls(); renderReceipts(); if(latest?.inspection_prefix) showFrame(latest.inspection_prefix,latest.attempt_id); text("source",latest ? `Live attempt ${latest.attempt_id}; checkpoint ${latest.revision ?? "none"}.` : "No committed checkpoint."); });
  $("refresh-archives").addEventListener("click",archives);
  $("disconnect").addEventListener("click",() => { clearSession(); $("token").focus(); });
  window.addEventListener("pagehide",() => clearSession());
  $("login").addEventListener("submit",async event => {
    event.preventDefault(); const input = $("token").value; $("token").value = ""; clearSession("Connecting…");
    if(!secret(input)) { text("notice","Connection rejected. Enter a valid administrator token."); $("token").focus(); return; }
    token = input; connected = true; const g = generation; await poll();
    if(g !== generation || !connected) return;
    if(!fresh) { clearSession("Connection rejected. Enter a valid administrator token."); $("token").focus(); return; }
    $("login").hidden = true; $("disconnect").hidden = false; $("session").hidden = false; text("notice","Connected."); $("disconnect").focus(); archives();
  });
})();
