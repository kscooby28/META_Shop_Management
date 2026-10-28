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
  selectedFrame: null,
};

function cutoutSVG(src, box, cls) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const [x1, y1, x2, y2] = box;
  svg.setAttribute("viewBox", x1 + " " + y1 + " " + (x2 - x1) + " " + (y2 - y1));
  if (cls) svg.setAttribute("class", cls);
  const img = document.createElementNS("http://www.w3.org/2000/svg", "image");
  img.setAttribute("href", src);
  img.setAttribute("x", "0"); img.setAttribute("y", "0");
  img.setAttribute("width", "1000"); img.setAttribute("height", "1000");
  svg.appendChild(img);
  return svg;
}

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
  } else if (modes.some((m) => m === "manual")) {
    pill.textContent = "hand entry (AI unreachable)"; pill.className = "pill demo";
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

function frameOrder() {
  // Walk-around order = upload/seed order, then any extra sighting frames.
  const seen = [];
  for (const img of state.images) {
    if (!seen.includes(img.name)) seen.push(img.name);
  }
  const parts = (state.harvest && state.harvest.parts) || [];
  for (const part of parts) {
    for (const s of (part.sightings || [])) {
      if (!seen.includes(s.frame)) seen.push(s.frame);
    }
  }
  return seen;
}

function buildOverlay(items) {
  const colors = { A: "#1e6b3a", B: "#9a6206", C: "#a83a32" };
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
  return svg;
}

function renderStrip() {
  const box = $("strip");
  box.innerHTML = "";
  const frames = Gallery.stripModel(frameOrder().map((n) => ({ name: n, src: frameSrc(n) })));
  for (const f of frames) {
    const fig = document.createElement("figure");
    if (f.name === state.selectedFrame) fig.className = "sel";
    const img = document.createElement("img");
    img.src = f.src;
    img.alt = f.name;
    fig.appendChild(img);
    const cap = document.createElement("figcaption");
    cap.textContent = f.name;
    fig.appendChild(cap);
    if (Gallery.isDemoFrame(f.name)) {
      const badge = document.createElement("span");
      badge.className = "demobadge";
      badge.textContent = "DEMO";
      fig.appendChild(badge);
    }
    fig.addEventListener("click", () => {
      state.selectedFrame = f.name;
      renderStrip();
      renderViewer();
    });
    box.appendChild(fig);
  }
}

function renderViewer() {
  const box = $("viewer");
  box.innerHTML = "";
  const frame = Gallery.selectFrame(
    frameOrder().map((n) => ({ name: n, src: frameSrc(n) })),
    state.selectedFrame
  );
  if (!frame) return;
  state.selectedFrame = frame.name;
  const parts = (state.harvest && state.harvest.parts) || [];
  const items = Gallery.sightingsForFrame(parts, frame.name);
  const wrap = document.createElement("div");
  wrap.className = "imgwrap";
  const img = document.createElement("img");
  img.src = frame.src;
  img.alt = frame.name;
  wrap.appendChild(img);
  wrap.appendChild(buildOverlay(items));
  box.appendChild(wrap);
  const cap = document.createElement("figcaption");
  cap.textContent = frame.name + " — " + items.length + " sighting(s)";
  if (Gallery.isDemoFrame(frame.name)) {
    const badge = document.createElement("span");
    badge.className = "demobadge";
    badge.textContent = "DEMO FRAME";
    cap.appendChild(document.createTextNode(" "));
    cap.appendChild(badge);
  }
  box.appendChild(cap);
}

function renderFrames() {
  renderStrip();
  renderViewer();
}

function renderPartList() {
  const box = $("partList");
  box.innerHTML = "";
  const parts = (state.harvest && state.harvest.parts) || [];
  for (const part of parts) {
    const li = document.createElement("li");
    li.className = "clickable";
    const grade = gradeOf(part.id);
    const thumb = Gallery.partThumb(part);
    if (thumb) li.appendChild(cutoutSVG(frameSrc(thumb.frame), thumb.box, "thumb"));
    li.insertAdjacentHTML("beforeend",
      (grade ? '<span class="grade grade-' + grade + '" style="width:1.5rem;height:1.5rem;line-height:1.5rem;font-size:0.8rem">' + grade + "</span>" : "") +
      "<strong>" + esc(part.label) + "</strong>" +
      "<span>condition: " + esc(part.intact) + "</span>" +
      "<span>count: " + esc(part.count) + "</span>" +
      (part.sightings || []).map((s) => '<span class="tag">' + esc(s.source_tag) + "</span>").join(""));
    li.addEventListener("mouseenter", () => highlightPart(part.id, true));
    li.addEventListener("mouseleave", () => highlightPart(part.id, false));
    if (thumb) {
      li.addEventListener("click", () => {
        state.selectedFrame = thumb.frame;
        renderStrip();
        renderViewer();
        highlightPart(part.id, true);
        document.getElementById("viewer").scrollIntoView({ block: "nearest" });
      });
    }
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
    const hpart = ((state.harvest && state.harvest.parts) || []).find((p) => p.id === v.part_id);
    const vthumb = hpart ? Gallery.partThumb(hpart) : null;
    if (vthumb) card.insertBefore(cutoutSVG(frameSrc(vthumb.frame), vthumb.box, "thumb"), card.firstChild);
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

function totalBig(t) {
  if (t.count === 0) return "$0";
  if (t.low === null || t.low === undefined) return "—";
  if (Math.round(t.low) === Math.round(t.high)) return money(t.high);
  return money(t.low) + "–" + money(t.high);
}

function renderTotals() {
  const box = $("totals");
  const totals = state.report && state.report.totals;
  if (!totals) { box.innerHTML = '<p class="hint">Totals appear after verdicts.</p>'; return; }
  const card = (grade, t, cls, label) =>
    "<div class='totalcard " + cls + "'><div class='lbl'>" + grade + " · " + label +
    " · " + t.count + " part(s)</div><div class='big'>" + totalBig(t) + "</div></div>";
  box.innerHTML =
    "<div class='totalgrid'>" +
    card("A", totals.A, "total-a", "pull and list now") +
    card("B", totals.B, "total-b", "worth it if standing there") +
    "</div>" +
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

/* ---------- bay side ---------- */

const bay = { case: null, plan: null, parts: [], labor: null, vinPhoto: null, editing: null };

function baySplit(value, byLine) {
  return (value || "").split(byLine ? "\n" : ",").map((s) => s.trim()).filter(Boolean);
}

function bayManual() {
  return {
    vehicle: {
      year: $("bayYear").value.trim(),
      make: $("bayMake").value.trim(),
      model: $("bayModel").value.trim(),
      trim: $("bayTrim").value.trim(),
      engine: $("bayEngine").value.trim(),
      source_tags: ["manual-entry"],
    },
    area: $("bayArea").value,
    service_requested: $("bayService").value.trim(),
    symptom: $("baySymptom").value.trim(),
    codes: baySplit($("bayCodes").value, false),
    observations: baySplit($("bayObs").value, true),
  };
}

function renderBayCase() {
  const box = $("bayCaseCard");
  const c = bay.case;
  if (!c) { box.innerHTML = ""; return; }
  if (c.declined) {
    const d = c.decline;
    box.innerHTML =
      '<div class="decline"><div class="dtitle">' + esc(d.title) + "</div>" +
      "<div>" + esc(d.body) + "</div>" +
      '<div class="next">' + esc(d.next_step) + "</div></div>";
    return;
  }
  const v = c.vehicle;
  box.innerHTML =
    '<div class="car-card"><div class="name">' + esc(v.category) + "</div><dl>" +
    "<dt>Year</dt><dd>" + esc(v.year) + "</dd>" +
    "<dt>Trim</dt><dd>" + esc(v.trim) + "</dd>" +
    "<dt>Engine</dt><dd>" + esc(v.engine) + "</dd>" +
    "<dt>Symptom</dt><dd>“" + esc(c.symptom) + "”</dd>" +
    "<dt>Codes</dt><dd>" + (c.codes.length ? esc(c.codes.join("; ")) : "none") + "</dd>" +
    (c.observations.length ? "<dt>Observed</dt><dd>" + esc(c.observations.join("; ")) + "</dd>" : "") +
    (c.stakes ? "<dt>Stakes</dt><dd>" + esc(c.stakes) + ' <span class="sourced">(' + esc(c.stakes_source) + ")</span></dd>" : "") +
    "<dt>Source</dt><dd>" + esc((v.source_tags || []).join(", ")) + "</dd>" +
    "</dl>" +
    (v.notes || []).map((n) => '<div class="notice">' + esc(n) + "</div>").join("") +
    "</div>";
}

function scoreLine(t) {
  const p = t.score_parts || {};
  const bits = [];
  if (p.symptom_match) bits.push("matches symptom +" + p.symptom_match);
  if (p.code_match) bits.push("matches code +" + p.code_match);
  if (p.rules_out_expensive) bits.push("rules out an expensive job +" + p.rules_out_expensive);
  if (p.quick) bits.push("quick +" + p.quick);
  if (p.shop_boost) bits.push("shop boost +" + p.shop_boost);
  if (p.suspected_cause) bits.push("suspected cause +" + p.suspected_cause);
  if (p.eliminated_penalty) bits.push("eliminated " + p.eliminated_penalty);
  return (t.score || 0) + " points (" + (bits.join(", ") || "no inputs") + ")";
}

function renderBayPlan() {
  const box = $("bayPlan");
  box.innerHTML = "";
  const plan = bay.plan;
  if (!plan) return;
  const done = Object.keys(plan.results).length;
  const total = plan.tests.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  box.insertAdjacentHTML("beforeend",
    "<p><strong>" + done + " of " + total + " recorded</strong></p>" +
    "<div class='progress' style='margin-bottom:0.7rem'><div style='width:" + pct + "%'></div></div>");
  plan.tests.forEach((t, i) => {
    const result = plan.results[t.id];
    const card = document.createElement("div");
    card.className = "testcard" +
      (t.standing === "eliminated" ? " eliminated" : "") +
      (result === "pass" ? " doneok" : "") +
      (result === "fail" ? " donefail" : "");
    const status = result
      ? '<span class="status ' + result + '">' + result.toUpperCase() + "</span>"
      : t.standing === "eliminated"
        ? '<span class="status out">RULED OUT</span>'
        : '<span class="status">PENDING</span>';
    const gate = t.final_gate ? ' <span class="gatebadge">final gate — still open</span>' : "";
    if (bay.editing === t.id) {
      card.innerHTML =
        '<div class="head"><span class="rank">' + (i + 1) + "</span>" +
        '<input data-ef="title" type="text" value="' + esc(t.title) + '" style="flex:1"></div>' +
        '<div class="bayform">' +
        '<label>What<input data-ef="what" type="text" value="' + esc(t.what) + '"></label>' +
        '<label>How<input data-ef="how" type="text" value="' + esc(t.how) + '"></label>' +
        '<label>Expected<input data-ef="expected" type="text" value="' + esc(t.expected) + '"></label>' +
        '<label>Minutes<input data-ef="minutes" type="number" min="0" value="' + (t.minutes == null ? "" : t.minutes) + '"></label>' +
        "</div>" +
        '<div class="row"><button type="button" class="small primary" data-save="' + t.id + '">Save</button>' +
        '<button type="button" class="small" data-cancel="1">Cancel</button></div>';
      card.querySelector("[data-save]").addEventListener("click", guard(async () => {
        const edited = bay.plan.tests.map((x) => {
          if (x.id !== t.id) return x;
          const get = (f) => card.querySelector('[data-ef="' + f + '"]').value;
          const minutes = get("minutes").trim();
          return Object.assign({}, x, {
            title: get("title"), what: get("what"), how: get("how"), expected: get("expected"),
            minutes: minutes === "" ? null : Number(minutes),
            minutes_source: minutes === "" ? "" : (x.minutes_source || "shop-set estimate"),
          });
        });
        bay.editing = null;
        await bayEditPlan(edited, null);
      }));
      card.querySelector("[data-cancel]").addEventListener("click", () => {
        bay.editing = null;
        renderBayPlan();
      });
    } else {
      card.innerHTML =
        '<div class="head"><span class="rank">' + (i + 1) + "</span>" +
        '<span class="tname">' + esc(t.title) + "</span>" + status + gate + "</div>" +
        "<table>" +
        "<tr><th>What to check</th><td>" + esc(t.what) + "</td></tr>" +
        "<tr><th>How</th><td>" + esc(t.how) + "</td></tr>" +
        "<tr><th>Expected</th><td>" + esc(t.expected) + "</td></tr>" +
        "<tr><th>Why it ranks here</th><td>" + esc(scoreLine(t)) + "</td></tr>" +
        (t.causes.length ? "<tr><th>Causes</th><td>" + esc(t.causes.join("; ")) + "</td></tr>" : "") +
        (plan.notes[t.id] ? "<tr><th>Note</th><td>" + esc(plan.notes[t.id]) + "</td></tr>" : "") +
        "</table>" +
        '<div class="row">' +
        '<input data-note type="text" placeholder="result note (optional)" style="flex:1;min-width:140px">' +
        '<button type="button" class="small" data-res="pass">Pass</button>' +
        '<button type="button" class="small" data-res="fail">Fail</button>' +
        '<button type="button" class="small" data-move="-1">↑</button>' +
        '<button type="button" class="small" data-move="1">↓</button>' +
        '<button type="button" class="small" data-edit="1">Edit</button>' +
        "</div>";
      card.querySelectorAll("[data-res]").forEach((btn) => {
        btn.addEventListener("click", guard(async () => {
          await bayRecord(t.id, btn.getAttribute("data-res"), card.querySelector("[data-note]").value);
        }));
      });
      card.querySelectorAll("[data-move]").forEach((btn) => {
        btn.addEventListener("click", guard(async () => {
          const order = bay.plan.tests.map((x) => x.id);
          const at = order.indexOf(t.id);
          const to = at + Number(btn.getAttribute("data-move"));
          if (to < 0 || to >= order.length) return;
          order.splice(at, 1);
          order.splice(to, 0, t.id);
          await bayEditPlan(null, order);
        }));
      });
      card.querySelector("[data-edit]").addEventListener("click", () => {
        bay.editing = t.id;
        renderBayPlan();
      });
    }
    box.appendChild(card);
  });
  renderBayTrail();
}

function renderBayTrail() {
  const box = $("bayTrail");
  const trail = (bay.plan && bay.plan.trail) || [];
  if (!trail.length) {
    box.innerHTML = '<p class="hint">Results you record appear here with the ranking change each one caused.</p>';
    return;
  }
  box.innerHTML = '<ul class="trail">' + trail.map((e) =>
    "<li><span class='seq'>#" + e.seq + "</span>" + esc(e.caused_by) +
    (e.moved && e.moved.length ? " Moved: " + esc(e.moved.join(", ")) + "." : " Order held.") + "</li>"
  ).join("") + "</ul>";
}

function renderBayParts(note) {
  const box = $("bayParts");
  if (!bay.parts.length) {
    box.innerHTML = "<p>" + esc(note || "No parts listed yet.") + "</p>";
    return;
  }
  box.innerHTML = "<ul class='part-list'>" + bay.parts.map((p) =>
    "<li><strong>" + esc(p.name) + "</strong>" +
    (p.note ? "<span>" + esc(p.note) + "</span>" : "") +
    '<span class="tag">' + esc(p.source || "no source") + "</span></li>"
  ).join("") + "</ul>" + (note ? '<p class="hint">' + esc(note) + "</p>" : "");
}

function renderBayLabor() {
  const box = $("bayLabor");
  const labor = bay.labor;
  if (!labor) { box.innerHTML = '<p class="hint">Labor appears after the plan.</p>'; return; }
  box.innerHTML =
    "<ul class='part-list'>" + labor.lines.map((l) =>
      "<li data-test='" + l.test_id + "'><strong>" + esc(l.title) + "</strong>" +
      '<label>min <input data-min type="number" min="0" value="' + (l.minutes == null ? "" : l.minutes) + '" style="width:5.5rem"></label>' +
      (l.source ? '<span class="tag">' + esc(l.source) + "</span>" : '<span class="missing">no shop time on file</span>') +
      "</li>"
    ).join("") + "</ul>" +
    "<p><strong>" + esc(labor.plain_words) + "</strong></p>";
}

async function bayCreateCase(demoCase) {
  const body = { sessionId: state.sessionId };
  if (demoCase) body.demoCase = demoCase;
  else {
    body.manual = bayManual();
    if (bay.vinPhoto) body.vinPhoto = bay.vinPhoto;
  }
  const res = await api("/api/bay/intake", body);
  state.sessionId = res.sessionId;
  bay.case = res.case;
  bay.plan = null;
  state.modes.bay = res.mode;
  setPill();
  if (res.notice) notice(esc(res.notice));
  renderBayCase();
  if (res.case.declined) {
    feed("Bay case declined: " + res.case.decline.title,
      "tool bay.intake — policy gate → decline card (" + res.mode + ")");
    return res;
  }
  const v = res.case.vehicle;
  feed("Bay case opened: " + v.category,
    "tool bay.intake — symptom + " + (res.case.codes || []).length + " code(s) → " + v.category + " (" + res.mode + ")");
  await bayDraftPlan();
  return res;
}

async function bayDraftPlan() {
  const res = await api("/api/bay/plan", { sessionId: state.sessionId });
  bay.plan = res.plan;
  state.modes.bay = res.mode;
  setPill();
  if (res.notice) notice(esc(res.notice));
  renderBayPlan();
  feed("Drafted " + res.plan.tests.length + " ranked tests",
    "tool bay.plan — symptom + codes → ranked tests (" + res.mode + ")");
  await bayParts();
  await bayLabor({});
  return res;
}

async function bayRecord(testId, result, note) {
  const res = await api("/api/bay/result", { sessionId: state.sessionId, testId, result, note });
  bay.plan = res.plan;
  renderBayPlan();
  const last = res.plan.trail[res.plan.trail.length - 1];
  feed("Recorded " + result + ": " + (last ? last.caused_by : ""),
    "tool bay.result — " + testId + " → " + result + ", plan re-ranked");
  return res;
}

async function bayEditPlan(tests, order) {
  const res = await api("/api/bay/plan/edit", { sessionId: state.sessionId, tests, order });
  bay.plan = res.plan;
  renderBayPlan();
  feed("Plan edited, ranking updated", "tool bay.plan.edit — shop edit → re-rank");
  return res;
}

async function bayParts(add) {
  const res = await api("/api/bay/parts", { sessionId: state.sessionId, add });
  bay.parts = res.parts;
  renderBayParts(res.note);
  return res;
}

async function bayLabor(standards) {
  const res = await api("/api/bay/labor", { sessionId: state.sessionId, standards });
  bay.labor = res.labor;
  renderBayLabor();
  return res;
}

async function bayKb() {
  const q = $("bayKbQ").value.trim();
  const res = await fetch("/api/bay/kb?q=" + encodeURIComponent(q));
  const data = await res.json();
  const box = $("bayKb");
  if (!data.notes.length) {
    box.innerHTML = "<p>No notes found. The shop can add its own files under shop_kb/.</p>";
    return;
  }
  box.innerHTML = data.notes.map((n) =>
    '<div class="kbnote"><strong>' + esc(n.title) + "</strong><div>" + esc(n.body) + "</div>" +
    '<span class="src">source: ' + esc(n.source) + "</span></div>"
  ).join("");
  feed("Looked up " + data.notes.length + " repair note(s)" + (q ? " for '" + q + "'" : ""),
    "tool bay.kb — shop notes + samples, no factory content");
}

function bayLaborFromInputs() {
  const standards = {};
  document.querySelectorAll("#bayLabor li[data-test]").forEach((li) => {
    const value = li.querySelector("[data-min]").value.trim();
    if (value !== "") {
      standards[li.getAttribute("data-test")] = { minutes: Number(value), source: "shop-set estimate" };
    }
  });
  return standards;
}

function showView(which) {
  $("view-yard").hidden = which !== "yard";
  $("view-bay").hidden = which !== "bay";
  $("view-inventory").hidden = which !== "inventory";
  $("tabYard").classList.toggle("active", which === "yard");
  $("tabBay").classList.toggle("active", which === "bay");
  $("tabInventory").classList.toggle("active", which === "inventory");
}

function initBay() {
  $("tabYard").addEventListener("click", () => showView("yard"));
  $("tabBay").addEventListener("click", () => { showView("bay"); bayKb(); });
  $("tabInventory").addEventListener("click", () => showView("inventory"));

  document.querySelectorAll("[data-baycase]").forEach((btn) => {
    btn.addEventListener("click", guard(async () => {
      await bayCreateCase(btn.getAttribute("data-baycase"));
    }));
  });
  $("btnBayCase").addEventListener("click", guard(async () => { await bayCreateCase(null); }));
  $("btnBayPlan").addEventListener("click", guard(async () => { await bayDraftPlan(); }));
  $("bayVin").addEventListener("change", guard(async (e) => {
    const file = (e.target.files || [])[0];
    if (!file) { bay.vinPhoto = null; $("bayVinRow").style.display = "none"; return; }
    const data = await downscale(file);
    bay.vinPhoto = { name: file.name, data };
    $("bayPlate").src = data;
    $("bayVinRow").style.display = "";
    feed("VIN photo attached (" + file.name + ")", "bay intake — plate shown below, read on your press");
  }));
  $("btnBayVinRead").addEventListener("click", guard(async () => {
    if (!bay.vinPhoto) throw new Error("attach a VIN photo first");
    const res = await api("/api/inv/vin", { photo: bay.vinPhoto });
    if (res.notice) notice(esc(res.notice));
    renderVinCard("bayVinCard", res.vehicle, res.mode, () => {
      const v = res.vehicle || {};
      if (v.year && v.year !== "unknown") $("bayYear").value = v.year;
      if (v.make && !/unknown/i.test(v.make)) $("bayMake").value = v.make.replace(" (demo sample)", "");
      if (v.model && !/unknown/i.test(v.model)) $("bayModel").value = v.model.replace(" (demo sample)", "");
      if (v.trim && v.trim !== "unknown") $("bayTrim").value = v.trim;
      feed("Vehicle card confirmed into Bay intake", "tool inv.vin — card → form fields");
    });
    feed("Plate read into a vehicle card", "tool inv.vin — plate → card, confirm to fill (" + res.mode + ")");
  }));
  $("btnBayAddTest").addEventListener("click", guard(async () => {
    const title = $("bayTTitle").value.trim();
    if (!title) { notice("Name the test first."); return; }
    const tests = (bay.plan ? bay.plan.tests : []).concat([{
      id: "t-shop-" + Date.now(),
      title,
      what: $("bayTWhat").value.trim(),
      how: $("bayTHow").value.trim(),
      expected: $("bayTExp").value.trim(),
      causes: baySplit($("bayTCauses").value, false),
      eliminates_on_pass: baySplit($("bayTOut").value, false),
      suspects_on_fail: baySplit($("bayTSusp").value, false),
      symptom_match: $("bayTSym").checked,
      code_match: $("bayTCode").checked,
      rules_out_expensive: $("bayTExp2").checked,
      quick: $("bayTQuick").checked,
    }]);
    await bayEditPlan(tests, null);
    $("bayTTitle").value = ""; $("bayTWhat").value = "";
    $("bayTHow").value = ""; $("bayTExp").value = "";
  }));
  $("btnBayAddPart").addEventListener("click", guard(async () => {
    await bayParts({ name: $("bayPName").value, note: $("bayPNote").value });
    $("bayPName").value = ""; $("bayPNote").value = "";
    feed("Added a part to the job list", "tool bay.parts — shop-entered entry");
  }));
  $("btnBayLabor").addEventListener("click", guard(async () => {
    await bayLabor(bayLaborFromInputs());
    feed("Labor math updated", "tool bay.labor — shop times at $180/hr");
  }));
  $("btnBayKb").addEventListener("click", guard(bayKb));
}

initBay();

/* ---------- first-run identity + enthusiast inventory ---------- */

const INV_KEY = "copilot.inventory";
const INV_SEED_KEY = "copilot.invSeeded";
let invState = Inventory.blankInventory();
let invSeeded = false;
let invPartPhotoData = null;

function loadInvState() {
  try {
    const raw = localStorage.getItem(INV_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.cars) && Array.isArray(parsed.parts)) invState = parsed;
    }
  } catch (err) {
    invState = Inventory.blankInventory();
  }
  invSeeded = localStorage.getItem(INV_SEED_KEY) === "1";
}

function saveInvState() {
  localStorage.setItem(INV_KEY, JSON.stringify(invState));
  localStorage.setItem(INV_SEED_KEY, invSeeded ? "1" : "0");
}

function renderSettings() {
  const box = $("settingsBody");
  const p = Profile.loadProfile(localStorage);
  box.innerHTML = "";
  if (!p) {
    box.textContent = "No profile yet — finish first-run setup.";
    return;
  }
  const span = document.createElement("span");
  span.textContent = p.email + " · " + p.mode;
  box.appendChild(span);
  const other = p.mode === "shop" ? "enthusiast" : "shop";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "small";
  btn.textContent = "Switch to " + other;
  btn.addEventListener("click", guard(async () => {
    Profile.setMode(localStorage, other);
    renderSettings();
    showView(Profile.routeFor(other));
    feed("Mode switched to " + other + " in settings", "profile — deliberate change, persisted locally");
  }));
  box.appendChild(btn);
  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "small";
  reset.textContent = "Reset demo profile";
  reset.addEventListener("click", () => {
    Profile.clearProfile(localStorage);
    localStorage.removeItem(INV_KEY);
    localStorage.removeItem(INV_SEED_KEY);
    location.reload();
  });
  box.appendChild(reset);
}

function initIdentity() {
  if (Profile.needsSetup(localStorage)) {
    $("setupOverlay").hidden = false;
  } else {
    showView(Profile.routeFor(Profile.loadProfile(localStorage).mode));
  }
  const choose = (mode) => guard(async () => {
    Profile.saveProfile(localStorage, $("setupEmail").value, mode);
    $("setupOverlay").hidden = true;
    renderSettings();
    showView(Profile.routeFor(mode));
    feed("First-run setup done: " + mode, "profile — stored in this browser only, never sent");
  });
  $("btnSetupShop").addEventListener("click", choose("shop"));
  $("btnSetupFan").addEventListener("click", choose("enthusiast"));
  renderSettings();
}

function fillCarSelect(sel) {
  const current = sel.value;
  sel.innerHTML = "";
  for (const car of invState.cars) {
    const opt = document.createElement("option");
    opt.value = car.id;
    opt.textContent = car.label;
    sel.appendChild(opt);
  }
  if (invState.cars.some((c) => c.id === current)) sel.value = current;
}

function renderInvCars() {
  const box = $("invCars");
  box.innerHTML = "";
  if (!invState.cars.length) {
    box.innerHTML = '<p class="hint">No cars yet. Load the demo inventory or register a car below.</p>';
    return;
  }
  for (const car of invState.cars) {
    const mine = invState.parts.filter((p) => p.carId === car.id);
    const t = Inventory.carTotals(invState, car.id);
    const div = document.createElement("div");
    div.className = "invcar";
    div.innerHTML =
      '<div class="cname">' + esc(car.label) + "</div>" +
      '<div class="ident">' + esc([car.identity.year, car.identity.make, car.identity.model].join(" ")) +
      " · trim " + esc(car.identity.trim) + " · " + esc(car.identity.category) + "</div>" +
      '<div class="ident">' + mine.length + " part(s). " + esc(Inventory.plainTotals(t, "parts")) + "</div>" +
      '<div class="ident">sources: ' + esc(car.source_tags.join(", ")) + "</div>";
    box.appendChild(div);
  }
}

function renderInvKnow() {
  fillCarSelect($("invKnowCar"));
  const box = $("invKnow");
  const carId = $("invKnowCar").value;
  const notes = carId ? Inventory.notesForCar(invState, carId) : [];
  if (!carId) {
    box.innerHTML = '<p class="hint">Register a car first.</p>';
    return;
  }
  if (!notes.length) {
    box.innerHTML = "<p>No knowledge notes for this car yet. Add what you know below — the software will not invent any.</p>";
    return;
  }
  box.innerHTML = "<ul class='part-list'>" + notes.map((n) =>
    "<li><strong>Look for the " + esc(n.part) + "</strong><span>" + esc(n.reason) + "</span>" +
    (n.value !== null ? "<span>about $" + n.value + "</span>" : "<span>value unknown</span>") +
    '<span class="tag">' + esc(n.source) + "</span></li>"
  ).join("") + "</ul>";
}

function renderInvParts() {
  const box = $("invParts");
  fillCarSelect($("invPartCar"));
  if (!invState.parts.length) {
    box.innerHTML = '<p class="hint">Parts appear here once cars exist.</p>';
    return;
  }
  box.innerHTML = "";
  for (const car of invState.cars) {
    const mine = invState.parts.filter((p) => p.carId === car.id);
    if (!mine.length) continue;
    const head = document.createElement("p");
    head.innerHTML = "<strong>" + esc(car.label) + "</strong>";
    box.appendChild(head);
    const ul = document.createElement("ul");
    ul.className = "part-list";
    for (const part of mine) {
      const li = document.createElement("li");
      if (part.photo) {
        const im = document.createElement("img");
        im.className = "invphoto";
        im.src = part.photo;
        im.alt = part.label;
        li.appendChild(im);
      } else {
        const ph = document.createElement("div");
        ph.className = "invphoto-ph";
        ph.textContent = (part.label || "?").slice(0, 1).toUpperCase();
        li.appendChild(ph);
      }
      li.insertAdjacentHTML("beforeend",
        "<strong>" + esc(part.label) + "</strong>" +
        '<span class="relbadge">' + esc(part.relation) + " " + esc(car.label) + "</span>" +
        "<span>" + esc(part.condition) + "</span>" +
        (part.note ? "<span>" + esc(part.note) + "</span>" : "") +
        (part.value !== null && part.valueSource
          ? "<span>$" + part.value + ' <span class="sourced">(' + esc(part.valueSource) + ")</span></span>"
          : '<span class="missing">value unknown</span>') +
        ' <button type="button" class="small" data-list="' + part.id + '">Draft listing</button>');
      li.querySelector("[data-list]").addEventListener("click", guard(async () => {
        await invDraftListing(part.id);
      }));
      ul.appendChild(li);
    }
    box.appendChild(ul);
  }
}

function renderInvTotals() {
  const box = $("invTotals");
  if (!invState.parts.length) {
    box.innerHTML = '<p class="hint">Totals appear once parts exist.</p>';
    return;
  }
  box.innerHTML = "<p><strong>" + esc(Inventory.plainTotals(Inventory.overallTotals(invState), "parts")) + "</strong></p>";
}

function renderInventory() {
  renderInvCars();
  renderInvKnow();
  renderInvParts();
  renderInvTotals();
}

async function invDraftListing(partId) {
  const part = invState.parts.find((p) => p.id === partId);
  if (!part) throw new Error("part not found");
  const car = invState.cars.find((c) => c.id === part.carId) || {};
  const res = await api("/api/listing", {
    sessionId: state.sessionId,
    demo: invSeeded,
    invPart: {
      id: part.id, label: part.label, condition: part.condition,
      value: part.value, valueSource: part.valueSource,
    },
    invCar: car.identity || {},
  });
  state.sessionId = res.sessionId;
  state.draftId = res.draftId;
  $("listingCard").style.display = "";
  $("listingTitle").value = res.draft.title || "";
  $("listingDesc").value = res.draft.description || "";
  $("receipt").innerHTML = "";
  $("cutoutSvg").innerHTML = "";
  $("cutoutNote").textContent = "Inventory draft: no photo cutout. Edit, Approve, then Post — nothing posts without approval.";
  showView("yard");
  document.getElementById("sec-listing").scrollIntoView();
  feed("Drafted a listing from inventory: " + part.label,
    "tool listing.draft — inventory item → Edit/Approve/Post card (" + res.mode + ")");
}

function readPhotoInput(input) {
  const file = (input.files || [])[0];
  if (!file) return Promise.resolve(null);
  return downscale(file).then((data) => ({ name: file.name, data }));
}

function renderVinCard(boxId, vehicle, mode, onConfirm) {
  // Same capture, plate, card, and confirm step in demo and live alike;
  // only the data source swaps when live turns on. The VIN itself is
  // never shown here and never stored.
  const box = $(boxId);
  box.innerHTML = "";
  const v = vehicle || {};
  const category = [v.make, v.model].filter((b) => b && b !== "unknown").join(" · ") || "unknown vehicle";
  const card = document.createElement("div");
  card.className = "vincard";
  card.innerHTML =
    "<strong>Vehicle card</strong> " +
    (mode === "live" ? "" : '<span class="demobadge">DEMO</span>') +
    "<dl>" +
    "<dt>Year</dt><dd>" + esc(v.year || "unknown") + "</dd>" +
    "<dt>Make</dt><dd>" + esc(v.make || "unknown") + "</dd>" +
    "<dt>Model</dt><dd>" + esc(v.model || "unknown") + "</dd>" +
    "<dt>Trim</dt><dd>" + esc(v.trim || "unknown") + "</dd>" +
    "<dt>Category</dt><dd>" + esc(category) + "</dd>" +
    "</dl>" +
    '<div class="row"><button type="button" class="small primary">Confirm into form</button></div>' +
    '<p class="hint">Confirm fills the form, or edit any field by hand. The plate photo never leaves this machine in demo.</p>';
  card.querySelector("button").addEventListener("click", onConfirm);
  box.appendChild(card);
}

function initInventory() {
  loadInvState();
  renderInventory();

  $("btnInvSeed").addEventListener("click", guard(async () => {
    const res = await fetch("/api/inv/seed");
    const data = await res.json();
    if (!data.ok) throw new Error("demo seed missing");
    invState = Inventory.applySeed(data.seed);
    invSeeded = true;
    saveInvState();
    renderInventory();
    feed("Loaded the demo inventory: 4 cars, 6 parts, 1 knowledge note",
      "tool inv.seed — anonymized samples, local only");
  }));
  $("btnInvClear").addEventListener("click", guard(async () => {
    invState = Inventory.blankInventory();
    invSeeded = false;
    saveInvState();
    renderInventory();
    feed("Inventory cleared", "inventory — local data removed from this browser");
  }));

  $("btnInvAddCar").addEventListener("click", guard(async () => {
    const added = Inventory.addCar(invState, {
      label: $("invCarLabel").value,
      identity: {
        year: $("invCarYear").value.trim(),
        make: $("invCarMake").value.trim(),
        model: $("invCarModel").value.trim(),
        trim: $("invCarTrim").value.trim(),
      },
      source_tags: ["owner-entered"],
    });
    invState = added.inv;
    saveInvState();
    renderInventory();
    $("invCarLabel").value = ""; $("invCarYear").value = "";
    $("invCarMake").value = ""; $("invCarModel").value = ""; $("invCarTrim").value = "";
    feed("Registered " + added.car.label, "tool inv.register — " + added.car.identity.category);
  }));

  $("btnInvCarPhoto").addEventListener("click", guard(async () => {
    const photo = await readPhotoInput($("invCarPhoto"));
    if (!photo) throw new Error("attach a picture first");
    const res = await api("/api/inv/identify", { photo, demo: invSeeded });
    const car = res.car || {};
    if (car.year && car.year !== "unknown") $("invCarYear").value = car.year;
    if (car.make && car.make !== "unknown") $("invCarMake").value = car.make;
    if (car.model && car.model !== "unknown") $("invCarModel").value = car.model;
    if (car.trim && car.trim !== "unknown") $("invCarTrim").value = car.trim;
    feed("Picture identified: " + [car.year, car.make, car.model].filter(Boolean).join(" "),
      "tool inv.identify — photo → car ID (" + res.mode + ")");
  }));

  $("invCarVin").addEventListener("change", guard(async (e) => {
    const file = (e.target.files || [])[0];
    if (!file) { $("invVinRow").style.display = "none"; return; }
    $("invVinPlate").src = await downscale(file);
    $("invVinRow").style.display = "";
  }));
  $("btnInvCarVin").addEventListener("click", guard(async () => {
    const photo = await readPhotoInput($("invCarVin"));
    if (!photo) throw new Error("attach a VIN photo first");
    const res = await api("/api/inv/vin", { photo, demo: invSeeded });
    if (res.notice) notice(esc(res.notice));
    renderVinCard("invVinCard", res.vehicle, res.mode, () => {
      const v = res.vehicle || {};
      if (v.year && v.year !== "unknown") $("invCarYear").value = v.year;
      if (v.make && !/unknown/i.test(v.make)) $("invCarMake").value = v.make.replace(" (demo sample)", "");
      if (v.model && !/unknown/i.test(v.model)) $("invCarModel").value = v.model.replace(" (demo sample)", "");
      feed("Vehicle card confirmed into registration", "tool inv.vin — card → form fields");
    });
    feed("Plate read into a vehicle card", "tool inv.vin — plate → card, confirm to fill (" + res.mode + ")");
  }));

  $("invKnowCar").addEventListener("change", renderInvKnow);
  $("btnInvAddNote").addEventListener("click", guard(async () => {
    const value = $("invKnowValue").value.trim();
    invState = Inventory.addNote(invState, {
      carId: $("invKnowCar").value,
      part: $("invKnowPart").value,
      reason: $("invKnowReason").value,
      value: value === "" ? null : Number(value),
      source: value === "" ? "" : "owner-entered",
    });
    saveInvState();
    renderInvKnow();
    $("invKnowPart").value = ""; $("invKnowReason").value = ""; $("invKnowValue").value = "";
    feed("Knowledge note added", "tool inv.note — owner-supplied, car-pinned");
  }));

  $("btnInvPartPhoto").addEventListener("click", guard(async () => {
    const photo = await readPhotoInput($("invPartPhoto"));
    if (!photo) throw new Error("attach a part picture first");
    invPartPhotoData = photo.data; // owner's photo, kept in this browser only
    const res = await api("/api/inv/part-photo", { photo, demo: invSeeded });
    if (res.part.label) $("invPartLabel").value = res.part.label.replace(" (demo sample)", "");
    if (res.part.condition) $("invPartCond").value = res.part.condition;
    if (res.notice) notice(esc(res.notice));
    feed("Part picture described: " + res.part.label,
      "tool inv.part-photo — photo → label + condition (" + res.mode + ")");
  }));

  $("btnInvComps").addEventListener("click", guard(async () => {
    const label = $("invPartLabel").value.trim();
    if (!label) throw new Error("name the part first");
    const res = await api("/api/inv/comps", { label, demo: invSeeded });
    if (res.comp.value !== null && res.comp.source) {
      $("invPartValue").value = res.comp.value;
      $("invPartValue").dataset.source = res.comp.source;
      feed("Comps say about $" + res.comp.value + " (" + res.comp.source + ")",
        "tool inv.comps — '" + label + "' → sourced value (" + res.mode + ")");
    } else {
      $("invPartValue").dataset.source = "";
      notice(esc(res.comp.note || "No reliable value."));
      feed("No reliable value for '" + label + "'", "tool inv.comps — no-data, honestly stated");
    }
  }));

  $("btnInvAddPart").addEventListener("click", guard(async () => {
    const valueRaw = $("invPartValue").value.trim();
    const added = Inventory.attachPart(invState, {
      carId: $("invPartCar").value,
      relation: $("invPartRel").value,
      label: $("invPartLabel").value,
      condition: $("invPartCond").value,
      note: $("invPartNote").value,
      value: valueRaw === "" ? null : Number(valueRaw),
      valueSource: valueRaw === "" ? "" : ($("invPartValue").dataset.source || "owner-entered"),
      source_tags: ["owner-entered"],
    });
    if (invPartPhotoData) added.part.photo = invPartPhotoData;
    invState = added.inv;
    saveInvState();
    renderInventory();
    $("invPartLabel").value = ""; $("invPartCond").value = "";
    $("invPartNote").value = ""; $("invPartValue").value = "";
    $("invPartValue").dataset.source = "";
    $("invPartPhoto").value = "";
    invPartPhotoData = null;
    feed("Attached " + added.part.label + " to " + Inventory.carLabel(invState, added.part.carId),
      "tool inv.attach — part → car (" + added.part.relation + ")");
  }));
}

initIdentity();
initInventory();
