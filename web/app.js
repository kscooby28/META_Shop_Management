/* Shop AI Copilot — Yard side. One page, no dependencies. */
"use strict";

const state = {
  sessionId: null,
  images: [],          // {name, src, data?} — data only for uploads (live path)
  demo: false,
  intake: null,
  harvest: null,
  comps: null,
  report: null,
  rules: null,
  draftId: null,
  modes: {},
  overrides: {},   // partId -> A/B/C, survives re-renders until a fresh grade run
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error((data && data.error) || ("request failed: " + path));
  }
  return data;
}

function feed(text, tool) {
  const box = $("feed");
  const el = document.createElement("details");
  el.open = false;
  const sum = document.createElement("summary");
  sum.textContent = text;
  el.appendChild(sum);
  if (tool) {
    const div = document.createElement("div");
    div.className = "tool";
    div.textContent = tool;
    el.appendChild(div);
  }
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function notice(html) {
  const box = $("notices");
  const div = document.createElement("div");
  div.className = "notice";
  div.innerHTML = html;
  box.appendChild(div);
}

function setPill() {
  const pill = $("modePill");
  const modes = Object.values(state.modes);
  if (!modes.length) { pill.textContent = "not started"; pill.className = "pill"; return; }
  if (modes.every((m) => m === "live" || m === "live-adapter")) {
    pill.textContent = "live AI"; pill.className = "pill live";
  } else if (modes.every((m) => m !== "live" && m !== "live-adapter")) {
    pill.textContent = "demo cache"; pill.className = "pill demo";
  } else {
    pill.textContent = "mixed: live + demo cache"; pill.className = "pill demo";
  }
}

function say(text, who, mode) {
  const thread = $("thread");
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.appendChild(document.createTextNode(text));
  if (mode) {
    const span = document.createElement("span");
    span.className = "mode";
    span.textContent = mode === "live" ? "answered live by Spark" : "answered from the case file (demo cache)";
    div.appendChild(span);
  }
  thread.appendChild(div);
  thread.scrollTop = thread.scrollHeight;
  return div;
}

/* ---------- intake ---------- */

function downscale(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const max = 1280;
      const scale = Math.min(1, max / Math.max(img.width, img.height));
      const w = Math.max(1, Math.round(img.width * scale));
      const h = Math.max(1, Math.round(img.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = w; canvas.height = h;
      canvas.getContext("2d").drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("could not read " + file.name)); };
    img.src = url;
  });
}

const DEMO_FRAMES = [
  { name: "demo-frame-1", src: "demo/frame1.svg" },
  { name: "demo-frame-2", src: "demo/frame2.svg" },
  { name: "demo-frame-3", src: "demo/frame3.svg" },
  { name: "demo-frame-4", src: "demo/frame4.svg" },
];

function renderThumbs() {
  const box = $("thumbs");
  box.innerHTML = "";
  for (const img of state.images) {
    const fig = document.createElement("figure");
    const el = document.createElement("img");
    el.src = img.src;
    el.alt = img.name;
    const cap = document.createElement("figcaption");
    cap.textContent = img.name;
    fig.appendChild(el); fig.appendChild(cap);
    box.appendChild(fig);
  }
}

function frameSrc(frameName) {
  const found = state.images.find((i) => i.name === frameName);
  if (found) return found.src;
  const demo = DEMO_FRAMES.find((d) => d.name === frameName);
  return demo ? demo.src : "";
}

function renderCar(car) {
  const box = $("carCard");
  if (!car) { box.innerHTML = ""; return; }
  const val = (v) => (v == null || v === "" ? "unknown" : esc(v));
  box.innerHTML =
    '<div class="car-card"><div class="name">' +
    [car.year, car.make, car.model].filter((b) => b && b !== "unknown").map(esc).join(" ") +
    "</div><dl>" +
    "<dt>Year</dt><dd>" + val(car.year) + (car.year_note ? " — " + esc(car.year_note) : "") + "</dd>" +
    "<dt>Make</dt><dd>" + val(car.make) + "</dd>" +
    "<dt>Model</dt><dd>" + val(car.model) + "</dd>" +
    "<dt>Trim</dt><dd>" + val(car.trim) + (car.trim_note ? " — " + esc(car.trim_note) : "") + "</dd>" +
    "<dt>Source</dt><dd>" + esc(car.source || "") + " · " + esc((car.source_tags || []).join(", ")) + "</dd>" +
    "</dl></div>";
}

