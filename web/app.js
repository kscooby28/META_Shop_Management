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
  forceDemo: localStorage.getItem("copilot.offline") === "1",
  offlineSeen: false,
};

function setBusy(text) {
  const bar = $("busbar");
  if (!text) {
    bar.hidden = true;
    bar.textContent = "";
    return;
  }
  bar.hidden = false;
  bar.textContent = "Working: " + text;
}

function updateOffline() {
  const bar = $("offlineBar");
  if (state.forceDemo) {
    bar.hidden = false;
    bar.textContent = "Offline demo, forced on in settings: everything below runs on demo cache.";
  } else if (state.offlineSeen) {
    bar.hidden = false;
    bar.textContent = "Live AI is unreachable, so this page runs on demo cache. Your work still saves.";
  } else {
    bar.hidden = true;
    bar.textContent = "";
  }
}

function watchFallback(explicitDemo, mode) {
  if (!explicitDemo && mode !== "live" && mode !== "live-adapter") {
    state.offlineSeen = true;
    updateOffline();
  }
}

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
  if (state.forceDemo && body && typeof body === "object") body.demo = true;
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

const EMPTY_ART = {
  gallery: "demo/frame1.svg",
  parts: "demo/frame2.svg",
  verdicts: "demo/frame3.svg",
  baycase: "demo/frame1.svg",
  bayplan: "demo/frame4.svg",
  bayparts: "demo/frame4.svg",
  invcars: "demo/frame1.svg",
  invparts: "demo/frame4.svg",
  comps: "demo/frame2.svg",
  totals: "demo/frame2.svg",
  baytests: "demo/frame3.svg",
  baykb: "demo/frame1.svg",
  baytrail: "demo/frame3.svg",
  invnotes: "demo/frame3.svg",
  compare: "demo/frame4.svg",
  setup: "demo/frame1.svg",
};

function emptyInto(box, key, onAction) {
  const e = UX.emptyState(key);
  box.innerHTML = "";
  const div = document.createElement("div");
  div.className = "emptybox";
  div.innerHTML = (EMPTY_ART[key]
    ? '<img src="' + EMPTY_ART[key] + '" alt="">'
    : "") +
    '<div class="etitle">' + esc(e.title) + "</div><p>" + esc(e.message) + "</p>";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = e.action;
  btn.addEventListener("click", onAction);
  div.appendChild(btn);
  box.appendChild(div);
}

function demoBadge() {
  const s = document.createElement("span");
  s.className = "demobadge";
  s.textContent = "DEMO";
  return s;
}

function isDemoMode(mode) {
  return mode === "demo-cache";
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
    span.textContent = mode === "live" ? "answered live" : "answered from the case file";
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
  if (isDemoMode(state.modes.intake)) {
    box.querySelector(".name").appendChild(document.createTextNode(" "));
    box.querySelector(".name").appendChild(demoBadge());
  }
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
  watchFallback(state.demo, res.mode);
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
  if (!frame) {
    emptyInto(box, "gallery", () => {
      $("btnDemo").click();
      document.getElementById("sec-intake").scrollIntoView();
    });
    return;
  }
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
  stageWorkview(box);
}

function renderFrames() {
  renderStrip();
  renderViewer();
}

