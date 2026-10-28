/* Node driver for the visual-layer suite (gallery model + overlay data).
 * Run directly with node, or through tests/test_visual.py.
 * Exits nonzero on the first failure. */
"use strict";

const fs = require("fs");
const path = require("path");
const Gallery = require("../web/gallery.js");

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

// ---- strip order follows walk-around order ----
const walk = [
  { name: "rear-3-4.jpg", src: "r" },
  { name: "front-left.jpg", src: "f" },
  { name: "side.jpg", src: "s" },
];
const strip = Gallery.stripModel(walk);
ok(strip.map((f) => f.name).join(",") === "rear-3-4.jpg,front-left.jpg,side.jpg",
  "gallery order matches walk-around order, never re-sorted");
ok(Gallery.selectFrame(walk, "side.jpg").name === "side.jpg", "strip selection picks the frame");
ok(Gallery.selectFrame(walk, "missing.jpg").name === "rear-3-4.jpg", "unknown selection falls back to first");
ok(Gallery.selectFrame([], "x") === null, "empty gallery selects nothing");

// ---- overlays and thumbs ----
const parts = [
  { id: "p1", sightings: [{ frame: "a", box: [1, 2, 3, 4], source_tag: "a" }] },
  { id: "p2", sightings: [{ frame: "b", box: [5, 6, 7, 8], source_tag: "b" }, { frame: "a", box: [1, 1, 2, 2], source_tag: "a" }] },
  { id: "p3", sightings: [] },
];
ok(Gallery.sightingsForFrame(parts, "a").length === 2, "viewer shows every sighting on its own frame");
ok(Gallery.sightingsForFrame(parts, "zzz").length === 0, "frames without sightings show none");
const thumb = Gallery.partThumb(parts[1]);
ok(thumb && thumb.frame === "b" && thumb.box.join(",") === "5,6,7,8",
  "part entry links to its source frame and box");
ok(Gallery.partThumb(parts[2]) === null, "part without sightings has no thumb link");
ok(Gallery.isDemoFrame("demo-frame-2") === true, "demo frames are flagged");
ok(Gallery.isDemoFrame("IMG_1234.jpg") === false, "user photos are not flagged as demo");

// ---- demo harvest: every entry has overlay coordinates on its frame ----
const harvest = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "demo_cache", "harvest.demo.json"), "utf-8"));
let sightingCount = 0;
let bad = 0;
for (const part of harvest.parts) {
  if (!part.sightings || !part.sightings.length) bad += 1;
  for (const s of part.sightings || []) {
    sightingCount += 1;
    if (!s.frame || !Array.isArray(s.box) || s.box.length !== 4 || !s.source_tag) bad += 1;
  }
}
ok(bad === 0 && sightingCount > 0, "every demo part has box coordinates on a tagged source frame");

// ---- VIN samples carry fields, never a VIN string ----
const seedRaw = fs.readFileSync(path.join(__dirname, "..", "demo_cache", "inv_seed.demo.json"), "utf-8");
const seed = JSON.parse(seedRaw);
ok(/"vin"\s*:/i.test(seedRaw) === false, "demo seed holds no VIN key anywhere");
for (const key of ["sampleIdentify", "sampleVin"]) {
  const sample = seed[key];
  ok(sample && sample.year && sample.make && sample.model && sample.trim,
    "VIN card sample '" + key + "' shows year, make, model, and trim");
}

if (!process.exitCode) console.log("ALL " + count + " VISUAL CHECKS PASSED");