function payloadImages() {
  // Demo path sends names only; live path sends the photo bytes.
  return state.images.map((i) => (state.demo ? { name: i.name } : { name: i.name, data: i.data || "" }));
}

async function runIntake() {
  if (!state.images.length) throw new Error("add photos or load the demo car first");
  const res = await api("/api/intake", {
    sessionId: state.sessionId, images: payloadImages(), demo: state.demo,
  });
  state.sessionId = res.sessionId;
  state.intake = res.intake;
  state.modes.intake = res.mode;
  setPill();
  if (res.notice) notice(esc(res.notice));
  renderCar(res.intake.car);
  const n = (res.intake.parts || []).length;
  feed("Found " + n + " parts on the " +
    [res.intake.car.year, res.intake.car.make, res.intake.car.model].filter(Boolean).join(" "),
    "tool spark.identify — " + state.images.length + " photo(s) → car ID + " + n + " grounded parts (" + res.mode + ")");
  return res;
}

/* ---------- harvest map ---------- */

function gradeOf(partId) {
  const list = (state.report && state.report.verdicts) || [];
  const found = list.find((v) => v.part_id === partId);
  return found ? found.verdict : null;
}

function renderFrames() {
  const box = $("frames");
  box.innerHTML = "";
  const parts = (state.harvest && state.harvest.parts) || [];
  const byFrame = {};
  for (const part of parts) {
    for (const s of (part.sightings || [])) {
      (byFrame[s.frame] = byFrame[s.frame] || []).push({ part, s });
    }
  }
  const colors = { A: "#1e6b3a", B: "#9a6206", C: "#a83a32" };
  for (const [frame, items] of Object.entries(byFrame)) {
    const fig = document.createElement("figure");
    fig.className = "frame";
    const wrap = document.createElement("div");
    wrap.className = "imgwrap";
    const img = document.createElement("img");
    img.src = frameSrc(frame);
    img.alt = frame;
    wrap.appendChild(img);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 1000 1000");
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("class", "overlay");
    for (const { part, s } of items) {
      const grade = gradeOf(part.id);
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("data-part", part.id);
      if (grade) g.setAttribute("class", "part-" + grade);
      const color = colors[grade] || "#1e6b3a";
      if (s.polygon && s.polygon.length >= 3) {
        const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        poly.setAttribute("points", s.polygon.map((p) => p.join(",")).join(" "));
        g.appendChild(poly);
      }
      if (s.box) {
        const [x1, y1, x2, y2] = s.box;
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", x1); rect.setAttribute("y", y1);
        rect.setAttribute("width", Math.max(1, x2 - x1));
        rect.setAttribute("height", Math.max(1, y2 - y1));
        rect.setAttribute("class", "box");
        rect.setAttribute("stroke", color);
        g.appendChild(rect);
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", x1 + 8); label.setAttribute("y", Math.max(40, y1 - 12));
        label.setAttribute("fill", color);
        label.textContent = part.label;
        g.appendChild(label);
      }
      svg.appendChild(g);
    }
    wrap.appendChild(svg);
    fig.appendChild(wrap);
    const cap = document.createElement("figcaption");
    cap.textContent = frame + " — " + items.length + " sighting(s)";
    fig.appendChild(cap);
    box.appendChild(fig);
  }
}

function renderPartList() {
  const box = $("partList");
  box.innerHTML = "";
  const parts = (state.harvest && state.harvest.parts) || [];
  for (const part of parts) {
    const li = document.createElement("li");
    const grade = gradeOf(part.id);
    li.innerHTML =
      (grade ? '<span class="grade grade-' + grade + '" style="width:1.5rem;height:1.5rem;line-height:1.5rem;font-size:0.8rem">' + grade + "</span>" : "") +
      "<strong>" + esc(part.label) + "</strong>" +
      "<span>condition: " + esc(part.intact) + "</span>" +
      "<span>count: " + esc(part.count) + "</span>" +
      (part.sightings || []).map((s) => '<span class="tag">' + esc(s.source_tag) + "</span>").join("");
    li.addEventListener("mouseenter", () => highlightPart(part.id, true));
    li.addEventListener("mouseleave", () => highlightPart(part.id, false));
    box.appendChild(li);
  }
}

function highlightPart(partId, on) {
  document.querySelectorAll("svg.overlay g[data-part]").forEach((g) => {
    if (!on) { g.classList.remove("dim", "lit"); return; }
    g.classList.toggle("lit", g.getAttribute("data-part") === partId);
    g.classList.toggle("dim", g.getAttribute("data-part") !== partId);
  });
}