function renderPartList() {
  const box = $("partList");
  box.innerHTML = "";
  const parts = (state.harvest && state.harvest.parts) || [];
  if (!parts.length) {
    emptyInto(box, "parts", () => {
      document.getElementById("sec-intake").scrollIntoView();
      $("btnIdentify").click();
    });
    return;
  }
  for (const part of parts) {
    const li = document.createElement("li");
    li.className = "clickable";
    const grade = gradeOf(part.id);
    const thumb = Gallery.partThumb(part);
    if (thumb) li.appendChild(cutoutSVG(frameSrc(thumb.frame), thumb.box, "thumb"));
    li.insertAdjacentHTML("beforeend",
      (grade ? '<span class="grade grade-sm grade-' + grade + '">' + grade + "</span>" : "") +
      "<strong>" + esc(part.label) + "</strong>" +
      "<span>condition: " + esc(part.intact) + "</span>" +
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
  watchFallback(state.demo, res.mode);
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

function amberMoney(escText) {
  // Money reads amber everywhere. Runs on already-escaped text: only a
  // dollar sign followed by digits is wrapped, never markup, never words.
  return escText.replace(/\$[\d,–-]+/g, (m) => '<span class="money">' + m + "</span>");
}

function moneyRow(v) {
  const inp = v.inputs;
  if (!inp.money_grade) return "";
  const nets = (inp.net_low != null && inp.net_high != null)
    ? " Nets " + money(inp.net_low) + "–" + money(inp.net_high) + " after fees."
    : "";
  const count = inp.sold_count != null
    ? " " + inp.sold_count + " sold(s)."
    : " Sold count unknown.";
  const notes = (inp.valuation_notes || []).join(" ");
  return amberMoney(esc(inp.money_grade + " — " + inp.money_reason + nets + count + (notes ? " " + notes : ""))) +
    ' <span class="sourced">(' + esc(inp.price_source || "no source") + ")</span>";
}

function renderVerdicts() {
  const box = $("verdicts");
  box.innerHTML = "";
  const list = (state.report && state.report.verdicts) || [];
  if (!list.length) {
    emptyInto(box, "verdicts", () => {
      document.getElementById("sec-intake").scrollIntoView();
      $("btnRunAll").click();
    });
    return;
  }
  for (const v of list) {
    const inp = v.inputs;
    const card = document.createElement("div");
    card.className = "verdict";
    card.setAttribute("data-part", v.part_id);
    const priceCell = inp.price_known
      ? amberMoney(esc(money(inp.price_low) + (inp.price_high && inp.price_high !== inp.price_low ? " to " + money(inp.price_high) : ""))) +
        ' <span class="sourced">(' + esc(inp.price_source) + ")</span>"
      : '<span class="missing">no reliable price</span>';
    const pullCell = inp.pull_minutes != null
      ? esc(inp.pull_minutes + " min") + ' <span class="sourced">(' + esc(inp.pull_source) + ")</span>"
      : '<span class="missing">no pull-time note</span>';
    const gradeWord = { A: "Pull now", B: "Worth it", C: "Leave it" }[v.verdict] || v.verdict;
    const gradeBtn = (g) =>
      g === ""
        ? '<button type="button" class="gtile gradecard" data-override="">' +
          '<span class="ticon" aria-hidden="true">○</span>' +
          '<span class="tbody"><span class="tword">Rule grade</span>' +
          '<span class="tfield">clear override</span></span></button>'
        : '<button type="button" class="gtile gradecard" data-override="' + g + '">' +
          '<span class="grade grade-sm grade-' + g + '">' + g + "</span>" +
          '<span class="tbody"><span class="tword">' + ({ A: "Pull now", B: "Worth it", C: "Leave it" }[g]) + "</span>" +
          '<span class="tfield">' + priceCell + "</span></span></button>";
    card.innerHTML =
      '<div class="head"><span class="grade grade-' + v.verdict + '">' + v.verdict + "</span>" +
      '<span class="pname">' + esc(v.label) + "</span>" +
      '<span class="vword">' + esc(gradeWord) + "</span>" +
      '<span class="vprice">' + priceCell + "</span>" +
      '<span class="vpull">' + pullCell + "</span></div>" +
      '<details class="rowmore"><summary>Evidence and inputs</summary>' +
      '<div class="rule">' + esc(v.verdict_means) + " — rule: " + esc(v.rule_name) + ". " + esc(v.rule_explain) + "</div>" +
      "<table>" +
      "<tr><th>Condition in photo</th><td>" + esc(inp.intact) + "</td></tr>" +
      "<tr><th>Frames seen</th><td>" + esc(inp.frames_seen) + " (" + esc((inp.frames || []).join(", ")) + ")</td></tr>" +
      "<tr><th>Count</th><td>" + esc(inp.count) + "</td></tr>" +
      "<tr><th>Demand</th><td>" + esc(inp.demand) + (inp.demand_source ? ' <span class="sourced">(' + esc(inp.demand_source) + ")</span>" : ' <span class="missing">(no source)</span>') + "</td></tr>" +
      "<tr><th>Price</th><td>" + priceCell + "</td></tr>" +
      "<tr><th>Pull effort</th><td>" + pullCell + "</td></tr>" +
      (moneyRow(v) ? "<tr><th>Money grade</th><td>" + moneyRow(v) + "</td></tr>" : "") +
      "</table></details>" +
      '<div class="override-row"><span>Overrule:</span>' +
      ["", "A", "B", "C"].map(gradeBtn).join("") +
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
  box.querySelectorAll('select[data-f="demand"]').forEach((sel) => segify(sel));
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
  if (!totals) {
    emptyInto(box, "totals", () => {
      document.getElementById("sec-intake").scrollIntoView();
      $("btnRunAll").click();
    });
    return;
  }
  const card = (grade, t, cls, label) =>
    "<div class='totalcard " + cls + "'><div class='lbl'>" + grade + " · " + label +
    " · " + t.count + " part(s)</div><div class='big'>" + totalBig(t) + "</div></div>";
  const yardDemo = ["intake", "harvest", "comps"].some((k) => isDemoMode(state.modes[k]));
  box.innerHTML =
    (yardDemo ? "<p><span class='demobadge'>DEMO</span> <span class='hint'>sample-backed totals</span></p>" : "") +
    "<div class='totalgrid'>" +
    card("A", totals.A, "total-a", "pull and list now") +
    card("B", totals.B, "total-b", "worth it if standing there") +
    "</div>" +
    "<p class='sure'>" + amberMoney(esc(totals.A.plain_words)) + "</p>" +
    "<p>" + amberMoney(esc(totals.A.shop_time_plain_words)) + "</p>" +
    "<p class='sure'>" + amberMoney(esc(totals.B.plain_words)) + "</p>" +
    "<p>" + amberMoney(esc(totals.B.shop_time_plain_words)) + "</p>" +
    "<p>" + amberMoney(esc(totals.excluded_note)) + "</p>";
}

/* ---------- listing factory ---------- */

function agreesLine(agrees) {
  if (agrees === true) return "Agrees with the primary call.";
  if (agrees === false) return "Disagrees with the primary call — read both before deciding.";
  return "Partly agrees — read both before deciding.";
}

function renderWonder(boxId, res) {
  // Distinct second-opinion card beside the primary call; never overwrites it.
  const box = $(boxId);
  box.innerHTML = "";
  const trig = document.createElement("p");
  trig.className = "hint";
  trig.textContent = res.triggers.length
    ? "Asked because: " + res.triggers.join("; ") + "."
    : "No hard triggers on the visible inputs.";
  box.appendChild(trig);
  if (!res.escalated || !res.opinion) {
    const note = document.createElement("div");
    note.className = "notice";
    note.textContent = res.notice || "No second opinion needed.";
    box.appendChild(note);
    return;
  }
  const card = document.createElement("div");
  card.className = "decline";
  const badge = res.mode === "live" ? "" : " <span class='demobadge'>DEMO</span>";
  card.innerHTML =
    '<div class="dtitle">Second opinion — Wonder Standard' + badge + "</div>" +
    "<div><strong>" + esc(res.opinion.title || "") + "</strong></div>" +
    "<div>" + esc(res.opinion.body || "") + "</div>" +
    (res.opinion.watch ? "<div>Watch: " + esc(res.opinion.watch) + "</div>" : "") +
    '<div class="next">' + esc(agreesLine(res.opinion.agrees)) + "</div>" +
    '<p class="hint">Source: ' + esc(res.opinion.source || "?") + "</p>";
  box.appendChild(card);
  flash(card);
}

async function runWonder(kind, ref, hard, boxId) {
  const res = await api("/api/wonder", {
    sessionId: state.sessionId, kind, ref, hard,
  });
  state.sessionId = res.sessionId;
  if (res.notice && !res.escalated) notice(esc(res.notice));
  if (res.notice && res.escalated) feed(res.notice, "tool wonder.route — demo sample opinion");
  renderWonder(boxId, res);
  scrollSoon($(boxId));
  feed(res.escalated ? "Second opinion in view" : "Router passed: straightforward",
    "tool wonder.route — " + res.triggers.length + " trigger(s) (" + res.mode + ")");
  return res;
}

function gradePill(grade) {
  if (grade === "A" || grade === "B" || grade === "C") {
    return '<span class="grade grade-' + grade + '">' + grade + "</span>";
  }
  return '<span class="missing">?</span>';
}

function renderCompare(res) {
  // Neutral panel over the current setting: one version, not three.
  const box = $("compareOut");
  box.innerHTML = "";
  const modeTag = (mode) => mode === "live"
    ? " <span class='sourced'>(live)</span>"
    : " <span class='demobadge'>DEMO</span>";
  const agree = res.rows.filter((r) =>
    r.grade13 !== "?" && r.gradeOpen !== "?" && r.grade13 === r.gradeOpen).length;
  const head = document.createElement("p");
  head.className = "compare-head";
  head.innerHTML = "<strong>" + agree + " of " + res.rows.length +
    " second looks agree.</strong> " +
    '<span class="hint">Rules decide; agreement is information, not a verdict.</span>';
  box.appendChild(head);
  const table = document.createElement("table");
  table.innerHTML = "<tr><th>Part</th><th>Rule grade</th>" +
    "<th>Muse Spark 1.3" + modeTag(res.mode13) + "</th>" +
    "<th>Muse Spark Open, open-weight via Baseten" + modeTag(res.modeOpen) + "</th></tr>";
  for (const r of res.rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = "<td><strong>" + esc(r.label) + "</strong></td>" +
      "<td>" + gradePill(r.rule) + "</td>" +
      "<td>" + gradePill(r.grade13) +
      ' <span class="hint">' + esc(r.reason13) + "</span></td>" +
      "<td>" + gradePill(r.gradeOpen) +
      ' <span class="hint">' + esc(r.reasonOpen) + "</span></td>";
    table.appendChild(tr);
  }
  const wrap = document.createElement("div");
  wrap.className = "verdict wideonly";
  wrap.appendChild(table);
  box.appendChild(wrap);
  const cards = document.createElement("div");
  cards.className = "narrowonly";
  for (const r of res.rows) {
    const pc = document.createElement("div");
    pc.className = "pccard";
    pc.innerHTML = '<div class="pchead"><strong>' + esc(r.label) + "</strong>" +
      gradePill(r.rule) + "</div>" +
      '<div class="engines">' +
      '<div class="enginecol"><div class="enginelabel">Muse Spark 1.3' + modeTag(res.mode13) + "</div>" +
      gradePill(r.grade13) + ' <span class="hint">' + esc(r.reason13) + "</span></div>" +
      '<div class="enginecol"><div class="enginelabel">Muse Spark Open, open-weight via Baseten' + modeTag(res.modeOpen) + "</div>" +
      gradePill(r.gradeOpen) + ' <span class="hint">' + esc(r.reasonOpen) + "</span></div>" +
      "</div>";
    cards.appendChild(pc);
  }
  box.appendChild(cards);
  const foot = document.createElement("p");
  foot.className = "hint";
  foot.textContent = res.notice13 + (res.noticeOpen ? " " + res.noticeOpen : "") +
    " Open-model source: " + (res.sourceOpen || "?");
  box.appendChild(foot);
  flash(wrap);
  flash(cards);
  scrollSoon(box);
}

async function runCompare(opts) {
  const demoOnly = !!(opts && opts.demo);
  if (!state.report || !(state.report.verdicts || []).length) {
    const box = $("compareOut");
    emptyInto(box, "compare", () => {
      showView("yard");
      document.getElementById("sec-intake").scrollIntoView();
      $("btnRunAll").click();
    });
    return null;
  }
  const res = await api("/api/compare", { sessionId: state.sessionId, demo: demoOnly });
  state.sessionId = res.sessionId;
  renderCompare(res);
  feed("Compared both engines on " + res.rows.length + " parts",
    "tool compare.run — spark 1.3 (" + res.mode13 + ") vs spark open (" + res.modeOpen + ")");
  return res;
}

function refreshListingParts() {
  const sel = $("listingPart");
  const wsel = $("wonderPart");
  wsel.innerHTML = "";
  sel.innerHTML = "";
  const list = (state.report && state.report.verdicts) || [];
  const order = { A: 0, B: 1, C: 2 };
  const sorted = list.slice().sort((a, b) => (order[a.verdict] - order[b.verdict]));
  for (const v of sorted) {
    const opt = document.createElement("option");
    opt.value = v.part_id;
    opt.textContent = v.verdict + " — " + v.label;
    sel.appendChild(opt);
    const wopt = document.createElement("option");
    wopt.value = v.part_id;
    wopt.textContent = v.verdict + " — " + v.label;
    wsel.appendChild(wopt);
  }
  syncPickers();
}

function renderStudio(studio, mode) {
  // Studio photo above, cutout preview below: when the studio step is
  // unavailable the box hides and the card stands on the cutout alone.
  const box = $("studioBox");
  box.innerHTML = "";
  if (!studio || !studio.body) { box.style.display = "none"; return; }
  box.style.display = "";
  if (studio.kind === "image") {
    const img = document.createElement("img");
    img.src = studio.body;
    img.alt = "Studio listing photo";
    box.appendChild(img);
  } else {
    box.insertAdjacentHTML("afterbegin", studio.body);
  }
  const note = document.createElement("div");
  note.className = "hint";
  note.textContent = (studio.note || "") + " Source: " + (studio.source || "?");
  box.appendChild(note);
  if (mode !== "live") box.appendChild(demoBadge());
}

async function runDraft(partId) {
  const pid = partId || $("listingPart").value;
  if (!pid) throw new Error("run verdicts first, then pick a part");
  const res = await api("/api/listing", { sessionId: state.sessionId, partId: pid });
  state.draftId = res.draftId;
  state.modes.listing = res.mode;
  setPill();
  watchFallback(state.demo, res.mode);
  if (res.notice) notice(esc(res.notice));
  $("listingCard").style.display = "";
  $("listingTitle").value = res.draft.title || "";
  $("listingDesc").value = res.draft.description || "";
  UX.clearDraft(localStorage, "listing");
  $("receipt").innerHTML = "";
  markListingDemo();
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
  renderStudio(res.studio, res.mode);
  const label = ((state.report.verdicts || []).find((v) => v.part_id === pid) || {}).label || pid;
  feed("Drafted a listing for the " + label,
    "tool listing.draft — " + pid + " → Edit/Approve/Post card (" + res.mode + ")");
  return res;
}

async function runApprove() {
  if (!state.draftId) throw new Error("press Draft listing again first — your words are still in the boxes");
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
  offerMockMarketplace(r);
  return res;
}

/* Mock marketplace (WO15): after the real Approve gate and the mock-outbox
 * Post, the DIY tier can walk the eBay Developer API shape as a labeled
 * demo: approval receipt in, mock listing plus mock cha-ching out. The
 * mock adapter re-checks the approval itself, so this button cannot post
 * without it either. */
function offerMockMarketplace(receipt) {
  const box = $("receipt");
  const dests = (receipt && receipt.destinations) || [];
  if (dests.indexOf("ebay") < 0) return;
  const wrap = document.createElement("div");
  wrap.className = "notice";
  wrap.textContent = "Approved and posted to the mock outbox. Next in the demo loop: post through the mock marketplace API. ";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "small";
  btn.textContent = "Post to mock marketplace (demo)";
  btn.addEventListener("click", guard(async () => {
    const out = Credentials.mockEbayPost({
      draft: { title: $("listingTitle").value || "mock listing" },
      approval: { approved: true, draftId: state.draftId },
      storage: localStorage,
    });
    const done = document.createElement("div");
    done.className = "notice";
    done.textContent = "Mock listing " + out.listing.id + ": '" + out.listing.title +
      "' — " + out.listing.status + ". " + out.chaching;
    box.appendChild(done);
    feed("Mock marketplace post (demo): listed, then cha-ching",
      "tool mock.ebay.post → mock listing, approval receipt required");
  }));
  wrap.appendChild(btn);
  const hint = document.createElement("div");
  hint.className = "hint";
  hint.textContent = "Needs your eBay developer key + account authorization in Settings (DIY). " +
    "Values stay in this browser; the mock checks presence only.";
  wrap.appendChild(hint);
  box.appendChild(wrap);
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
  span.textContent = mode === "live" ? "answered live" : "answered from the case file";
  bubble.appendChild(span);
}

/* ---------- run-all + init ---------- */

async function runAll(tick) {
  const step = (i) => { if (typeof tick === "function") tick(i); };
  await runIntake();
  step(0);
  await runHarvest();
  step(1);
  await runComps();
  step(2);
  await runVerdicts(false);
  step(3);
  revealResults();
  // Auto-draft the most valuable pull-now part: the demo's trust moment.
  const list = (state.report && state.report.verdicts) || [];
  const best = list
    .filter((v) => v.verdict === "A")
    .sort((a, b) => ((b.inputs.price_high || 0) - (a.inputs.price_high || 0)))[0];
  if (best) {
    $("listingPart").value = best.part_id;
    syncPickers();
    await runDraft(best.part_id);
    scrollSoon($("listingCard"));
    flash($("listingCard"));
  } else {
    scrollSoon($("totals"));
    flash($("totals"));
  }
  feed("Flow complete: photo in, verdicts out, listing ready for your approval", null);
}

function guard(fn, busyLabel) {
  return async (...args) => {
    if (busyLabel) setBusy(busyLabel);
    try { await fn(...args); }
    catch (err) {
      notice(esc(err.message));
      feed("Step hit a snag: " + err.message, null);
    }
    finally { if (busyLabel) setBusy(null); }
  };
}

function micSupported() {
  return !!(navigator.mediaDevices && window.MediaRecorder);
}

async function sendVoice(blob, kind) {
  let audio = null;
  if (blob && blob.size) {
    const data = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("could not read the recording"));
      reader.readAsDataURL(blob);
    });
    audio = { mime: blob.type || "audio/webm", data };
  }
  const res = await api("/api/voice/note", {
    sessionId: state.sessionId, target: { kind }, audio,
  });
  state.sessionId = res.sessionId;
  if (res.notice) notice(esc(res.notice));
  return res;
}

function pressMic(btn, kind, onText) {
  // Push-to-talk: hold (pointer or keyboard) to record, release to send.
  // No mic, blocked mic, or empty recording all degrade to typed notes.
  if (!micSupported()) {
    btn.disabled = true;
    btn.textContent = "Mic unavailable — type instead";
    return;
  }
  const label = btn.textContent;
  let recorder = null, stream = null;
  const chunks = [];
  async function start(e) {
    if (e) e.preventDefault();
    if (recorder) return;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      notice("Mic blocked — type the note instead.");
      return;
    }
    chunks.length = 0;
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (ev) => { if (ev.data && ev.data.size) chunks.push(ev.data); };
    recorder.start();
    btn.textContent = "Listening… release to send";
  }
  async function stop(e) {
    if (e) e.preventDefault();
    if (!recorder) return;
    const rec = recorder;
    recorder = null;
    btn.textContent = label;
    await new Promise((resolve) => { rec.onstop = resolve; rec.stop(); });
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
    try {
      onText(await sendVoice(new Blob(chunks, { type: rec.mimeType }), kind));
    } catch (err) {
      notice(esc(err.message));
    }
  }
  const fail = (fn) => (e) => { fn(e).catch((err) => notice(esc(err.message))); };
  btn.addEventListener("pointerdown", fail(start));
  window.addEventListener("pointerup", fail(stop));
  window.addEventListener("pointercancel", fail(stop));
  btn.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && !e.repeat) fail(start)(e);
  });
  btn.addEventListener("keyup", (e) => {
    if (e.key === "Enter" || e.key === " ") fail(stop)(e);
  });
}

function pokeDraft(box) {
  box.dispatchEvent(new Event("input", { bubbles: true }));
}

/* ===== guided tour (WO12): demo-path walk, creates nothing external =====
 * Ten beats in spine order. Actions reuse the same demo calls the video
 * shows; the tour never approves or posts a listing, never touches rules,
 * and runs every leg on demo cache. Static tests scan this section: beat
 * order, exit on every beat, and no approve/post calls.
 */
