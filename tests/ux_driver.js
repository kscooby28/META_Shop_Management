/* Node driver for the usability suite (drafts, guides, states, deletes).
 * Run directly with node, or through tests/test_ux.py.
 * Exits nonzero on the first failure. */
"use strict";

const fs = require("fs");
const path = require("path");
const UX = require("../web/ux.js");

let count = 0;
function ok(cond, name) {
  count += 1;
  if (!cond) {
    console.error("FAIL " + count + ": " + name);
    process.exitCode = 1;
  } else {
    console.log("ok " + count + " - " + name);
  }
}
function memStore(backing) {
  const data = backing || {};
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; },
  };
}

// ---- drafts survive a reload (new accessor, same backing) ----
const backing = {};
UX.saveDraft(memStore(backing), "listing", { title: "Used diff", description: "Works." });
const reloaded = UX.loadDraft(memStore(backing), "listing");
ok(reloaded && reloaded.title === "Used diff" && reloaded.description === "Works.",
  "draft text survives a reload");
UX.clearDraft(memStore(backing), "listing");
ok(UX.loadDraft(memStore(backing), "listing") === null, "cleared draft stays cleared");
ok(UX.loadDraft(memStore(), "missing") === null, "no draft reads as none, not an error");

// ---- guided tasks: dismiss once, never reappear ----
ok(UX.isGuideHidden(memStore(backing), "enthusiast") === false, "guide shows until dismissed");
UX.hideGuide(memStore(backing), "enthusiast");
ok(UX.isGuideHidden(memStore(backing), "enthusiast") === true, "dismissal persists across reloads");
UX.showGuide(memStore(backing), "enthusiast");
ok(UX.isGuideHidden(memStore(backing), "enthusiast") === false, "settings can bring the guide back");

const fanFresh = UX.guideSteps("enthusiast", { cars: 0, parts: 0, valued: 0 });
ok(fanFresh.length === 3 && fanFresh.every((s) => !s.done && s.text), "enthusiast guide has 3 plain steps");
const fanMid = UX.guideSteps("enthusiast", { cars: 2, parts: 1, valued: 0 });
ok(fanMid[0].done && fanMid[1].done && !fanMid[2].done, "enthusiast steps check off from real state");
const shopMid = UX.guideSteps("shop", { hasCase: true, planTests: 4, results: 0 });
ok(shopMid[0].done && shopMid[1].done && !shopMid[2].done, "shop steps check off from real state");

// ---- every empty state names a next action ----
for (const key of ["gallery", "parts", "verdicts", "baycase", "bayplan", "bayparts", "invcars", "invparts", "comps"]) {
  const card = UX.emptyState(key);
  ok(card.title && card.message && card.action, "empty state '" + key + "' has title, message, and action");
}
ok(UX.emptyState("nope").action === "Continue", "unknown states still offer a next action");

// ---- destructive actions require confirmation ----
let ran = 0;
let out = UX.guardedDelete(() => true, "Remove?", () => { ran += 1; return "gone"; });
ok(out.done && ran === 1, "confirmed delete acts");
out = UX.guardedDelete(() => false, "Remove?", () => { ran += 1; });
ok(!out.done && ran === 1, "cancelled delete does nothing");

// ---- navigation skeleton: doors point at views that exist, backs lead out ----
const html = fs.readFileSync(path.join(__dirname, "..", "web", "index.html"), "utf-8");
for (const pair of [["door-bay", "view-bay"], ["door-yard", "view-yard"], ["door-driveway", "view-inventory"], ["navHome", "view-home"]]) {
  ok(html.indexOf('id="' + pair[0] + '"') >= 0 && html.indexOf('id="' + pair[1] + '"') >= 0,
    "door '" + pair[0] + "' has its '" + pair[1] + "' view (a way there and back)");
}
for (const id of ["backYard", "backBay", "backInv", "backCompare", "btnCompareOpen", "navGear"]) {
  ok(html.indexOf('id="' + id + '"') >= 0, "navigation control '" + id + "' is on the page (never stranded)");
}
ok(html.indexOf('id="settings"') >= 0 && html.indexOf('id="setupOverlay"') >= 0,
  "settings and first-run setup are on the page");

if (!process.exitCode) console.log("ALL " + count + " UX CHECKS PASSED");