async function runHarvest() {
  const res = await api("/api/harvest", {
    sessionId: state.sessionId, images: payloadImages(), demo: state.demo,
  });
  state.harvest = res.harvest;
  state.modes.harvest = res.mode;
  setPill();
  if (res.notice) notice(esc(res.notice));
  // Demo fallback swaps to the sample frames so boxes never lie on your photos.
  if (res.mode !== "live") {
    state.demo = true;
    state.images = DEMO_FRAMES.map((d) => ({ name: d.name, src: d.src }));
    renderThumbs();
    renderCar((state.intake && state.intake.car) || res.harvest.car);
  }
  renderFrames();
  renderPartList();
  const n = (res.harvest.parts || []).length;
  const frames = new Set();
  for (const p of res.harvest.parts || []) for (const s of p.sightings || []) frames.add(s.frame);
  feed("Mapped " + n + " parts across " + frames.size + " frames",
    "tool sam.segment — " + n + " parts × " + frames.size + " frames → masks + tracking (" + res.mode + ")");
  return res;
}

/* ---------- comps + verdicts ---------- */

function shopInputsFromCards() {
  const out = {};
  document.querySelectorAll(".verdict").forEach((card) => {
    const pid = card.getAttribute("data-part");
    const entry = {};
    const demand = card.querySelector("[data-f=demand]").value;
    const low = card.querySelector("[data-f=price_low]").value;
    const high = card.querySelector("[data-f=price_high]").value;
    const mins = card.querySelector("[data-f=pull_minutes]").value;
    const override = card.querySelector("[data-f=override]").value;
    if (demand) { entry.demand = demand; entry.demand_source = "shop-entered"; }
    if (low !== "" || high !== "") {
      if (low !== "") entry.price_low = Number(low);
      if (high !== "") entry.price_high = Number(high);
      entry.price_source = "shop-entered";
    }
    if (mins !== "") { entry.pull_minutes = Number(mins); entry.pull_source = "shop-entered"; }
    const kept = override || state.overrides[pid];
    if (kept) entry.override = kept;
    out[pid] = entry;
  });
  return out;
}

async function runComps() {
  const res = await api("/api/comps", { sessionId: state.sessionId });
  state.comps = res.comps;
  state.modes.comps = res.mode;
  setPill();
  const box = $("compsNote");
  box.innerHTML = res.notice ? '<div class="notice">' + esc(res.notice) + "</div>" : "";
  const priced = Object.values(res.comps).filter((c) => c.price_source).length;
  const total = Object.keys(res.comps).length;
  feed("Checked comps: " + priced + " of " + total + " parts have a sourced price",
    "tool comps.lookup (" + res.adapter + ") — " + total + " parts → " + priced + " priced (" + res.mode + ")");
  return res;
}

function money(v) {
  return v == null ? "" : "$" + Math.round(v);
}