const TOUR_BEATS = [
  { id: "chooser", view: null, section: null, title: "One question, once",
    line: "On the very first open, the app asks shop or enthusiast — once, never again — and remembers your answer on this machine." },
  { id: "register", view: "inventory", section: "sec-icars", title: "Register a parts car",
    line: "A photo names the car, a VIN photo fills the blanks, one tap registers it — the app never guesses a field it cannot see." },
  { id: "dme", view: "inventory", section: "sec-iknow", title: "The engine-computer note",
    line: "On this M3 parts car the app surfaces the engine computer — no EWS handshake needed, which is why E30 owners want it — owner-valued at $200." },
  { id: "totals", view: "inventory", section: "sec-itotals", title: "Plain-money totals",
    line: "Totals count only sourced values; unknown parts are named, never guessed into the sum." },
  { id: "listing", view: "yard", section: "sec-listing", title: "The listing gate",
    line: "One tap drafts the listing from the photos. Approve is a human tap — the tour shows the draft and stops here." },
  { id: "ranking", view: "bay", section: "sec-bplan", title: "Ranked test plan",
    line: "A symptom becomes a ranked test plan; every test shows why it sits where it sits." },
  { id: "decline", view: "bay", section: "sec-bcase", title: "A professional decline",
    line: "Jobs the shop will not touch get a clean decline with a next step — never an error, never silence." },
  { id: "close", view: "bay", section: "sec-bplan", title: "Plan complete",
    line: "Every test recorded, the plan is complete — the evidence trail shows exactly what each result changed." },
  { id: "money", view: "yard", section: "sec-verdicts", title: "Money grade",
    line: "Beside every rule grade, the money grade prices the part from real sold ranges, with count and reliability shown." },
  { id: "compare", view: "compare", section: "sec-compare", title: "Both engines",
    line: "Spark 1.3 on the demo leg and Spark Open side by side on the same case — a second look only, rules still decide." },
];

let tourState = null; // { beat } while the tour runs
let tourPreview = false;

function tourBar(beat, index) {
  const bar = document.createElement("div");
  bar.id = "tourBar";
  bar.className = "homehead";
  const strong = document.createElement("strong");
  strong.textContent = "Tour — beat " + (index + 1) + " of " + TOUR_BEATS.length + ": " + beat.title;
  bar.appendChild(strong);
  const span = document.createElement("span");
  span.className = "hint";
  span.textContent = beat.line;
  bar.appendChild(span);
  const journey = document.createElement("div");
  journey.className = "jline";
  journey.setAttribute("role", "img");
  journey.setAttribute("aria-label", "Tour beat " + (index + 1) + " of " + TOUR_BEATS.length);
  TOUR_BEATS.forEach((b, i) => {
    const d = document.createElement("span");
    d.className = "jdot";
    if (i === index) d.classList.add("now");
    if (i < index) d.classList.add("done");
    d.setAttribute("aria-hidden", "true");
    journey.appendChild(d);
  });
  const dest = document.createElement("span");
  dest.className = "jdest";
  dest.textContent = index + 1 < TOUR_BEATS.length ? "Next: " + TOUR_BEATS[index + 1].title : "Last beat";
  journey.appendChild(dest);
  bar.appendChild(journey);
  const next = document.createElement("button");
  next.type = "button";
  next.className = "small primary";
  next.textContent = index + 1 >= TOUR_BEATS.length ? "Finish" : "Next";
  next.addEventListener("click", guard(tourNext, "walking…"));
  bar.appendChild(next);
  const exit = document.createElement("button");
  exit.type = "button";
  exit.className = "small";
  exit.textContent = "Exit tour";
  exit.addEventListener("click", () => exitTour());
  bar.appendChild(exit);
  return bar;
}

function placeTourBar(beat, index) {
  const old = $("tourBar");
  if (old) old.remove();
  const bar = tourBar(beat, index);
  if (beat.id === "chooser") {
    document.querySelector("#setupOverlay .setup-card").appendChild(bar);
  } else {
    const section = document.getElementById(beat.section);
    section.parentNode.insertBefore(bar, section);
  }
  flash(bar);
}

function endTourPreview() {
  if (!tourPreview) return;
  tourPreview = false;
  $("setupOverlay").hidden = true;
  $("setupEmail").disabled = false;
  $("btnSetupShop").disabled = false;
  $("btnSetupFan").disabled = false;
}

/* The tour starts past the doors: entries sit on the Bay and inventory
 * homes, so the door tap is the video opening shot, not a beat. Beats
 * render in the setting current at entry; the tour never swaps settings,
 * never approves, never posts. */
function startTour() {
  if (Profile.needsSetup(localStorage)) {
    notice("Answer the one first-run question first — then take the tour from either home.");
    return;
  }
  tourState = { beat: 0 };
  feed("Tour started: ten beats, demo cache, nothing leaves this machine", "tour — guided spine walk");
  showTourBeat();
}

function exitTour() {
  const old = $("tourBar");
  if (old) old.remove();
  endTourPreview();
  tourState = null;
  feed("Tour exited — explore freely from here", "tour — stopped by hand");
}

async function tourNext() {
  if (!tourState) return;
  if (tourState.beat + 1 >= TOUR_BEATS.length) {
    exitTour();
    feed("Tour finished: the whole spine, ten beats, nothing approved", "tour — complete");
    return;
  }
  tourState.beat += 1;
  await showTourBeat();
}

async function tourEnsureSeed() {
  if (!invState.cars.length) {
    $("btnInvSeed").click();
    for (let i = 0; i < 40 && !invState.cars.length; i++) {
      await new Promise((r) => setTimeout(r, 100));
    }
  }
}

async function showTourBeat() {
  const beat = TOUR_BEATS[tourState.beat];
  endTourPreview();
  if (beat.id === "chooser") {
    $("setupEmail").disabled = true;
    $("btnSetupShop").disabled = true;
    $("btnSetupFan").disabled = true;
    $("setupOverlay").hidden = false;
    tourPreview = true;
  } else if (beat.id === "register" || beat.id === "dme" || beat.id === "totals") {
    showView("inventory");
    await tourEnsureSeed();
    if (beat.id === "register") {
      const d = document.querySelector("#sec-icars details");
      if (d) d.open = true;
    }
  } else if (beat.id === "listing" || beat.id === "money") {
    showView("yard");
    if (!state.report || !(state.report.verdicts || []).length) await runAll();
  } else if (beat.id === "ranking") {
    showView("bay");
    if (!bay.case || bay.case.declined || bay.demoCase !== "case1") await bayCreateCase("case1");
    if (!bay.plan) await bayDraftPlan();
  } else if (beat.id === "decline") {
    // Oil-change decline on purpose: same decline mechanics, and no engine
    // code ever appears on screen, on camera or off.
    showView("bay");
    $("bayYear").value = "2015"; $("bayMake").value = "BMW"; $("bayModel").value = "328i";
    $("bayTrim").value = ""; $("bayEngine").value = "";
    $("bayService").value = "oil change";
    $("baySymptom").value = "due for an oil change";
    $("bayCodes").value = "";
    await bayCreateCase(null);
  } else if (beat.id === "close") {
    showView("bay");
    await bayCreateCase("case1");
    for (const t of bay.plan.tests) {
      if (!bay.plan.results[t.id]) {
        await bayRecord(t.id, t.id === "t4" ? "fail" : "pass", "tour recording");
      }
    }
  } else if (beat.id === "compare") {
    showView("compare");
    await runCompare({ demo: true });
  }
  placeTourBar(beat, tourState.beat);
  const target = beat.id === "listing" ? $("listingCard")
    : beat.id === "close" ? $("bayTrail")
    : beat.section ? document.getElementById(beat.section) : null;
  if (target) {
    flash(target);
    if (beat.id !== "compare") scrollSoon(target);
  }
}
/* ===== end guided tour ===== */

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

  $("btnIdentify").addEventListener("click", guard(
    () => withStages("identify", yardPhoto(), async (tick) => {
      await runIntake();
      tick(0);
      await runHarvest();
      tick(1);
      revealResults();
    }),
    "identifying the car…"));
  $("btnRunAll").addEventListener("click", guard(
    () => withStages("yard", yardPhoto(), (tick) => runAll(tick)),
    "running intake to listing…"));
  $("btnRerun").addEventListener("click", guard(async () => { await runVerdicts(true); }));
  $("btnWonderYard").addEventListener("click", guard(async () => {
    await runWonder("yard", $("wonderPart").value, $("wonderHard").checked, "wonderYard");
  }, "asking the second opinion…"));
  $("btnCompare").addEventListener("click", guard(runCompare, "comparing both engines…"));
  $("btnDraft").addEventListener("click", guard(async () => { await runDraft(); }, "drafting the listing…"));
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

function voiceNotesHtml(c) {
  const notes = (c && c.voice_notes) || [];
  if (!notes.length) return "";
  return "<ul class='part-list'>" + notes.map((n) =>
    "<li><strong>Spoken note:</strong> “" + esc(n.text) + "”" +
    ' <span class="sourced">(' + esc(n.source || "voice") + ")</span></li>"
  ).join("") + "</ul>";
}

