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

// ---- motion timings (WO18): one table, hard limits ----
const M = UX.Motion;
ok(M.ease === "cubic-bezier(0.4, 0, 0.2, 1)", "easing is Material standard, never linear");
ok(M.tapMs <= 200 && M.doorMs === 150, "tap feedback and door crossfade answer fast");
ok(M.pageMs >= 300 && M.pageMs <= M.pageMaxMs && M.pageMaxMs <= 400,
  "page transitions run 300-400ms, sweet spot 300");
ok(M.flipMs >= M.flipMinMs && M.flipMs <= M.flipMaxMs && M.flipMinMs >= 250 && M.flipMaxMs <= 350,
  "Bay re-rank FLIP glides inside 250-350ms");
ok(M.revealMs <= 200 && M.revealStepMs * 4 + M.revealMs <= M.maxMs,
  "staged reveal lands every piece inside the 1000ms ceiling");
ok(M.quietMs >= 300 && M.quietMs <= 400 && M.skeletonMs === 2000,
  "loading ladder: quiet under ~350ms, skeleton to 2s, staged text after");
for (const k of ["tapMs", "doorMs", "pageMs", "pageMaxMs", "sheetMs", "flipMs",
                 "flipMinMs", "flipMaxMs", "revealMs", "revealStepMs"]) {
  ok(M[k] <= M.maxMs, "motion token '" + k + "' (" + M[k] + "ms) is under the 1000ms ceiling");
}

// ---- direction means something (WO18) ----
ok(UX.transitionFor("bay", "yard") === "door-fade", "door to door crossfades, never slides");
ok(UX.transitionFor("inventory", "bay") === "door-fade", "doors are equals in both directions");
ok(UX.transitionFor("home", "yard") === "page-in-right", "going deeper slides in from the right");
ok(UX.transitionFor("yard", "compare") === "page-in-right", "compare hangs under yard, deeper");
ok(UX.transitionFor("yard", "home") === "page-in-left", "going back slides in from the left");
ok(UX.transitionFor("compare", "yard") === "page-in-left", "compare backtracks to the left");
ok(UX.transitionFor("yard", "yard") === "none", "same view plays no transition");

// ---- staged analysis (WO18): plain words, answer first ----
for (const flow of ["yard", "identify", "vin", "part"]) {
  const steps = UX.stagesFor(flow);
  ok(steps.length >= 2 && steps.every((s) => typeof s === "string" && s.length > 4 && s.indexOf("…") >= 0),
    "flow '" + flow + "' ticks plain-words stages");
}
ok(UX.stagesFor("yard")[0] === "Reading photo…", "yard stages start with the photo");
const reveal = UX.revealOrder();
ok(JSON.stringify(reveal) === JSON.stringify(["what", "worth", "next", "details"]),
  "result reveals answer first, then evidence, never evidence first");

// ---- camera guides (WO18): one line per shot, two labeled modes ----
const modes = UX.captureModes();
ok(modes.length === 2 && modes[0].label === "Whole car" && modes[1].label === "Single part",
  "two capture modes, labeled in plain words");
for (const shot of ["hero", "yard", "carphoto", "bayvin", "carvin", "part"]) {
  const g = UX.guideFor(shot);
  ok(g.guide && g.guide.split(".").length <= 2, "shot '" + shot + "' has one guide line");
  ok(g.modeLabel === "Whole car" || g.modeLabel === "Single part",
    "shot '" + shot + "' names its capture mode");
}
ok(UX.guideFor("part").guide.indexOf("badge or label") >= 0, "part guide names the badge or label");
ok(UX.guideFor("yard").mode === "whole", "walk-around is whole-car mode");
ok(UX.guideFor("bayvin").mode === "part", "VIN plate is a single-part label shot");

// ---- failure lines (WO18): specific fixes, never generic, never a guess ----
for (const kind of UX.failureKinds()) {
  const line = UX.failureLine(kind);
  ok(line && line.length > 20 && /retake|try again|keep it unknown/i.test(line),
    "failure '" + kind + "' names a specific fix");
}
ok(UX.failureLine("low").indexOf("nothing here is a guess") >= 0,
  "low confidence never presents a guessed answer as fact");
ok(UX.failureLine("low").indexOf("keep it unknown") >= 0,
  "low confidence offers keeping it unknown");
ok(UX.classifyFailure("too blurry") === "blur", "blur signal maps to the blur fix");
ok(UX.classifyFailure("subject cropped at the edge of frame") === "cropped", "crop signal maps to the crop fix");
ok(UX.classifyFailure("glare washed out") === "glare", "glare signal maps to the glare fix");
ok(UX.classifyFailure("no car found") === "subject", "empty result maps to the no-subject fix");
ok(UX.classifyFailure("low confidence match") === "low", "uncertainty maps to low, never a guess");
ok(UX.classifyFailure("Failed to fetch") === "retry", "unknown errors map to retry, photo saved");
ok(UX.classifyFailure("attach a picture first") === "subject", "missing file maps to the no-subject fix");

// ---- sunlight mode (WO18): browser-local, like the profile ----
ok(UX.SUN_KEY === "copilot.sunlight", "sunlight state has its own local key");
const sunBacking = {};
ok(UX.loadSunlight(memStore(sunBacking)) === false, "sunlight defaults off");
UX.saveSunlight(memStore(sunBacking), true);
ok(UX.loadSunlight(memStore(sunBacking)) === true, "sunlight toggle persists across reloads");
UX.saveSunlight(memStore(sunBacking), false);
ok(UX.loadSunlight(memStore(sunBacking)) === false, "sunlight toggles back off");

if (!process.exitCode) console.log("ALL " + count + " UX CHECKS PASSED");