function renderVerdicts() {
  const box = $("verdicts");
  box.innerHTML = "";
  const list = (state.report && state.report.verdicts) || [];
  for (const v of list) {
    const inp = v.inputs;
    const card = document.createElement("div");
    card.className = "verdict";
    card.setAttribute("data-part", v.part_id);
    const priceCell = inp.price_known
      ? esc(money(inp.price_low) + (inp.price_high && inp.price_high !== inp.price_low ? " to " + money(inp.price_high) : "")) +
        ' <span class="sourced">(' + esc(inp.price_source) + ")</span>"
      : '<span class="missing">no reliable price</span>';
    const pullCell = inp.pull_minutes != null
      ? esc(inp.pull_minutes + " min") + ' <span class="sourced">(' + esc(inp.pull_source) + ")</span>"
      : '<span class="missing">no pull-time note</span>';
    card.innerHTML =
      '<div class="head"><span class="grade grade-' + v.verdict + '">' + v.verdict + "</span>" +
      '<span class="pname">' + esc(v.label) + "</span>" +
      '<span class="rule">' + esc(v.verdict_means) + " — rule: " + esc(v.rule_name) + ". " + esc(v.rule_explain) + "</span></div>" +
      "<table>" +
      "<tr><th>Condition in photo</th><td>" + esc(inp.intact) + "</td></tr>" +
      "<tr><th>Frames seen</th><td>" + esc(inp.frames_seen) + " (" + esc((inp.frames || []).join(", ")) + ")</td></tr>" +
      "<tr><th>Count</th><td>" + esc(inp.count) + "</td></tr>" +
      "<tr><th>Demand</th><td>" + esc(inp.demand) + (inp.demand_source ? ' <span class="sourced">(' + esc(inp.demand_source) + ")</span>" : ' <span class="missing">(no source)</span>') + "</td></tr>" +
      "<tr><th>Price</th><td>" + priceCell + "</td></tr>" +
      "<tr><th>Pull effort</th><td>" + pullCell + "</td></tr>" +
      "</table>" +
      '<div class="override-row"><span>Overrule:</span>' +
      ["", "A", "B", "C"].map((g) =>
        '<button type="button" class="small" data-override="' + g + '">' + (g === "" ? "clear" : g) + "</button>"
      ).join("") +
      '<input type="hidden" data-f="override" value="">' +
      (v.overridden ? '<span class="sourced">you overruled this grade</span>' : "") +
      "</div>" +
      '<div class="comp-row"><span>Shop comps:</span>' +
      '<label>demand <select data-f="demand"><option value="">—</option><option>high</option><option>medium</option><option>low</option></select></label>' +
      '<label>low $<input data-f="price_low" type="number" min="0"></label>' +
      '<label>high $<input data-f="price_high" type="number" min="0"></label>' +
      '<label>pull min<input data-f="pull_minutes" type="number" min="0"></label>' +
      "</div>";
    card.querySelector('[data-f="override"]').value = state.overrides[v.part_id] || "";
    card.querySelectorAll("[data-override]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const grade = btn.getAttribute("data-override");
        if (grade) state.overrides[v.part_id] = grade;
        else delete state.overrides[v.part_id];
        card.querySelector('[data-f="override"]').value = grade;
        await runVerdicts(true);
      });
    });
    box.appendChild(card);
  }
  // Re-color the harvest map now that grades exist.
  renderFrames();
  renderPartList();
}

async function runVerdicts(fromOverride) {
  if (!fromOverride) state.overrides = {};
  const res = await api("/api/verdicts", {
    sessionId: state.sessionId,
    partInputs: fromOverride ? shopInputsFromCards() : {},
  });
  state.report = res.report;
  Object.assign(state.modes, res.report.modes || {});
  setPill();
  renderVerdicts();
  renderTotals();
  refreshListingParts();
  const counts = { A: 0, B: 0, C: 0 };
  for (const v of res.report.verdicts) counts[v.verdict]++;
  feed("Graded " + res.report.verdicts.length + " parts: " +
    counts.A + " pull-now, " + counts.B + " worth-it, " + counts.C + " leave-it" +
    (fromOverride ? " (your override applied)" : ""),
    "tool verdict.evaluate — " + res.report.verdicts.length + " parts → " +
    counts.A + "A " + counts.B + "B " + counts.C + "C (rules v" + ((state.rules && state.rules.version) || "?") + ")");
  return res;
}

function renderTotals() {
  const box = $("totals");
  const totals = state.report && state.report.totals;
  if (!totals) { box.innerHTML = '<p class="hint">Totals appear after verdicts.</p>'; return; }
  box.innerHTML =
    "<p class='sure'>" + esc(totals.A.plain_words) + "</p>" +
    "<p>" + esc(totals.A.shop_time_plain_words) + "</p>" +
    "<p class='sure'>" + esc(totals.B.plain_words) + "</p>" +
    "<p>" + esc(totals.B.shop_time_plain_words) + "</p>" +
    "<p>" + esc(totals.excluded_note) + "</p>";
}

/* ---------- listing factory ---------- */

function refreshListingParts() {
  const sel = $("listingPart");
  sel.innerHTML = "";
  const list = (state.report && state.report.verdicts) || [];
  const order = { A: 0, B: 1, C: 2 };
  const sorted = list.slice().sort((a, b) => (order[a.verdict] - order[b.verdict]));
  for (const v of sorted) {
    const opt = document.createElement("option");
    opt.value = v.part_id;
    opt.textContent = v.verdict + " — " + v.label;
    sel.appendChild(opt);
  }
}