function renderBayCase() {
  const box = $("bayCaseCard");
  renderBayHome();
  renderGuides();
  const c = bay.case;
  if (!c) { box.innerHTML = ""; return; }
  if (c.declined) {
    const d = c.decline;
    box.innerHTML =
      '<div class="decline"><div class="dtitle"><span class="dmark" aria-hidden="true">⊘</span>' + esc(d.title) + "</div>" +
      "<div>" + esc(d.body) + "</div>" +
      '<div class="next">' + esc(d.next_step) + "</div></div>" +
      voiceNotesHtml(c);
    return;
  }
  const v = c.vehicle;
  box.innerHTML =
    '<div class="car-card">' +
    (bay.vinPhoto && bay.vinPhoto.data
      ? '<img class="casephoto" alt="Case car photo" src="' + bay.vinPhoto.data + '">'
      : "") +
    '<div class="name">' + esc(v.category) + "</div><dl>" +
    "<dt>Year</dt><dd>" + esc(v.year) + "</dd>" +
    "<dt>Trim</dt><dd>" + esc(v.trim) + "</dd>" +
    "<dt>Engine</dt><dd>" + esc(v.engine) + "</dd>" +
    "<dt>Symptom</dt><dd>“" + esc(c.symptom) + "”</dd>" +
    "<dt>Codes</dt><dd>" + (c.codes.length ? esc(c.codes.join("; ")) : "none") + "</dd>" +
    (c.observations.length ? "<dt>Observed</dt><dd>" + esc(c.observations.join("; ")) + "</dd>" : "") +
    (c.stakes ? "<dt>Stakes</dt><dd>" + esc(c.stakes) + ' <span class="sourced">(' + esc(c.stakes_source) + ")</span></dd>" : "") +
    "<dt>Source</dt><dd>" + esc((v.source_tags || []).join(", ")) + "</dd>" +
    "</dl>" +
    voiceNotesHtml(c) +
    (v.notes || []).map((n) => '<div class="notice">' + esc(n) + "</div>").join("") +
    "</div>";
  if (bay.vinPhoto && bay.vinPhoto.data) {
    stageWorkview(box.querySelector(".car-card"));
  }
  if (isDemoMode(state.modes.bayIntake)) {
    box.querySelector(".name").appendChild(document.createTextNode(" "));
    box.querySelector(".name").appendChild(demoBadge());
  }
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
  renderBayHome();
  renderGuides();
  const plan = bay.plan;
  if (!plan) {
    emptyInto(box, "bayplan", () => {
      document.getElementById("sec-bcase").scrollIntoView();
      $("btnBayPlan").click();
    });
    return;
  }
  if (!plan.tests.length) {
    emptyInto(box, "baytests", () => { $("bayTTitle").focus(); });
    renderBayTrail();
    return;
  }
  const done = Object.keys(plan.results).length;
  const total = plan.tests.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  box.insertAdjacentHTML("beforeend",
    "<p><strong>" + done + " of " + total + " recorded</strong>" +
    (isDemoMode(state.modes.bayPlan) ? " <span class='demobadge'>DEMO</span>" : "") + "</p>" +
    "<div class='progress' style='margin-bottom:0.7rem'><div style='width:" + pct + "%'></div></div>");
  plan.tests.forEach((t, i) => {
    const result = plan.results[t.id];
    const card = document.createElement("div");
    card.setAttribute("data-test", t.id);
    card.className = "testcard" +
      (t.standing === "eliminated" ? " eliminated" : "") +
      (result === "pass" ? " doneok" : "") +
      (result === "fail" ? " donefail" : "");
    const status = result
      ? '<span class="status ' + result + '">' + (result === "pass" ? "✓ PASS" : result === "fail" ? "✕ FAIL" : result.toUpperCase()) + "</span>"
      : t.standing === "eliminated"
        ? '<span class="status out">RULED OUT</span>'
        : '<span class="status">○ PENDING</span>';
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
      const tmeta = (t.minutes == null ? "shop time unknown" : t.minutes + " min") +
        " · " + (t.score || 0) + " pts";
      card.innerHTML =
        '<div class="head"><span class="rank">' + (i + 1) + "</span>" +
        '<span class="tname">' + esc(t.title) + "</span>" + status + gate +
        '<span class="tmeta">' + esc(tmeta) + "</span></div>" +
        "<table>" +
        "<tr><th>What to check</th><td>" + esc(t.what) + "</td></tr>" +
        "<tr><th>How</th><td>" + esc(t.how) + "</td></tr>" +
        "<tr><th>Expected</th><td>" + esc(t.expected) + "</td></tr>" +
        "</table>" +
        '<details class="rowmore"><summary>Why it ranks here</summary><table>' +
        "<tr><th>Score</th><td>" + esc(scoreLine(t)) + "</td></tr>" +
        (t.causes.length ? "<tr><th>Causes</th><td>" + esc(t.causes.join("; ")) + "</td></tr>" : "") +
        (plan.notes[t.id] ? "<tr><th>Note</th><td>" + esc(plan.notes[t.id]) + "</td></tr>" : "") +
        "</table></details>" +
        '<div class="row">' +
        '<input data-note type="text" placeholder="result note (optional)" style="flex:1;min-width:140px">' +
        '<button type="button" class="gtile verdictbtn" data-res="pass">' +
        '<span class="ticon" aria-hidden="true">✓</span>' +
        '<span class="tbody"><span class="tword">Pass</span></span></button>' +
        '<button type="button" class="gtile verdictbtn" data-res="fail">' +
        '<span class="ticon" aria-hidden="true">✕</span>' +
        '<span class="tbody"><span class="tword">Fail</span></span></button>' +
        "</div>" +
        '<div class="row movers">' +
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
  flash(box);
}

function renderBayTrail() {
  const box = $("bayTrail");
  const trail = (bay.plan && bay.plan.trail) || [];
  if (!trail.length) {
    emptyInto(box, "baytrail", () => {
      document.getElementById("sec-bplan").scrollIntoView();
    });
    return;
  }
  const plan = bay.plan;
  const doneCount = Object.keys(plan.results).length;
  box.innerHTML = '<ul class="trail">' + trail.map((e) =>
    "<li><span class='seq'>#" + e.seq + "</span>" + esc(e.caused_by) +
    (e.moved && e.moved.length ? " Moved: " + esc(e.moved.join(", ")) + "." : " Order held.") + "</li>"
  ).join("") + "</ul>";
  if (plan.tests.length && doneCount >= plan.tests.length) {
    const div = document.createElement("div");
    div.className = "emptybox";
    div.innerHTML = "<div class='etitle'>Plan complete — every test recorded.</div>" +
      "<p>Review the parts list and the labor math next.</p>";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Review parts";
    btn.addEventListener("click", () => document.getElementById("sec-bparts").scrollIntoView());
    div.appendChild(btn);
    box.insertBefore(div, box.firstChild);
  }
}

function renderBayParts(note) {
  const box = $("bayParts");
  if (!bay.parts.length) {
    box.innerHTML = note ? "<p>" + esc(note) + "</p>" : "";
    const sub = document.createElement("div");
    box.appendChild(sub);
    emptyInto(sub, "bayparts", () => { $("bayPName").focus(); });
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
    "<p><strong>" + amberMoney(esc(labor.plain_words)) + "</strong></p>";
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
  bay.demoCase = demoCase || null;
  state.modes.bayIntake = res.mode;
  setPill();
  watchFallback(!!demoCase, res.mode);
  if (res.notice) notice(esc(res.notice));
  renderBayCase();
  if (res.case.declined) {
    scrollSoon($("bayCaseCard"));
    flash($("bayCaseCard"));
    feed("Bay case declined: " + res.case.decline.title,
      "tool bay.intake — policy gate → decline card (" + res.mode + ")");
    return res;
  }
  UX.clearDraft(localStorage, "baycase");
  const v = res.case.vehicle;
  feed("Bay case opened: " + v.category,
    "tool bay.intake — symptom + " + (res.case.codes || []).length + " code(s) → " + v.category + " (" + res.mode + ")");
  await bayDraftPlan();
  return res;
}

async function bayDraftPlan() {
  const res = await api("/api/bay/plan", { sessionId: state.sessionId });
  bay.plan = res.plan;
  state.modes.bayPlan = res.mode;
  setPill();
  watchFallback(!!bay.demoCase, res.mode);
  if (res.notice) notice(esc(res.notice));
  renderBayPlan();
  if (!Object.keys(res.plan.results || {}).length) scrollSoon($("bayPlan"));
  feed("Drafted " + res.plan.tests.length + " ranked tests",
    "tool bay.plan — symptom + codes → ranked tests (" + res.mode + ")");
  await bayParts();
  await bayLabor({});
  return res;
}

async function bayRecord(testId, result, note) {
  const before = snapshotRows($("bayPlan"));
  const res = await api("/api/bay/result", { sessionId: state.sessionId, testId, result, note });
  bay.plan = res.plan;
  renderBayPlan();
  const last = res.plan.trail[res.plan.trail.length - 1];
  playFlip($("bayPlan"), before, testId, last ? flipNote(last) : "");
  feed("Recorded " + result + ": " + (last ? last.caused_by : ""),
    "tool bay.result — " + testId + " → " + result + ", plan re-ranked");
  return res;
}

async function bayEditPlan(tests, order) {
  const before = snapshotRows($("bayPlan"));
  const res = await api("/api/bay/plan/edit", { sessionId: state.sessionId, tests, order });
  bay.plan = res.plan;
  renderBayPlan();
  playFlip($("bayPlan"), before, null, "");
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
    emptyInto(box, "baykb", () => {
      document.getElementById("sec-bcase").scrollIntoView();
      $("baySymptom").focus();
    });
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

function flash(el) {
  if (!el || !el.classList) return;
  el.classList.remove("flash");
  void el.offsetWidth; // restart the animation
  el.classList.add("flash");
}

function scrollSoon(el) {
  if (!el || typeof el.scrollIntoView !== "function") return;
  const calm = typeof matchMedia === "function" &&
    matchMedia("(prefers-reduced-motion: reduce)").matches;
  const go = () => {
    try { el.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" }); }
    catch (e) { el.scrollIntoView(); }
  };
  if (typeof requestAnimationFrame === "function") requestAnimationFrame(go);
  else go();
}

function showView(which) {
  const from = typeof currentView === "undefined" ? "yard" : currentView;
  $("view-home").hidden = which !== "home";
  $("view-yard").hidden = which !== "yard";
  $("view-bay").hidden = which !== "bay";
  $("view-inventory").hidden = which !== "inventory";
  $("view-compare").hidden = which !== "compare";
  $("navHome").classList.toggle("active", which === "home");
  const subs = {
    home: "Three doors: fix it, strip it, or your own car.",
    yard: "The lot: point at a parts car, learn which parts are worth pulling.",
    bay: "The repair bench: symptoms in, test plans out.",
    inventory: "Driveway: your cars and parts, what you have and what it is worth.",
    compare: "Two engines grade the same case, side by side.",
  };
  document.querySelector(".top .sub").textContent =
    (subs[which] || subs.yard) + " Built for a Gulf Coast shop.";
  flash(document.querySelector(".work"));
  playViewTransition(document.querySelector(".work"), UX.transitionFor(from, which));
  currentView = which;
}

/* Camera-first intake (WO17): each Take-a-photo button opens a hidden
 * capture input (device camera on phones, picker on desktop); the shot
 * is handed to the existing upload input untouched, so every flow below
 * runs exactly as before. Upload stays beside it as the fallback.
 * WO18 adds the confirm step around that handoff: a guide line before
 * capture, a full-screen preview after, and only the Use photo tap
 * moves the flow forward into the same upload path, unchanged. */
function twinCamera(camId, targetId, btnId) {
  paintShotGuide(btnId, SHOT_FOR_CAM[camId] || "yard");
  $(btnId).addEventListener("click", () => $(camId).click());
  $(camId).addEventListener("change", guard(async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;
    openConfirm(camId, files);
  }));
}

function wireCameras() {
  twinCamera("fileCamera", "fileInput", "btnPhoto");
  twinCamera("bayVinCamera", "bayVin", "btnBayVinPhoto");
  twinCamera("invCarPhotoCamera", "invCarPhoto", "btnInvCarPhotoCam");
  twinCamera("invCarVinCamera", "invCarVin", "btnInvCarVinCam");
  twinCamera("invPartPhotoCamera", "invPartPhoto", "btnInvPartPhotoCam");
  twinCamera("homeHeroCamera", "fileInput", "btnHomePhoto");
}

/* ---------- motion + confirm + sunlight (WO18) ----------
 * Presentation, navigation, and photo-input only. The flows, grades,
 * and gates underneath run exactly as before; this section only wraps
 * them with motion, a confirm step, staged working states, and a
 * sunlight toggle. No approve, post, or rules call lives here. */

let currentView = "yard";

function calmMotion() {
  return typeof matchMedia === "function" &&
    matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function tourActive() {
  return typeof tourState !== "undefined" && !!tourState;
}

function playViewTransition(work, cls) {
  if (!work || !work.classList || calmMotion() || !cls || cls === "none") return;
  work.classList.remove("page-in-right");
  work.classList.remove("page-in-left");
  work.classList.remove("door-fade");
  void work.offsetWidth;
  work.classList.add(cls);
}

/* ---- Bay re-rank FLIP: fail state first, then rows glide ---- */
let flipRun = 0;

function snapshotRows(box) {
  const map = {};
  if (!box || !box.querySelectorAll) return map;
  box.querySelectorAll(".testcard").forEach((card) => {
    map[card.getAttribute("data-test")] = card.getBoundingClientRect().top;
  });
  return map;
}

function flipNote(last) {
  return last.caused_by + (last.moved && last.moved.length
    ? " Moved: " + last.moved.join(", ") + "."
    : "");
}

function playFlip(box, before, focusId, noteText) {
  const run = ++flipRun;
  const calm = calmMotion();
  box.querySelectorAll(".testcard").forEach((card) => {
    const id = card.getAttribute("data-test");
    const was = before[id];
    const now = card.getBoundingClientRect().top;
    const moved = typeof was === "number" && Math.abs(now - was) > 2;
    if (id === focusId && noteText) {
      const p = document.createElement("p");
      p.className = "moved-note";
      p.textContent = noteText;
      card.appendChild(p);
    }
    if (moved && id !== focusId) {
      const p = document.createElement("p");
      p.className = "moved-note";
      p.textContent = "Moved " + (now > was ? "down" : "up") + " in the ranking.";
      card.appendChild(p);
    }
    if (id === focusId || moved) card.classList.add("moved-flash");
    if (moved && !calm) {
      card.classList.add("flip-glide");
      card.style.transform = "translateY(" + Math.round(was - now) + "px)";
    }
  });
  if (calm) return; // reduced motion: instant reorder plus the highlight only
  const raf = typeof requestAnimationFrame === "function"
    ? requestAnimationFrame
    : (fn) => setTimeout(fn, 16);
  raf(() => {
    if (run !== flipRun) return; // interruptible: a newer render wins
    box.querySelectorAll(".flip-glide").forEach((card) => { card.style.transform = ""; });
    setTimeout(() => {
      if (run !== flipRun) return;
      box.querySelectorAll(".flip-glide").forEach((card) => card.classList.remove("flip-glide"));
    }, UX.Motion.flipMs + 60);
  });
}

/* ---- camera confirm: guide before, preview after, Use moves on ---- */
const SHOT_FOR_CAM = {
  fileCamera: "yard",
  homeHeroCamera: "hero",
  bayVinCamera: "bayvin",
  invCarPhotoCamera: "carphoto",
  invCarVinCamera: "carvin",
  invPartPhotoCamera: "part",
};
const TARGET_FOR_CAM = {
  fileCamera: "fileInput",
  homeHeroCamera: "fileInput",
  bayVinCamera: "bayVin",
  invCarPhotoCamera: "invCarPhoto",
  invCarVinCamera: "invCarVin",
  invPartPhotoCamera: "invPartPhoto",
};
const AUTO_SHOT = { bayvin: 1, carvin: 1, carphoto: 1, part: 1 };

let confirmState = null;

function paintShotGuide(btnId, shot) {
  const btn = $(btnId);
  if (!btn || !btn.parentNode) return;
  const next = btn.nextElementSibling;
  if (next && next.classList && next.classList.contains("camguide")) return;
  const g = UX.guideFor(shot);
  const p = document.createElement("p");
  p.className = "camguide";
  p.textContent = g.guide;
  const tag = document.createElement("span");
  tag.className = "mode-tag";
  tag.textContent = g.modeLabel;
  p.appendChild(tag);
  btn.parentNode.insertBefore(p, next);
}

function renderConfirmStrip() {
  const strip = $("confirmStrip");
  strip.innerHTML = "";
  const st = confirmState;
  if (!st) { strip.hidden = true; return; }
  if (UX.guideFor(st.shot).mode !== "whole") { strip.hidden = true; return; }
  strip.hidden = false;
  st.shots.forEach((s, i) => {
    const img = document.createElement("img");
    img.className = "thumb";
    img.alt = "Angle " + (i + 1);
    if (s.url) img.src = s.url;
    strip.appendChild(img);
  });
  const add = document.createElement("button");
  add.type = "button";
  add.className = "gtile";
  add.textContent = "Add another angle";
  const plus = document.createElement("span");
  plus.className = "ticon";
  plus.setAttribute("aria-hidden", "true");
  plus.textContent = "+";
  add.insertBefore(plus, add.firstChild);
  add.addEventListener("click", () => $(st.camId).click());
  strip.appendChild(add);
}

function openConfirm(camId, files) {
  const shot = SHOT_FOR_CAM[camId] || "yard";
  if (!confirmState || confirmState.camId !== camId || confirmState.replaceNext) {
    closeConfirm();
    confirmState = { camId, shot, shots: [], replaceNext: false };
  }
  confirmState.replaceNext = false;
  for (const file of files) {
    let url = null;
    try { url = URL.createObjectURL(file); } catch (err) { url = null; }
    confirmState.shots.push({ file, url });
  }
  const g = UX.guideFor(shot);
  const guide = $("confirmGuide");
  guide.textContent = g.guide;
  const tag = document.createElement("span");
  tag.className = "mode-tag";
  tag.textContent = g.modeLabel;
  guide.appendChild(tag);
  const latest = confirmState.shots[confirmState.shots.length - 1];
  $("confirmPhoto").src = latest.url || "";
  const retakeThumb = document.querySelector("#btnConfirmRetake img.timg");
  if (retakeThumb && latest.url) {
    retakeThumb.src = latest.url;
    retakeThumb.alt = "Shot to retake";
  }
  renderConfirmStrip();
  $("confirmSteps").hidden = true;
  $("confirmSkel").hidden = true;
  $("confirmFail").hidden = true;
  $("confirmDone").hidden = true;
  $("confirmActions").hidden = false;
  $("confirmWorkActions").hidden = true;
  const box = $("confirm");
  const first = box.hidden;
  box.hidden = false;
  if (first && !calmMotion()) {
    const card = $("confirmCard");
    card.classList.remove("sheet-up");
    void card.offsetWidth;
    card.classList.add("sheet-up");
  }
}

function closeConfirm() {
  $("confirm").hidden = true;
  confirmState = null;
}

function confirmRetake() {
  const st = confirmState;
  if (!st || !st.camId) { closeConfirm(); return; }
  st.replaceNext = true;
  $(st.camId).click();
}

function confirmUse() {
  const st = confirmState;
  if (!st || !st.shots.length) { closeConfirm(); return; }
  try {
    const dt = new DataTransfer();
    for (const s of st.shots) dt.items.add(s.file);
    const target = $(TARGET_FOR_CAM[st.camId]);
    target.files = dt.files;
    target.dispatchEvent(new Event("change", { bubbles: true }));
  } catch (err) {
    notice("This browser blocked the camera handoff — use Upload instead.");
    closeConfirm();
    return;
  }
  if (st.shot === "hero") {
    const rect = $("confirmPhoto").getBoundingClientRect();
    const url = st.shots[st.shots.length - 1].url;
    closeConfirm();
    showView("yard");
    heroExpand(rect, url);
    return;
  }
  if (AUTO_SHOT[st.shot]) {
    // Auto-analyzing shot: keep the photo on screen. The analysis
    // wrapper takes this overlay into its working state next.
    $("confirmActions").hidden = true;
    $("confirmWorkActions").hidden = true;
    return;
  }
  closeConfirm();
  flash($("thumbs"));
}

/* ---- photo becomes screen: the capture expands into the app ---- */
function heroExpand(rect, url) {
  if (!rect || !url || calmMotion()) return;
  const box = $("thumbs");
  const target = box ? box.getBoundingClientRect() : null;
  const img = document.createElement("img");
  img.className = "hero-clone";
  img.alt = "";
  img.src = url;
  img.style.left = rect.left + "px";
  img.style.top = rect.top + "px";
  img.style.width = Math.max(1, rect.width) + "px";
  img.style.height = Math.max(1, rect.height) + "px";
  document.body.appendChild(img);
  const dx = target ? (target.left + target.width / 2 - (rect.left + rect.width / 2)) : 0;
  const dy = target ? (target.top + 60 - (rect.top + rect.height / 2)) : 0;
  const s = target && rect.width > 0
    ? Math.min(3, Math.max(1.2, (target.width || rect.width) / rect.width))
    : 1.6;
  const raf = typeof requestAnimationFrame === "function"
    ? requestAnimationFrame
    : (fn) => setTimeout(fn, 16);
  raf(() => {
    img.style.transform = "translate(" + Math.round(dx) + "px," + Math.round(dy) +
      "px) scale(" + s.toFixed(2) + ")";
    img.style.opacity = "0";
    setTimeout(() => {
      if (img.parentNode) img.parentNode.removeChild(img);
    }, UX.Motion.pageMs + 80);
  });
}

function yardPhoto() {
  return state.images.length ? state.images[0].src : null;
}

/* ---- staged work: photo stays, ladder decides what else shows ---- */
let workRerun = null;
let workCancelled = false;

function openWorking(photoSrc, steps) {
  const box = $("confirm");
  const wasHidden = box.hidden;
  box.hidden = false;
  if (photoSrc) $("confirmPhoto").src = photoSrc;
  $("confirmGuide").textContent = "Working on your photo — it stays here until the result lands.";
  const list = $("confirmSteps");
  list.innerHTML = "";
  steps.forEach((s) => {
    const li = document.createElement("li");
    li.className = "confirm-step";
    li.textContent = s;
    list.appendChild(li);
  });
  list.hidden = true; // ladder: quiet first, steps only past 2s
  const skel = $("confirmSkel");
  skel.innerHTML = "";
  skel.hidden = true;
  $("confirmFail").hidden = true;
  $("confirmDone").hidden = true;
  $("confirmActions").hidden = true;
  $("confirmWorkActions").hidden = false;
  if (wasHidden && !calmMotion()) {
    const card = $("confirmCard");
    card.classList.remove("sheet-up");
    void card.offsetWidth;
    card.classList.add("sheet-up");
  }
  const items = Array.from(list.children);
  return {
    showSkel() {
      if (box.hidden) return;
      skel.innerHTML = '<div class="skel"><div class="skel-bar"></div>' +
        '<div class="skel-bar"></div><div class="skel-bar"></div>' +
        '<div class="skel-bar short"></div></div>';
      skel.hidden = false;
    },
    showSteps() {
      if (box.hidden) return;
      list.hidden = false;
    },
    tick(i) {
      const li = items[i];
      if (!li || li.className !== "confirm-step") return;
      li.className = "confirm-step done";
      li.textContent = steps[i] + " — done";
    },
    finishOk() {
      if (box.hidden) return;
      const done = $("confirmDone");
      done.innerHTML = "";
      done.appendChild(document.createTextNode("Done — the result is below."));
      const close = document.createElement("button");
      close.type = "button";
      close.className = "small";
      close.textContent = "Close";
      close.addEventListener("click", () => closeConfirm());
      done.appendChild(close);
      skel.hidden = true;
      list.hidden = true;
      done.hidden = false;
      $("confirmWorkActions").hidden = true;
    },
    finishFail(flow, photo, err) {
      if (box.hidden) return;
      const kind = UX.classifyFailure(err && err.message);
      saveShotDraft(flow, photo, err);
      const fail = $("confirmFail");
      fail.innerHTML = "";
      const line = document.createElement("p");
      line.textContent = UX.failureLine(kind);
      fail.appendChild(line);
      const kept = document.createElement("p");
      kept.className = "hint";
      kept.textContent = "Your photo is saved with the draft — nothing is lost.";
      fail.appendChild(kept);
      const row = document.createElement("div");
      row.className = "row";
      const st = confirmState;
      const again = document.createElement("button");
      again.type = "button";
      again.className = "small";
      again.textContent = "Retake";
      again.addEventListener("click", () => {
        if (st && st.camId) {
          st.replaceNext = true;
          $(st.camId).click();
        } else {
          closeConfirm();
        }
      });
      row.appendChild(again);
      if (kind === "low") {
        const keep = document.createElement("button");
        keep.type = "button";
        keep.className = "small";
        keep.textContent = "Keep as unknown";
        keep.addEventListener("click", () => closeConfirm());
        row.appendChild(keep);
      }
      fail.appendChild(row);
      skel.hidden = true;
      list.hidden = true;
      fail.hidden = false;
      $("confirmWorkActions").hidden = true;
      feed("Step hit a snag: " + (err && err.message), null);
    },
  };
}

function saveShotDraft(flow, photoSrc, err) {
  const small = typeof photoSrc === "string" && photoSrc.length < 150000 &&
    photoSrc.indexOf("blob:") !== 0;
  const draft = {
    at: new Date().toISOString(),
    error: err && err.message ? err.message : "unknown error",
    photo: small ? photoSrc : null,
    photoSaved: small,
  };
  try {
    UX.saveDraft(localStorage, "shot-" + flow, draft);
  } catch (storeErr) {
    try {
      draft.photo = null;
      draft.photoSaved = false;
      UX.saveDraft(localStorage, "shot-" + flow, draft);
    } catch (err2) { /* storage full; the message still stands */ }
  }
}

async function withStages(flow, photoSrc, work) {
  if (tourActive()) return work(() => {});
  const M = UX.Motion;
  const overlay = openWorking(photoSrc, UX.stagesFor(flow));
  workCancelled = false;
  workRerun = () => withStages(flow, photoSrc, work);
  const quietTimer = setTimeout(() => overlay.showSkel(), M.quietMs);
  const stageTimer = setTimeout(() => overlay.showSteps(), M.skeletonMs);
  const stop = () => { clearTimeout(quietTimer); clearTimeout(stageTimer); };
  try {
    const out = await work((i) => overlay.tick(i));
    stop();
    if (!workCancelled) overlay.finishOk();
    return out;
  } catch (err) {
    stop();
    if (!workCancelled) overlay.finishFail(flow, photoSrc, err);
    else feed("Step hit a snag: " + err.message, null);
    return null;
  }
}

/* ---- staged reveal: what, worth, next, details — in that order ---- */
let revealRun = 0;

function revealResults() {
  const run = ++revealRun;
  const boxes = [$("carCard"), $("totals"), $("verdicts"), $("listingCard")].filter((box) => {
    if (!box) return false;
    if (box.style && box.style.display === "none") return false;
    return (box.textContent || "").trim().length > 0;
  });
  if (!boxes.length || calmMotion() || tourActive()) return;
  const M = UX.Motion;
  boxes.forEach((box, i) => {
    box.classList.add("reveal");
    setTimeout(() => {
      if (run === revealRun) box.setAttribute("data-on", "1");
    }, i * M.revealStepMs);
  });
  setTimeout(() => {
    if (run !== revealRun) return;
    boxes.forEach((box) => box.setAttribute("data-on", "1"));
  }, M.maxMs);
}

/* ---- sunlight mode: one tap, header or settings, browser-local ---- */
function applySunlight() {
  const on = UX.loadSunlight(localStorage);
  document.body.classList.toggle("sunlight", on);
  const nav = $("navSun");
  if (nav) nav.classList.toggle("active", on);
  const box = $("sunToggle");
  if (box) box.checked = on;
}

function initMotion() {
  applySunlight();
  $("navSun").addEventListener("click", () => {
    UX.saveSunlight(localStorage, !UX.loadSunlight(localStorage));
    applySunlight();
    renderSettings();
    feed("Sunlight mode " + (UX.loadSunlight(localStorage) ? "on" : "off"),
      "settings — display only, stays in this browser");
  });
  $("btnConfirmRetake").addEventListener("click", () => confirmRetake());
  $("btnConfirmUse").addEventListener("click", () => confirmUse());
  $("btnConfirmCancel").addEventListener("click", () => {
    workCancelled = true;
    workRerun = null;
    closeConfirm();
  });
  $("btnConfirmRetry").addEventListener("click", () => { if (workRerun) workRerun(); });
}

function initBay() {
  $("navHome").addEventListener("click", () => { applySetting("home"); showView("home"); });
  $("navGear").addEventListener("click", () => {
    $("settings").open = true;
    scrollSoon($("settings"));
  });
  $("door-bay").addEventListener("click", (e) => { doorPress(e.currentTarget); applySetting("bay"); showView("bay"); bayKb(); });
  $("door-yard").addEventListener("click", (e) => { doorPress(e.currentTarget); applySetting("yard"); showView("yard"); });
  $("door-driveway").addEventListener("click", (e) => { doorPress(e.currentTarget); applySetting("inventory"); showView("inventory"); });
  $("backYard").addEventListener("click", () => { applySetting("home"); showView("home"); });
  $("backBay").addEventListener("click", () => { applySetting("home"); showView("home"); });
  $("backInv").addEventListener("click", () => { applySetting("home"); showView("home"); });
  $("backCompare").addEventListener("click", () => { applySetting("yard"); showView("yard"); });
  $("btnCompareOpen").addEventListener("click", () => showView("compare"));
  wireCameras();

  document.querySelectorAll("[data-baycase]").forEach((btn) => {
    btn.addEventListener("click", guard(async () => {
      await bayCreateCase(btn.getAttribute("data-baycase"));
    }));
  });
  $("btnBayCase").addEventListener("click", guard(async () => { await bayCreateCase(null); }, "opening the case…"));
  $("btnBayPlan").addEventListener("click", guard(async () => { await bayDraftPlan(); }, "drafting the plan…"));
  $("btnWonderBay").addEventListener("click", guard(async () => {
    await runWonder("bay", "plan", $("bayHard").checked, "wonderBay");
  }, "asking the second opinion…"));
  async function readBayVin() {
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
  }
  $("bayVin").addEventListener("change", guard(async (e) => {
    const file = (e.target.files || [])[0];
    if (!file) { bay.vinPhoto = null; $("bayVinRow").style.display = "none"; return; }
    const data = await downscale(file);
    bay.vinPhoto = { name: file.name, data };
    $("bayPlate").src = data;
    $("bayVinRow").style.display = "";
    await withStages("vin", data, async (tick) => {
      tick(0);
      await readBayVin();
      tick(1);
    });
  }, "reading the plate…"));
  $("btnBayVinRead").addEventListener("click", guard(readBayVin, "reading the plate…"));
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
    UX.clearDraft(localStorage, "baytest");
  }));
  $("btnBayAddPart").addEventListener("click", guard(async () => {
    await bayParts({ name: $("bayPName").value, note: $("bayPNote").value });
    $("bayPName").value = ""; $("bayPNote").value = "";
    UX.clearDraft(localStorage, "baypart");
    feed("Added a part to the job list", "tool bay.parts — shop-entered entry");
  }));
  $("btnBayLabor").addEventListener("click", guard(async () => {
    await bayLabor(bayLaborFromInputs());
    feed("Labor math updated", "tool bay.labor — shop times at $180/hr");
  }));
  $("btnBayKb").addEventListener("click", guard(bayKb));
  pressMic($("btnBayMic"), "bay", (res) => {
    if (bay.case && res.pinned) {
      bay.case.voice_notes = bay.case.voice_notes || [];
      bay.case.voice_notes.push({ text: res.text, source: res.source });
      renderBayCase();
      feed("Voice note pinned to the case", "tool voice.note — mic → text (" + res.mode + ")");
    } else {
      const box = $("bayObs");
      box.value = box.value ? box.value + "\n" + res.text : res.text;
      pokeDraft(box);
      feed("Voice note landed in observations", "tool voice.note — mic → text (" + res.mode + ")");
    }
  });
}


/* ---------- graphical choices (WO20): doors, settings, staging, pickers ---------- */
function doorPress(btn) {
  if (!btn || !btn.classList || calmMotion()) return;
  btn.classList.remove("door-fade");
  void btn.offsetWidth;
  btn.classList.add("door-fade");
}

/* Setting system (WO20 item 3): the entrance tap swaps the whole visual
 * context and it persists per mode. Chrome only: this touches the body
 * dataset and the band art, never the case, so a setting change cannot
 * lose the open case, its grades, or its totals. Compare is neutral and
 * keeps whatever setting is current. */
var SETTING_FOR_VIEW = { home: "home", bay: "shop", yard: "yard", inventory: "garage", compare: null };
var SETTING_BANDS = {
  shop: '<img src="assets/band-shop.png" role="img" aria-label="Illustrated shop interior: lift, workbench, tool wall">',
  yard: '<img src="assets/band-yard.png" role="img" aria-label="Illustrated yard lot: fence, parts cars, daylight">',
  garage: '<img src="assets/band-garage.png" role="img" aria-label="Illustrated home garage: one car, shelves, warm lamp">'
};
function renderSettingBand(s) {
  var work = document.querySelector(".work");
  if (!work) return;
  var band = $("settingBand");
  if (!band) {
    band = document.createElement("div");
    band.id = "settingBand";
    band.className = "settingband";
    work.insertBefore(band, work.firstChild);
  }
  if (!SETTING_BANDS[s]) { band.hidden = true; return; }
  band.hidden = false;
  band.innerHTML = SETTING_BANDS[s];
}
function applySetting(view) {
  var s = SETTING_FOR_VIEW[view];
  if (s === undefined || s === null) return;
  document.body.dataset.setting = s;
  renderSettingBand(s);
}

/* Capture staging (WO20 item 4): frame the evidence photo as the working
 * view. Never touches the photo source — the setting frames it. */
function stageWorkview(container) {
  container.classList.add("staged");
  const wv = document.createElement("div");
  wv.className = "workview";
  wv.textContent = "Working view — the job at hand";
  container.appendChild(wv);
}

/* Graphical pickers (WO20 item 8): every native select stays in the DOM
 * as the hidden data carrier — all logic keeps reading .value — and a
 * segmented group or an option sheet becomes the face. Faces sync from
 * the carrier, never the other way around. */
const pickerSyncs = [];
function syncPickers() {
  pickerSyncs.forEach((fn) => fn());
}
function segify(sel) {
  if (!sel || sel.dataset.segified) return;
  sel.dataset.segified = "1";
  sel.hidden = true;
  const seg = document.createElement("div");
  seg.className = "seg";
  const sync = () => {
    seg.querySelectorAll("button").forEach((b) => {
      b.setAttribute("aria-pressed",
        b.dataset.value === sel.value ? "true" : "false");
    });
  };
  Array.from(sel.options).forEach((opt) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.value = opt.value;
    b.textContent = opt.textContent || "—";
    b.addEventListener("click", () => {
      sel.value = opt.value;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
      sync();
    });
    seg.appendChild(b);
  });
  sel.addEventListener("change", sync);
  sel.parentNode.insertBefore(seg, sel.nextSibling);
  pickerSyncs.push(sync);
  sync();
}
function openOptSheet(sel, title) {
  let sheet = $("optSheet");
  if (!sheet) {
    sheet = document.createElement("div");
    sheet.id = "optSheet";
    sheet.className = "gsheet";
    sheet.setAttribute("role", "dialog");
    sheet.setAttribute("aria-label", title);
    document.body.appendChild(sheet);
  }
  sheet.setAttribute("aria-label", title);
  sheet.innerHTML = "";
  const h = document.createElement("div");
  h.className = "gtitle";
  h.textContent = title;
  sheet.appendChild(h);
  const opts = document.createElement("div");
  opts.className = "gopts";
  Array.from(sel.options).forEach((opt) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "gtile";
    const picked = opt.value !== "" && opt.value === sel.value;
    if (picked) b.setAttribute("aria-pressed", "true");
    const ic = document.createElement("span");
    ic.className = "ticon";
    ic.setAttribute("aria-hidden", "true");
    ic.textContent = picked ? "✓" : "○";
    const tb = document.createElement("span");
    tb.className = "tbody";
    const w = document.createElement("span");
    w.className = "tword";
    w.textContent = opt.textContent || "—";
    tb.appendChild(w);
    b.appendChild(ic);
    b.appendChild(tb);
    b.addEventListener("click", () => {
      sel.value = opt.value;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
      sheet.hidden = true;
      syncPickers();
    });
    opts.appendChild(b);
  });
  const close = document.createElement("button");
  close.type = "button";
  close.className = "gtile";
  close.textContent = "Close";
  close.addEventListener("click", () => { sheet.hidden = true; });
  sheet.appendChild(opts);
  sheet.appendChild(close);
  sheet.hidden = false;
}
function sheetPicker(sel, title) {
  if (!sel || sel.dataset.pickified) return;
  sel.dataset.pickified = "1";
  sel.hidden = true;
  const trig = document.createElement("button");
  trig.type = "button";
  trig.className = "gtile";
  trig.setAttribute("aria-haspopup", "dialog");
  const sync = () => {
    const opt = Array.from(sel.options).find((o) => o.value === sel.value) ||
      sel.options[0];
    trig.innerHTML = "";
    const ic = document.createElement("span");
    ic.className = "ticon";
    ic.setAttribute("aria-hidden", "true");
    ic.textContent = "▤";
    const tb = document.createElement("span");
    tb.className = "tbody";
    const w = document.createElement("span");
    w.className = "tword";
    w.textContent = opt ? opt.textContent : title;
    tb.appendChild(w);
    const f = document.createElement("span");
    f.className = "tfield";
    f.textContent = title + " — tap to change";
    tb.appendChild(f);
    trig.appendChild(ic);
    trig.appendChild(tb);
  };
  trig.addEventListener("click", () => openOptSheet(sel, title));
  sel.addEventListener("change", sync);
  sel.parentNode.insertBefore(trig, sel.nextSibling);
  pickerSyncs.push(sync);
  sync();
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
  // Neutral panel over the current setting: one version, not three.
  const box = $("settingsBody");
  box.classList.add("neutralpanel");
  const p = Profile.loadProfile(localStorage);
  box.innerHTML = "";
  if (!p) {
    emptyInto(box, "setup", () => { $("setupOverlay").hidden = false; });
    return;
  }
  const line = document.createElement("p");
  line.className = "screen-line";
  line.textContent = "Your profile, credentials, and demo switches. Everything here stays on this machine.";
  box.appendChild(line);
  const card = document.createElement("div");
  card.className = "gcard homehead";
  box.appendChild(card);
  const ctitle = document.createElement("div");
  ctitle.className = "ctitle";
  ctitle.textContent = "Profile";
  card.appendChild(ctitle);
  const span = document.createElement("span");
  span.textContent = p.email + " · " + p.mode;
  card.appendChild(span);
  const other = p.mode === "shop" ? "enthusiast" : "shop";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "small";
  btn.textContent = "Switch to " + other;
  btn.addEventListener("click", guard(async () => {
    Profile.setMode(localStorage, other);
    renderSettings();
    var dest = Profile.routeFor(other);
    applySetting(dest);
    showView(dest);
    feed("Mode switched to " + other + " in settings", "profile — deliberate change, persisted locally");
  }));
  card.appendChild(btn);
  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "small";
  reset.textContent = "Reset demo profile";
  reset.addEventListener("click", () => {
    Profile.clearProfile(localStorage);
    localStorage.removeItem(INV_KEY);
    localStorage.removeItem(INV_SEED_KEY);
    localStorage.removeItem(Credentials.KEY);
    location.reload();
  });
  card.appendChild(reset);
  const demoCard = document.createElement("div");
  demoCard.className = "gcard";
  const demoTitle = document.createElement("div");
  demoTitle.className = "ctitle";
  demoTitle.textContent = "Demo";
  demoCard.appendChild(demoTitle);
  box.appendChild(demoCard);
  const off = document.createElement("label");
  off.className = "gtile";
  const offBox = document.createElement("input");
  offBox.type = "checkbox";
  offBox.checked = state.forceDemo;
  offBox.addEventListener("change", () => {
    state.forceDemo = offBox.checked;
    localStorage.setItem("copilot.offline", state.forceDemo ? "1" : "0");
    updateOffline();
    feed(state.forceDemo ? "Offline demo forced on" : "Offline demo off",
      "settings — demo-cache switch, no network touched");
  });
  const offIcon = document.createElement("span");
  offIcon.className = "ticon";
  offIcon.setAttribute("aria-hidden", "true");
  offIcon.textContent = "⊘";
  off.appendChild(offBox);
  off.appendChild(offIcon);
  off.appendChild(document.createTextNode(" Force offline demo"));
  demoCard.appendChild(off);
  const dispCard = document.createElement("div");
  dispCard.className = "gcard";
  const dispTitle = document.createElement("div");
  dispTitle.className = "ctitle";
  dispTitle.textContent = "Display";
  dispCard.appendChild(dispTitle);
  box.appendChild(dispCard);
  const sun = document.createElement("label");
  sun.className = "gtile";
  const sunBox = document.createElement("input");
  sunBox.type = "checkbox";
  sunBox.id = "sunToggle";
  sunBox.checked = UX.loadSunlight(localStorage);
  sunBox.addEventListener("change", () => {
    UX.saveSunlight(localStorage, sunBox.checked);
    applySunlight();
    feed(sunBox.checked ? "Sunlight mode on" : "Sunlight mode off",
      "settings — display only, stays in this browser");
  });
  const sunIcon = document.createElement("span");
  sunIcon.className = "ticon";
  sunIcon.setAttribute("aria-hidden", "true");
  sunIcon.textContent = "☀";
  sun.appendChild(sunBox);
  sun.appendChild(sunIcon);
  sun.appendChild(document.createTextNode(" Sunlight mode — bold type, solid surfaces for glare"));
  dispCard.appendChild(sun);
  const walk = document.createElement("button");
  walk.type = "button";
  walk.className = "small";
  walk.textContent = "Show walkthroughs again";
  walk.addEventListener("click", () => {
    UX.showGuide(localStorage, "shop");
    UX.showGuide(localStorage, "enthusiast");
    renderGuides();
  });
  demoCard.appendChild(walk);
  renderCreds(box);
}

