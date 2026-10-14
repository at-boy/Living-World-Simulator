"use strict";
(() => {
  const routes = Object.freeze({world: "/world", run: "/world/run", replay: "/world/replay", entities: "/world/entities", entity: "/world/entities/", relationships: "/world/relationships", resources: "/world/resources", needs: "/world/needs", consequences: "/world/consequences", goals: "/world/goals", work: "/world/work-orders", external: "/world/external-references", dispatches: "/world/external-dispatches", stages: "/world/settlement-stages", events: "/world/events"});
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const str = value => typeof value === "string";
  const integer = value => Number.isSafeInteger(value);
  const number = value => typeof value === "number" && Number.isFinite(value);
  const boolean = value => typeof value === "boolean";
  const nullableInteger = value => value === null || integer(value);
  const nullableString = value => value === null || str(value);
  const fields = (value, shape) => object(value) && Object.entries(shape).every(([key, check]) => check(value[key]));
  const list = check => value => Array.isArray(value) && value.every(check);
  const safe = value => {
    if (typeof value === "number") return Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER && (!Number.isInteger(value) || integer(value));
    if (Array.isArray(value)) return value.every(safe);
    if (object(value)) return Object.values(value).every(safe);
    return value === null || ["string", "boolean"].includes(typeof value);
  };
  const lifecycle = {created_tick: integer, destroyed_tick: nullableInteger};
  const entityShape = value => fields(value, {id: str, definition_key: str, name: str, attributes: object, ...lifecycle});
  const evidence = list(value => fields(value, {tick: integer, description: str, source_event_ids: list(str)}));
  const criterion = value => {
    if (!object(value)) return false;
    // Known variant fields select their full shape; invalid fields cannot fall
    // through to population or the less specific constructed-capability shape.
    const variants = [
      {keys: ["resource"], shape: {resource: str, minimum: integer}},
      {keys: ["capability", "count", "minimum_condition"], shape:
        Object.hasOwn(value, "minimum_condition")
          ? {capability: str, count: integer, minimum_condition: integer}
          : {capability: str, count: integer}},
      {keys: ["capacity"], shape: {capacity: str, minimum: integer}},
      {keys: ["role", "state"], shape: {role: str, state: str}},
      {keys: ["need", "maximum", "duration_ticks"], shape:
        {need: str, maximum: number, duration_ticks: integer}},
      {keys: ["stage"], shape: {stage: str}}
    ];
    const selected = variants.filter(variant =>
      variant.keys.some(key => Object.hasOwn(value, key)));
    if (!selected.length) return fields(value, {minimum: integer});
    return selected.every(variant => fields(value, variant.shape)) &&
      (!Object.hasOwn(value, "minimum") || integer(value.minimum));
  };
  const objective = value => fields(value, {definition: d => fields(d, {id: str, label: str, dependencies: list(str), completion_criteria: list(criterion), failure_criteria: list(criterion)}), state: s => fields(s, {objective_id: str, status: str, evidence})});
  const pair = (definitionShape, stateShape) => value => fields(value, {definition: d => fields(d, definitionShape), state: s => fields(s, stateShape)});
  const assessment = value => fields(value, {tick: integer, level: str, available: nullableInteger, required: nullableInteger, balance: nullableInteger, pressure: v => v === null || typeof v === "number"});
  const workTarget = value => object(value) && ({
    resource: v => fields(v, {resource: str, quantity: integer}),
    capability: v => fields(v, {definition_key: str, count: integer}),
    maintenance: v => fields(v, {policy_id: str}),
    external_connection: v => fields(v, {reference_id: str})
  }[value.kind]?.(value) === true);
  const toolRequirements = list(value => fields(value, {tool: str, quantity: integer}));
  const resourceRequirements = list(value => fields(value, {resource: str, quantity: integer}));
  const policies = {
    consumption: list(v => fields(v, {policy: p => fields(p, {id: str, owner_id: str, food_per_person_per_tick: integer, water_per_person_per_tick: integer}), state: s => fields(s, {policy_id: str, last_processed_tick: nullableInteger, food_shortage: boolean, water_shortage: boolean})})),
    storage: list(v => fields(v, {policy: p => fields(p, {id: str, owner_id: str, resources: list(r => fields(r, {resource: str, spoilage_per_tick: integer}))}), state: s => fields(s, {policy_id: str, last_processed_tick: nullableInteger, overflowing: boolean, spoiling: boolean})})),
    maintenance: list(v => fields(v, {policy: p => fields(p, {id: str, owner_id: str, capability_id: str, label: str, upkeep: list(r => fields(r, {resource: str, amount: integer})), initial_condition: integer, maximum_condition: integer, deterioration_per_unpaid_tick: integer, recovery_per_paid_tick: integer}), state: s => fields(s, {policy_id: str, last_processed_tick: nullableInteger, condition: integer, upkeep_shortage: boolean})}))
  };
  const validators = {
    world: value => fields(value, {tick: integer, entity_count: integer, event_count: integer, replay_configured: v => typeof v === "boolean"}) && Object.entries(value).every(([key, v]) => !key.endsWith("_count") || integer(v)),
    run: value => fields(value, {scenario_key: str, schema_version: integer, seed: integer, configuration_fingerprint: str}),
    replay: value => object(value) && (Object.keys(value).length === 0 || fields(value, {binding: b => fields(b, {scenario_key: str, scenario_fingerprint: str, tape_fingerprint: str, actor_sequence: list(str), configured_tick: integer}), state: s => fields(s, {next_index: integer, last_attempt_tick: nullableInteger}), entity_bindings: v => object(v) && Object.values(v).every(str)})),
    entity: entityShape, entities: list(entityShape),
    relationships: list(v => fields(v, {id: str, kind: str, source_id: str, target_id: str, attributes: object, ...lifecycle})),
    resources: list(v => fields(v, {key: str})),
    needs: list(pair({id: str, owner_id: str, kind: str, requirement_per_person: integer, assessment_window_ticks: integer, secure_maximum: number, strained_maximum: number}, {need_id: str, current: v => v === null || assessment(v), history: list(assessment)})),
    consequences: value => fields(value, policies),
    goals: list(v => pair({id: str, owner_id: str, label: str, objective_ids: list(str), completion_criteria: list(criterion), failure_criteria: list(criterion)}, {goal_id: str, status: str, evidence})(v) && list(objective)(v.objectives)),
    work: list(v => pair({id: str, category: str, public_label: str, target: workTarget, settlement_id: str, objective_id: str, location_id: str, labor_required: integer, tools: toolRequirements, resources: resourceRequirements, priority: integer, created_tick: integer, prerequisite_work_ids: list(str), deadline_tick: nullableInteger, required_progress: integer}, {work_id: str, status: str, progress: integer, status_reason: nullableString, reservation_id: nullableString, started_tick: nullableInteger, inputs_charged_tick: nullableInteger, resolution_tick: nullableInteger})(v) && list(r => fields(r, {id: str, work_id: str, labor_entity_ids: list(str), tools: toolRequirements, resources: resourceRequirements, created_tick: integer, released_tick: nullableInteger}))(v.reservations)),
    external: list(v => fields(v, {id: str, name: str, role: str, allowed_imports: list(str), allowed_exports: list(str), capacity: integer, delay_ticks: integer, cost_per_unit: integer, reliability: v => typeof v === "number", contact_state: str, created_tick: integer})),
    dispatches: list(v => fields(v, {id: str, source_entity_id: str, reference_id: str, direction: str, good: str, quantity: integer, reserved_good: integer, reserved_cost: integer, status: str, created_tick: integer, departure_tick: nullableInteger, resolution_tick: nullableInteger})),
    stages: list(v => fields(v, {program: p => fields(p, {settlement_id: str, stages: list(s => fields(s, {stage: str, requirements: list(r => fields(r, {kind: str, objective_id: str}))}))}), state: s => fields(s, {settlement_id: str, current_stage: str, entered_tick: integer, last_transition_tick: nullableInteger})})),
    events: list(v => fields(v, {id: str, tick: integer, kind: str, subject_id: nullableString, attributes: object}))
  };
  const prose = {missing: "Snapshot not found.", unavailable: "Snapshot unavailable. Try Refresh.", malformed: "Malformed or unsupported snapshot."};
  async function fetchSnapshot(key, entityId = null) {
    if (!Object.hasOwn(routes, key) || (key === "entity" && !str(entityId))) throw new Error("malformed");
    let response;
    try { response = await fetch(routes[key] + (key === "entity" ? encodeURIComponent(entityId) : ""), {method: "GET", credentials: "same-origin", redirect: "error"}); }
    catch { throw new Error("unavailable"); }
    if (response.status === 404) throw new Error("missing");
    if (!response.ok) throw new Error("unavailable");
    let value;
    try { value = await response.json(); } catch { throw new Error("malformed"); }
    if (!safe(value) || !validators[key](value)) throw new Error("malformed");
    return value;
  }
  const content = document.querySelector("#content");
  const records = document.querySelector("#records");
  const title = document.querySelector("#view-title");
  const status = document.querySelector("#status");
  let generation = 0;
  let current = {view: "Overview", entityId: null, eventId: null};
  let names = new Map();
  const node = (tag, text = "") => { const element = document.createElement(tag); element.textContent = text; return element; };
  function button(label, action) { const result = node("button", label); result.type = "button"; result.addEventListener("click", action); return result; }
  const idOf = value => value.id ?? value.key ?? value.definition?.id ?? value.program?.settlement_id ?? value.policy?.id ?? "";
  const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  const ordered = values => [...values].sort((a, b) => compare(idOf(a), idOf(b)));
  function renderValue(value, key = "") {
    if (Array.isArray(value)) {
      const result = node("ul"); result.className = "values";
      const values = value.every(object) && value.every(v => idOf(v)) ? ordered(value) : value;
      for (const item of values) { const li = node("li"); li.append(renderValue(item, key)); result.append(li); }
      if (!value.length) result.append(node("li", "[]"));
      return result;
    }
    if (object(value)) {
      const wrapper = node("div"); wrapper.className = "table-scroll";
      const table = node("table"); const tbody = node("tbody");
      for (const field of Object.keys(value).sort(compare)) { const row = node("tr"); const heading = node("th", field); heading.scope = "row"; const cell = node("td"); cell.append(renderValue(value[field], field)); row.append(heading, cell); tbody.append(row); }
      table.append(tbody); wrapper.append(table); return wrapper;
    }
    if (str(value) && (key === "source_event_ids" || key === "source_event_id")) return button(`View event ${value}`, () => show("History", null, value));
    const text = value === null ? "null" : String(value);
    return node("span", names.has(value) && key.endsWith("_id") ? `${text} (${names.get(value)})` : text);
  }
  function renderRecords(label, values, entityButtons = false, eventId = null) {
    records.append(node("h3", label));
    if (!values.length) { records.append(node("p", "No records reported.")); return; }
    for (const value of ordered(values)) {
      const article = node("article");
      article.append(node("h4", String(idOf(value))));
      if (entityButtons) article.append(button(value.name, () => openEntityDetail(value.id)));
      if (label === "Events") { article.dataset.eventId = value.id; if (eventId === value.id) article.classList.add("selected"); }
      article.append(renderValue(value)); records.append(article);
    }
  }
  // Task15c extension: add a registry entry with sources and render(snapshotMap).
  const views = {
    Overview: {sources: ["world", "run", "replay"], render: data => { for (const key of ["world", "run", "replay"]) { records.append(node("h3", key)); records.append(data[key] === null ? node("p", "Run unbound.") : renderValue(data[key])); } }},
    Entities: {sources: ["entities"], render: data => renderRecords("Entities", data.entities, true)},
    Relationships: {sources: ["relationships", "entities"], render: data => renderRecords("Relationships", data.relationships)},
    Resources: {sources: ["resources", "entities"], render: data => { renderRecords("Resource definitions", data.resources); const quantities = data.entities.filter(e => Object.hasOwn(e.attributes, "resources")).map(e => ({id: e.id, name: e.name, resources: e.attributes.resources})); if (quantities.some(e => !object(e.resources) || !Object.values(e.resources).every(integer))) throw new Error("malformed"); renderRecords("Reported entity quantities", quantities); }},
    Needs: {sources: ["needs", "consequences"], render: data => { renderRecords("Needs", data.needs); for (const key of ["consumption", "maintenance", "storage"]) renderRecords(key, data.consequences[key]); }},
    Goals: {sources: ["goals"], render: data => renderRecords("Goals", data.goals)},
    Work: {sources: ["work"], render: data => renderRecords("Work orders", data.work)},
    "External connections": {sources: ["external", "dispatches"], render: data => { renderRecords("References", data.external); renderRecords("Dispatches", data.dispatches); }},
    Stages: {sources: ["stages"], render: data => renderRecords("Stages", data.stages)},
    History: {sources: ["events"], render: data => renderHistory(data.events)}
  };
  function renderHistory(events) {
    const label = node("label", "Filter history"); label.htmlFor = "history-filter";
    const input = node("input"); input.id = "history-filter"; input.type = "search";
    const container = node("div"); records.append(label, input, container);
    const draw = () => {
      container.replaceChildren();
      const selected = events.filter(e => (!current.eventId || e.id === current.eventId) && JSON.stringify(e).toLowerCase().includes(input.value.toLowerCase())).sort((a, b) => a.tick - b.tick || compare(a.id, b.id));
      if (!selected.length) container.append(node("p", events.length ? "No records match this filter." : "No records reported."));
      for (const event of selected) { const article = node("article"); article.dataset.eventId = event.id; article.append(node("h3", `${event.tick} · ${event.id}`), renderValue(event)); if (event.id === current.eventId) article.classList.add("selected"); container.append(article); }
    };
    if (current.eventId) records.append(button("Show all history", () => show("History")));
    input.addEventListener("input", draw); draw();
  }
  // Task15c entity-detail extension entry point. Only exact fetched references.
  function openEntityDetail(entityId) { return show("Entity detail", entityId); }
  function references(value, entityId, field = "") {
    if (Array.isArray(value)) return value.some(item => references(item, entityId, field));
    if (object(value)) return Object.entries(value).some(([key, item]) => references(item, entityId, key));
    return value === entityId && ["owner_id", "source_id", "target_id", "subject_id", "source_entity_id", "settlement_id", "location_id", "labor_entity_ids", "entity_id", "capability_id"].includes(field);
  }
  async function show(view, entityId = null, eventId = null, focus = true) {
    const token = ++generation; current = {view, entityId, eventId};
    document.querySelector("#tick").textContent = "Reported tick: unavailable";
    title.textContent = view; records.replaceChildren(); status.textContent = "Loading snapshots…"; content.setAttribute("aria-busy", "true");
    document.querySelectorAll("#navigation button").forEach(b => { if (b.textContent === view || (view === "Entity detail" && b.textContent === "Entities")) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    if (focus) title.focus();
    if (entityId !== null) records.append(button("Back to Entities", () => show("Entities")));
    try {
      const sources = entityId === null ? views[view].sources : ["entity", "relationships", "needs", "goals", "work", "dispatches", "stages", "events", "consequences"];
      const keys = [...new Set(["world", ...sources])];
      const values = await Promise.all(keys.map(async key => { try { return await fetchSnapshot(key, entityId); } catch (error) { if (key === "run" && error.message === "missing") return null; throw error; } }));
      if (token !== generation) return;
      const data = Object.fromEntries(keys.map((key, index) => [key, values[index]]));
      document.querySelector("#tick").textContent = `Reported tick: ${data.world.tick}`;
      names = new Map((data.entities || []).map(e => [e.id, e.name]));
      if (entityId === null) views[view].render(data);
      else {
        records.append(renderValue(data.entity));
        for (const key of sources.filter(key => key !== "entity")) {
          const values = Array.isArray(data[key]) ? data[key] : Object.values(data[key]).flat();
          renderRecords(`Matching ${key}`, values.filter(value => references(value, entityId)));
          if (key === "events") for (const event of values.filter(value => references(value, entityId))) records.append(button(`View event ${event.id}`, () => show("History", null, event.id)));
        }
      }
      status.textContent = "Snapshots loaded.";
    } catch (error) {
      if (token !== generation) return;
      records.replaceChildren(); if (entityId !== null) records.append(button("Back to Entities", () => show("Entities")));
      status.textContent = prose[error.message] || prose.malformed;
    } finally { if (token === generation) content.setAttribute("aria-busy", "false"); }
  }
  for (const view of Object.keys(views)) document.querySelector("#navigation").append(button(view, () => show(view)));
  document.querySelector("#refresh").addEventListener("click", () => show(current.view, current.entityId, current.eventId));
  show("Overview", null, null, false);
})();