async function runDraft(partId) {
  const pid = partId || $("listingPart").value;
  if (!pid) throw new Error("run verdicts first, then pick a part");
  const res = await api("/api/listing", { sessionId: state.sessionId, partId: pid });
  state.draftId = res.draftId;
  state.modes.listing = res.mode;
  setPill();
  if (res.notice) notice(esc(res.notice));
  $("listingCard").style.display = "";
  $("listingTitle").value = res.draft.title || "";
  $("listingDesc").value = res.draft.description || "";
  $("receipt").innerHTML = "";
  // Cutout preview: crop the best box out of its source frame.
  const svg = $("cutoutSvg");
  svg.innerHTML = "";
  const cut = res.cutout || {};
  if (cut.box) {
    const [x1, y1, x2, y2] = cut.box;
    svg.setAttribute("viewBox", x1 + " " + y1 + " " + (x2 - x1) + " " + (y2 - y1));
    const img = document.createElementNS("http://www.w3.org/2000/svg", "image");
    img.setAttribute("href", frameSrc(cut.frame));
    img.setAttribute("x", "0"); img.setAttribute("y", "0");
    img.setAttribute("width", "1000"); img.setAttribute("height", "1000");
    svg.appendChild(img);
  }
  $("cutoutNote").textContent = (cut.note || "") + " Source: " + (cut.source_tag || "?");
  const label = ((state.report.verdicts || []).find((v) => v.part_id === pid) || {}).label || pid;
  feed("Drafted a listing for the " + label,
    "tool listing.draft — " + pid + " → Edit/Approve/Post card (" + res.mode + ")");
  return res;
}

async function runApprove() {
  if (!state.draftId) throw new Error("draft a listing first");
  const res = await api("/api/listing/approve", {
    sessionId: state.sessionId,
    draftId: state.draftId,
    title: $("listingTitle").value,
    description: $("listingDesc").value,
    destinations: [
      $("destEbay").checked ? "ebay" : null,
      $("destExchange").checked ? "exchange" : null,
    ].filter(Boolean),
  });
  $("receipt").innerHTML = '<div class="notice">Approved. Nothing has posted — Post is a separate, deliberate press.</div>';
  feed("You approved the listing", "approval gate — draft " + state.draftId + " → approved");
  return res;
}

async function runPost() {
  if (!state.draftId) throw new Error("draft a listing first");
  const res = await api("/api/listing/post", {
    sessionId: state.sessionId, draftId: state.draftId,
  });
  const r = res.receipt || {};
  $("receipt").innerHTML = '<div class="notice">' + esc(r.note || "Posted.") +
    " Destinations: " + esc((r.destinations || []).join(", ") || "none") + ".</div>";
  feed("Posted via the mock outbox (nothing left this machine)",
    "tool listing.post (" + (r.adapter || "mock") + ") → local outbox receipt");
  return res;
}

/* ---------- rules ---------- */

async function loadRules() {
  const res = await fetch("/api/rules");
  const data = await res.json();
  state.rules = data.rules;
  renderRules();
}

function renderRules() {
  const box = $("rulesForm");
  box.innerHTML = "";
  const rules = state.rules;
  if (!rules) return;
  const t = rules.thresholds;
  const wrap = document.createElement("div");
  wrap.className = "row";
  wrap.innerHTML =
    "<label>Pull-now needs frames ≥ <input data-t='min_frames_a' type='number' min='1' value='" + t.min_frames_a + "'></label>" +
    "<label>Pull-now needs price ≥ $<input data-t='min_list_price_a' type='number' min='0' value='" + t.min_list_price_a + "'></label>" +
    "<label>Shop rate $<input data-t='__rate' type='number' min='1' value='" + rules.labor_rate_per_hour + "'>/hr</label>";
  box.appendChild(wrap);
  for (const rule of rules.rules) {
    const div = document.createElement("div");
    div.className = "rule";
    div.innerHTML =
      "<label><input type='checkbox' data-rule='" + rule.id + "'" + (rule.enabled ? " checked" : "") +
      (rule.id === "r_default" ? " disabled" : "") + "> <strong>" + esc(rule.verdict) +
      "</strong> · " + esc(rule.name) + "</label>" +
      "<div class='explain'>" + esc(rule.explain) + "</div>";
    box.appendChild(div);
  }
}