/* Credentials settings (WO15): two profiles, browser-local only. Inputs
 * always render empty and presence renders set/not-set, so a value is
 * never shown after entry. Mock buttons walk the mock adapters below,
 * all labeled demo. */
function renderCreds(box) {
  const head = document.createElement("h4");
  head.textContent = "Credentials (this browser only — never sent, never shown again)";
  box.appendChild(head);
  const cards = [
    { profile: "shop", title: "Shop: distributor login + email API credential",
      blurb: "For live retailer quotes and estimate emails (live integrations are roadmap; the mocks below are demo).",
      mockLabel: "Test distributor login (demo mock)",
      mockFn: () => Credentials.mockDistributorLogin(localStorage) },
    { profile: "diy", title: "DIY: parts-store login + marketplace accounts",
      blurb: "For price checks and posting (live integrations are roadmap; the mocks below are demo).",
      mockLabel: "Test store login (demo mock)",
      mockFn: () => Credentials.mockStoreLogin(localStorage) },
  ];
  for (const card of cards) {
    const wrap = document.createElement("div");
    wrap.className = "gcard";
    const title = document.createElement("div");
    title.className = "ctitle";
    title.textContent = card.title;
    wrap.appendChild(title);
    const blurb = document.createElement("div");
    blurb.className = "hint";
    blurb.textContent = card.blurb;
    wrap.appendChild(blurb);
    const fields = {};
    for (const spec of Credentials.PROFILES[card.profile]) {
      const row = document.createElement("label");
      row.textContent = spec.label + " ";
      const input = document.createElement("input");
      input.type = spec.secret ? "password" : "text";
      input.autocomplete = "off";
      fields[spec.field] = input;
      row.appendChild(input);
      wrap.appendChild(row);
    }
    const present = document.createElement("div");
    present.className = "hint";
    const paint = () => {
      present.textContent = Credentials.presenceLines(localStorage)
        .filter((l) => l.profile === card.profile)
        .map((l) => l.text).join(" · ");
    };
    paint();
    wrap.appendChild(present);
    const save = document.createElement("button");
    save.type = "button";
    save.className = "small";
    save.textContent = "Save " + card.profile + " credentials";
    save.addEventListener("click", guard(async () => {
      const values = {};
      for (const k of Object.keys(fields)) values[k] = fields[k].value;
      Credentials.saveCreds(localStorage, card.profile, values);
      for (const k of Object.keys(fields)) fields[k].value = "";
      paint();
      feed("Credentials saved (" + card.profile + ", presence only shown)",
        "settings — browser-local store, never sent");
    }));
    wrap.appendChild(save);
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "small";
    clear.textContent = "Clear";
    clear.addEventListener("click", () => {
      Credentials.clearCreds(localStorage, card.profile);
      for (const k of Object.keys(fields)) fields[k].value = "";
      paint();
    });
    wrap.appendChild(clear);
    const mockOut = document.createElement("div");
    mockOut.className = "hint";
    const mock = document.createElement("button");
    mock.type = "button";
    mock.className = "small";
    mock.textContent = card.mockLabel;
    mock.addEventListener("click", guard(async () => {
      const session = card.mockFn();
      mockOut.textContent = (session.supplier || session.store) + ": " +
        session.account + " (" + session.sessionId + "). " + session.note;
      feed("Mock login walked (demo): " + (session.supplier || session.store),
        "tool mock.login → presence-checked session, no network");
    }));
    wrap.appendChild(mock);
    wrap.appendChild(mockOut);
    if (card.profile === "diy") {
      const row = document.createElement("label");
      row.textContent = "Mock price check (demo): part name ";
      const name = document.createElement("input");
      name.type = "text";
      name.placeholder = "rear differential";
      row.appendChild(name);
      wrap.appendChild(row);
      const price = document.createElement("button");
      price.type = "button";
      price.className = "small";
      price.textContent = "Check new vs used (demo)";
      const out = document.createElement("div");
      out.className = "hint";
      price.addEventListener("click", () => {
        const fresh = Credentials.mockNewPrice(name.value);
        const hit = ((state.report && state.report.verdicts) || [])
          .filter((v) => (v.label || "").toLowerCase() === (name.value || "").trim().toLowerCase())[0];
        let used = "Used: no graded verdict yet — run the Yard flow to grade it first.";
        if (hit && hit.inputs && hit.inputs.price_known) {
          used = "Used: " + money(hit.inputs.price_low) +
            (hit.inputs.price_high && hit.inputs.price_high !== hit.inputs.price_low
              ? " to " + money(hit.inputs.price_high) : "") +
            " (" + hit.inputs.price_source + ").";
        }
        out.textContent = fresh.known
          ? "New (mock): $" + fresh.newPrice + " (" + fresh.source + "). " + used
          : fresh.note + " " + used;
      });
      wrap.appendChild(price);
      wrap.appendChild(out);
    }
    box.appendChild(wrap);
  }
}

function initIdentity() {
  if (Profile.needsSetup(localStorage)) {
    $("setupOverlay").hidden = false;
  } else {
    showView("home");
  }
  const choose = (mode) => guard(async () => {
    Profile.saveProfile(localStorage, $("setupEmail").value, mode);
    $("setupOverlay").hidden = true;
    renderSettings();
    showView("home");
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
  syncPickers();
}

function renderInvCars() {
  const box = $("invCars");
  box.innerHTML = "";
  if (!invState.cars.length) {
    emptyInto(box, "invcars", () => {
      const d = document.querySelector("#sec-icars details");
      d.open = true;
      $("invCarLabel").focus();
    });
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
      '<div class="ident">' + mine.length + " part(s). " + amberMoney(esc(Inventory.plainTotals(t, "parts"))) + "</div>" +
      '<details class="rowmore"><summary>Sources</summary><div>sources: ' + esc(car.source_tags.join(", ")) + "</div></details>";
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "small";
    rm.textContent = "Remove car";
    rm.addEventListener("click", () => {
      const mine = invState.parts.filter((p) => p.carId === car.id).length;
      const res = UX.guardedDelete(
        window.confirm.bind(window),
        "Remove " + car.label + " and its " + mine + " part(s)? This cannot be undone.",
        () => {
          invState = {
            cars: invState.cars.filter((c) => c.id !== car.id),
            parts: invState.parts.filter((p) => p.carId !== car.id),
            knowledge: invState.knowledge.filter((n) => n.carId !== car.id),
          };
          saveInvState();
          renderInventory();
        }
      );
      if (res.done) feed("Removed " + car.label, "inventory — confirmed delete");
    });
    div.appendChild(rm);
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
    emptyInto(box, "invnotes", () => {
      const d = document.querySelector("#sec-iknow details");
      if (d) d.open = true;
      $("invKnowPart").focus();
    });
    return;
  }
  box.innerHTML = "<ul class='part-list'>" + notes.map((n) =>
    "<li><strong>Look for the " + esc(n.part) + "</strong><span>" + esc(n.reason) + "</span>" +
    (n.value !== null ? '<span>about <span class="money">$' + n.value + "</span></span>" : "<span>value unknown</span>") +
    '<span class="tag">' + esc(n.source) + "</span></li>"
  ).join("") + "</ul>";
}

function renderInvParts() {
  const box = $("invParts");
  fillCarSelect($("invPartCar"));
  if (!invState.parts.length) {
    emptyInto(box, "invparts", () => {
      const d = document.querySelector("#sec-iparts details");
      d.open = true;
      document.getElementById("sec-iparts").scrollIntoView();
    });
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
        stageWorkview(li);
      } else {
        const ph = document.createElement("div");
        ph.className = "invphoto-ph";
        ph.textContent = (part.label || "?").slice(0, 1).toUpperCase();
        li.appendChild(ph);
      }
      li.insertAdjacentHTML("beforeend",
        "<strong>" + esc(part.label) + "</strong>" +
        '<span class="relbadge">' + esc(part.relation) + " " + esc(car.label) + "</span>" +
        (part.value !== null && part.valueSource
          ? '<span><span class="money">$' + part.value + '</span> <span class="sourced">(' + esc(part.valueSource) + ")</span></span>"
          : '<span class="missing">value unknown</span>') +
        ' <button type="button" class="small" data-list="' + part.id + '">Draft listing</button>');
      const more = document.createElement("details");
      more.className = "rowmore";
      const sum = document.createElement("summary");
      sum.textContent = "Condition and note";
      more.appendChild(sum);
      const cond = document.createElement("div");
      cond.textContent = part.condition + (part.note ? " — " + part.note : "");
      more.appendChild(cond);
      li.insertBefore(more, li.querySelector("[data-list]"));
      li.querySelector("[data-list]").addEventListener("click", guard(async () => {
        await invDraftListing(part.id);
      }));
      const rm = document.createElement("button");
      rm.type = "button";
      rm.className = "small";
      rm.textContent = "Remove";
      rm.addEventListener("click", () => {
        const res = UX.guardedDelete(
          window.confirm.bind(window),
          "Remove " + part.label + " from the inventory? This cannot be undone.",
          () => {
            invState = {
              cars: invState.cars,
              parts: invState.parts.filter((p) => p.id !== part.id),
              knowledge: invState.knowledge,
            };
            saveInvState();
            renderInventory();
          }
        );
        if (res.done) feed("Removed " + part.label, "inventory — confirmed delete");
      });
      li.appendChild(rm);
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
  const sentence = Inventory.plainTotals(Inventory.overallTotals(invState), "parts");
  const cut = sentence.indexOf(" across ");
  if (cut < 0) {
    box.innerHTML = "<p><strong>" + amberMoney(esc(sentence)) + "</strong></p>";
  } else {
    box.innerHTML = '<div class="big-money">' + amberMoney(esc(sentence.slice(0, cut))) + "</div>" +
      "<p><strong>" + amberMoney(esc(sentence.slice(cut + 1))) + "</strong></p>";
  }
  if (invSeeded) {
    const line = document.createElement("p");
    line.appendChild(demoBadge());
    line.appendChild(document.createTextNode(" sample-backed totals"));
    box.appendChild(line);
  }
}

function renderInventory() {
  renderInvCars();
  renderInvKnow();
  renderInvParts();
  renderInvTotals();
  renderInvHome();
  renderGuides();
}

function renderInvHome() {
  const box = $("invHome");
  box.innerHTML = "";
  const strong = document.createElement("strong");
  strong.textContent = "Inventory home";
  box.appendChild(strong);
  const span = document.createElement("span");
  span.textContent = invState.cars.length + " car(s), " + invState.parts.length + " part(s).";
  box.appendChild(span);
  const reg = document.createElement("button");
  reg.type = "button";
  reg.className = "small";
  reg.textContent = "Register a car";
  reg.addEventListener("click", () => {
    const d = document.querySelector("#sec-icars details");
    d.open = true;
    document.getElementById("sec-icars").scrollIntoView();
  });
  box.appendChild(reg);
  const add = document.createElement("button");
  add.type = "button";
  add.className = "small";
  add.textContent = "Add a part";
  add.addEventListener("click", () => {
    const d = document.querySelector("#sec-iparts details");
    d.open = true;
    document.getElementById("sec-iparts").scrollIntoView();
  });
  box.appendChild(add);
  const why = document.createElement("span");
  why.className = "hint";
  why.textContent = "Your parts cars and their parts: what you have, what fits, what it is worth.";
  box.appendChild(why);
  const tour = document.createElement("button");
  tour.type = "button";
  tour.className = "small primary";
  tour.textContent = "Take the tour";
  tour.addEventListener("click", () => startTour());
  box.appendChild(tour);
}

function renderBayHome() {
  const box = $("bayHome");
  if (!box) return;
  box.innerHTML = "";
  const strong = document.createElement("strong");
  strong.textContent = "Bay home";
  box.appendChild(strong);
  const span = document.createElement("span");
  if (bay.case && !bay.case.declined) {
    const done = bay.plan ? Object.keys(bay.plan.results).length : 0;
    const total = bay.plan ? bay.plan.tests.length : 0;
    span.textContent = "Case open: " + bay.case.vehicle.category + ", " + done + " of " + total + " recorded.";
  } else if (bay.case) {
    span.textContent = "Case declined. Start a new one below.";
  } else {
    span.textContent = "No case open. Start one below.";
  }
  box.appendChild(span);
  const fresh = document.createElement("button");
  fresh.type = "button";
  fresh.className = "small";
  fresh.textContent = "New case";
  fresh.addEventListener("click", () => document.getElementById("sec-bcase").scrollIntoView());
  box.appendChild(fresh);
  const kb = document.createElement("button");
  kb.type = "button";
  kb.className = "small";
  kb.textContent = "Knowledge base";
  kb.addEventListener("click", () => document.getElementById("sec-bkb").scrollIntoView());
  box.appendChild(kb);
  const why = document.createElement("span");
  why.className = "hint";
  why.textContent = "The repair bench: describe a symptom, get a test plan, record pass or fail.";
  box.appendChild(why);
  const tour = document.createElement("button");
  tour.type = "button";
  tour.className = "small primary";
  tour.textContent = "Take the tour";
  tour.addEventListener("click", () => startTour());
  box.appendChild(tour);
}

function renderGuide(boxId, mode, facts, title) {
  const box = $(boxId);
  box.innerHTML = "";
  if (UX.isGuideHidden(localStorage, mode)) return;
  const steps = UX.guideSteps(mode, facts);
  const card = document.createElement("div");
  card.className = "guide";
  card.innerHTML = "<h3>" + esc(title) + "</h3><ol>" + steps.map((s) =>
    "<li class='" + (s.done ? "done" : "") + "'>" + (s.done ? "✓ " : "") + esc(s.text) + "</li>"
  ).join("") + "</ol>";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "small";
  btn.textContent = steps.every((s) => s.done) ? "Done — dismiss" : "Dismiss walkthrough";
  btn.addEventListener("click", () => {
    UX.hideGuide(localStorage, mode);
    renderGuides();
  });
  card.appendChild(btn);
  box.appendChild(card);
}

function renderGuides() {
  renderGuide("bayGuide", "shop", {
    hasCase: !!(bay.case && !bay.case.declined),
    planTests: bay.plan ? bay.plan.tests.length : 0,
    results: bay.plan ? Object.keys(bay.plan.results).length : 0,
  }, "First task: open a case");
  renderGuide("invGuide", "enthusiast", {
    cars: invState.cars.length,
    parts: invState.parts.length,
    valued: invState.parts.filter((p) => p.value !== null && p.valueSource).length,
  }, "First task: register a parts car");
}

function markListingDemo() {
  const old = $("listingBadge");
  if (old) old.remove();
  if (isDemoMode(state.modes.listing)) {
    const badge = demoBadge();
    badge.id = "listingBadge";
    const card = $("listingCard");
    card.insertBefore(badge, card.firstChild);
  }
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
  state.modes.listing = res.mode;
  setPill();
  watchFallback(invSeeded, res.mode);
  if (res.notice) notice(esc(res.notice));
  $("listingCard").style.display = "";
  $("listingTitle").value = res.draft.title || "";
  $("listingDesc").value = res.draft.description || "";
  UX.clearDraft(localStorage, "listing");
  $("receipt").innerHTML = "";
  markListingDemo();
  $("cutoutSvg").innerHTML = "";
  $("cutoutNote").textContent = "Inventory draft: no photo cutout. Edit, Approve, then Post — nothing posts without approval.";
  renderStudio(res.studio, res.mode);
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
    scrollSoon($("invCars"));
    flash($("invCars"));
    $("invCarLabel").value = ""; $("invCarYear").value = "";
    $("invCarMake").value = ""; $("invCarModel").value = ""; $("invCarTrim").value = "";
    UX.clearDraft(localStorage, "invcar");
    feed("Registered " + added.car.label, "tool inv.register — " + added.car.identity.category);
  }));

  async function identifyInvCarPhoto() {
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
  }
  async function identifyInvCarPhotoStaged() {
    const file = ($("invCarPhoto").files || [])[0];
    let photo = null;
    if (file) { try { photo = await downscale(file); } catch (err) { photo = null; } }
    await withStages("identify", photo, async (tick) => {
      tick(0);
      await identifyInvCarPhoto();
      tick(1);
    });
  }
  $("btnInvCarPhoto").addEventListener("click", guard(identifyInvCarPhotoStaged, "identifying the picture…"));
  $("invCarPhoto").addEventListener("change", guard(async (e) => {
    if (!(e.target.files || []).length) return;
    await identifyInvCarPhotoStaged();
  }, "identifying the picture…"));

  async function readInvVin() {
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
  }
  async function readInvVinStaged() {
    await withStages("vin", $("invVinPlate").src || null, async (tick) => {
      tick(0);
      await readInvVin();
      tick(1);
    });
  }
  $("invCarVin").addEventListener("change", guard(async (e) => {
    const file = (e.target.files || [])[0];
    if (!file) { $("invVinRow").style.display = "none"; return; }
    $("invVinPlate").src = await downscale(file);
    $("invVinRow").style.display = "";
    await readInvVinStaged();
  }, "reading the plate…"));
  $("btnInvCarVin").addEventListener("click", guard(readInvVinStaged, "reading the plate…"));
  pressMic($("btnInvMic"), "inv", (res) => {
    const box = $("invPartNote");
    box.value = box.value ? box.value + " " + res.text : res.text;
    pokeDraft(box);
    feed("Voice note landed in the owner note", "tool voice.note — mic → text (" + res.mode + ")");
  });

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
    UX.clearDraft(localStorage, "invnote");
    feed("Knowledge note added", "tool inv.note — owner-supplied, car-pinned");
  }));

  async function describeInvPart() {
    const photo = await readPhotoInput($("invPartPhoto"));
    if (!photo) throw new Error("attach a part picture first");
    invPartPhotoData = photo.data; // owner's photo, kept in this browser only
    const res = await api("/api/inv/part-photo", { photo, demo: invSeeded });
    if (res.part.label) $("invPartLabel").value = res.part.label.replace(" (demo sample)", "");
    if (res.part.condition) $("invPartCond").value = res.part.condition;
    if (res.notice) notice(esc(res.notice));
    feed("Part picture described: " + res.part.label,
      "tool inv.part-photo — photo → label + condition (" + res.mode + ")");
  }
  async function describeInvPartStaged() {
    const file = ($("invPartPhoto").files || [])[0];
    let photo = null;
    if (file) { try { photo = await downscale(file); } catch (err) { photo = null; } }
    await withStages("part", photo, async (tick) => {
      tick(0);
      await describeInvPart();
      tick(1);
    });
  }
  $("btnInvPartPhoto").addEventListener("click", guard(describeInvPartStaged, "describing the picture…"));
  $("invPartPhoto").addEventListener("change", guard(async (e) => {
    if (!(e.target.files || []).length) return;
    await describeInvPartStaged();
  }, "describing the picture…"));

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
    let valueRaw = $("invPartValue").value.trim();
    let valueSource = $("invPartValue").dataset.source || "";
    const labelRaw = $("invPartLabel").value.trim();
    if (valueRaw === "" && labelRaw !== "") {
      // One tap saved: look up comps on attach. A miss stays unknown.
      try {
        const lookup = await api("/api/inv/comps", { label: labelRaw, demo: invSeeded });
        if (lookup.comp.value !== null && lookup.comp.source) {
          valueRaw = String(lookup.comp.value);
          valueSource = lookup.comp.source;
          $("invPartValue").value = valueRaw;
          feed("Comps filled about $" + valueRaw + " (" + valueSource + ")",
            "tool inv.comps — auto on attach (" + lookup.mode + ")");
        }
      } catch (err) {
        // Lookup failed: the part still attaches as unknown.
      }
    }
    const added = Inventory.attachPart(invState, {
      carId: $("invPartCar").value,
      relation: $("invPartRel").value,
      label: $("invPartLabel").value,
      condition: $("invPartCond").value,
      note: $("invPartNote").value,
      value: valueRaw === "" ? null : Number(valueRaw),
      valueSource: valueRaw === "" ? "" : (valueSource || "owner-entered"),
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
    UX.clearDraft(localStorage, "invpart");
    feed("Attached " + added.part.label + " to " + Inventory.carLabel(invState, added.part.carId),
      "tool inv.attach — part → car (" + added.part.relation + ")");
  }));
}