async function saveRules() {
  const thresholds = Object.assign({}, state.rules.thresholds);
  document.querySelectorAll("#rulesForm [data-t]").forEach((el) => {
    const key = el.getAttribute("data-t");
    if (key === "__rate") return;
    thresholds[key] = Number(el.value);
  });
  const rate = Number(document.querySelector("#rulesForm [data-t=__rate]").value);
  const rules = state.rules.rules.map((r) => {
    const box = document.querySelector("#rulesForm [data-rule=" + r.id + "]");
    return { id: r.id, enabled: r.id === "r_default" ? true : !!(box && box.checked) };
  });
  const res = await fetch("/api/rules", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rules: { labor_rate_per_hour: rate, thresholds, rules } }),
  });
  const data = await res.json();
  if (!res.ok || data.ok === false) throw new Error((data && data.error) || "could not save rules");
  state.rules = data.rules;
  renderRules();
  feed("Rules saved", "tool rules.save — thresholds + toggles stored in rules.json");
  if (state.sessionId && state.harvest) await runVerdicts(true);
}

/* ---------- chat ---------- */

async function sendChat(message) {
  const text = (message || "").trim();
  if (!text) return;
  say(text, "user");
  $("chatInput").value = "";
  const bubble = say("", "bot");
  let mode = "demo-cache";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId: state.sessionId, message: text }),
    });
    if (!res.ok || !res.body) throw new Error("chat failed");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let reply = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const raw = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = raw.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const event = JSON.parse(line.slice(5).trim());
        if (event.type === "mode") mode = event.mode;
        if (event.type === "token") {
          reply += event.text;
          bubble.childNodes[0].textContent = reply;
          $("thread").scrollTop = $("thread").scrollHeight;
        }
      }
    }
  } catch (err) {
    bubble.childNodes[0].textContent = "The chat step hit a snag: " + err.message;
  }
  const span = document.createElement("span");
  span.className = "mode";
  span.textContent = mode === "live" ? "answered live by Spark" : "answered from the case file (demo cache)";
  bubble.appendChild(span);
}

/* ---------- run-all + init ---------- */

async function runAll() {
  await runIntake();
  await runHarvest();
  await runComps();
  await runVerdicts(false);
  // Auto-draft the most valuable pull-now part: the demo's trust moment.
  const list = (state.report && state.report.verdicts) || [];
  const best = list
    .filter((v) => v.verdict === "A")
    .sort((a, b) => ((b.inputs.price_high || 0) - (a.inputs.price_high || 0)))[0];
  if (best) {
    $("listingPart").value = best.part_id;
    await runDraft(best.part_id);
  }
  feed("Flow complete: photo in, verdicts out, listing ready for your approval", null);
}

function guard(fn) {
  return async (...args) => {
    try { await fn(...args); }
    catch (err) {
      notice(esc(err.message));
      feed("Step hit a snag: " + err.message, null);
    }
  };
}

async function init() {
  const res = await api("/api/session", {});
  state.sessionId = res.sessionId;
  await loadRules();
  feed("Ready — upload photos or load the demo car", null);
  say("I am Shop Copilot. Run the flow on the left, then ask me about any grade — I will show the rule behind it.", "bot");

  $("fileInput").addEventListener("change", guard(async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    state.demo = false;
    state.images = [];
    for (const file of files.slice(0, 8)) {
      const data = await downscale(file);
      state.images.push({ name: file.name, src: data, data });
    }
    renderThumbs();
    feed("Loaded " + state.images.length + " photo(s)", "intake — local files, nothing uploaded yet");
  }));

  $("btnDemo").addEventListener("click", guard(async () => {
    state.demo = true;
    state.images = DEMO_FRAMES.map((d) => ({ name: d.name, src: d.src }));
    renderThumbs();
    feed("Loaded the demo car (anonymized Yard Case 4)", "intake — 4 sample frames, no customer data");
  }));

  $("btnIdentify").addEventListener("click", guard(async () => {
    await runIntake();
    await runHarvest();
  }));
  $("btnRunAll").addEventListener("click", guard(runAll));
  $("btnRerun").addEventListener("click", guard(async () => { await runVerdicts(true); }));
  $("btnDraft").addEventListener("click", guard(async () => { await runDraft(); }));
  $("btnApprove").addEventListener("click", guard(runApprove));
  $("btnPost").addEventListener("click", guard(runPost));
  $("btnSaveRules").addEventListener("click", guard(saveRules));

  $("chatForm").addEventListener("submit", (e) => {
    e.preventDefault();
    sendChat($("chatInput").value);
  });
  document.querySelectorAll("#chips button").forEach((btn) => {
    btn.addEventListener("click", () => sendChat(btn.getAttribute("data-chip")));
  });
  $("panelToggle").addEventListener("click", () => $("panel").classList.toggle("open"));
}

init();