initIdentity();
initInventory();

/* ---------- usability: drafts, guides, paint every state ---------- */

function persistFields(key, ids) {
  const save = () => {
    const data = {};
    for (const id of ids) {
      const el = $(id);
      if (el) data[id] = el.value;
    }
    UX.saveDraft(localStorage, key, data);
  };
  for (const id of ids) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener("input", save);
    el.addEventListener("change", save);
  }
}

function restoreDraft(key, ids) {
  const data = UX.loadDraft(localStorage, key);
  if (!data) return;
  for (const id of ids) {
    const el = $(id);
    if (el && data[id] !== undefined) el.value = data[id];
  }
}

function initUx() {
  initMotion();
  updateOffline();
  // Paint every state on load so empties guide instead of blanking.
  renderViewer();
  renderPartList();
  renderVerdicts();
  renderBayCase();
  renderBayPlan();
  renderBayParts("");
  renderGuides();
  // Drafts: never eaten by a reload.
  persistFields("listing", ["listingTitle", "listingDesc"]);
  persistFields("baycase", ["bayYear", "bayMake", "bayModel", "bayTrim", "bayEngine", "bayArea", "bayService", "baySymptom", "bayCodes", "bayObs"]);
  persistFields("invcar", ["invCarLabel", "invCarYear", "invCarMake", "invCarModel", "invCarTrim"]);
  persistFields("invpart", ["invPartLabel", "invPartCond", "invPartNote", "invPartValue"]);
  persistFields("invnote", ["invKnowPart", "invKnowReason", "invKnowValue"]);
  persistFields("baytest", ["bayTTitle", "bayTWhat", "bayTHow", "bayTExp", "bayTCauses", "bayTOut", "bayTSusp"]);
  persistFields("baypart", ["bayPName", "bayPNote"]);
  restoreDraft("baycase", ["bayYear", "bayMake", "bayModel", "bayTrim", "bayEngine", "bayArea", "bayService", "baySymptom", "bayCodes", "bayObs"]);
  restoreDraft("invcar", ["invCarLabel", "invCarYear", "invCarMake", "invCarModel", "invCarTrim"]);
  restoreDraft("invpart", ["invPartLabel", "invPartCond", "invPartNote", "invPartValue"]);
  restoreDraft("invnote", ["invKnowPart", "invKnowReason", "invKnowValue"]);
  restoreDraft("baytest", ["bayTTitle", "bayTWhat", "bayTHow", "bayTExp", "bayTCauses", "bayTOut", "bayTSusp"]);
  restoreDraft("baypart", ["bayPName", "bayPNote"]);
  segify($("bayArea"));
  segify($("invPartRel"));
  sheetPicker($("listingPart"), "Pick a part");
  sheetPicker($("wonderPart"), "Ask about a part");
  sheetPicker($("invKnowCar"), "Car notes for");
  sheetPicker($("invPartCar"), "Attach to car");
  syncPickers();
  const savedListing = UX.loadDraft(localStorage, "listing");
  if (savedListing && (savedListing.listingTitle || savedListing.listingDesc)) {
    $("listingCard").style.display = "";
    $("listingTitle").value = savedListing.listingTitle || "";
    $("listingDesc").value = savedListing.listingDesc || "";
  }
  $("panelClose").addEventListener("click", () => $("panel").classList.remove("open"));
  $("btnDiscardDraft").addEventListener("click", () => {
    UX.guardedDelete(
      window.confirm.bind(window),
      "Discard this listing draft? Your last approved post stays put.",
      () => {
        $("listingCard").style.display = "none";
        $("listingTitle").value = "";
        $("listingDesc").value = "";
        $("receipt").innerHTML = "";
        state.draftId = null;
        UX.clearDraft(localStorage, "listing");
        markListingDemo();
        feed("Draft discarded", "listing — confirmed discard, approvals untouched");
      }
    );
  });
}

initUx();
