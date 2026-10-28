/* Node driver for the video-spine journey, enthusiast half (WO6).
 * Beats run in the order the video walks them: first-run, home route,
 * seed + register, look-for moment, totals, reopen. The shop half
 * (Bay case, re-rank, decline, close) and the listing gate run in
 * tests/test_spine.py against the server modules. Exits nonzero
 * on the first failure. */
"use strict";

const fs = require("fs");
const path = require("path");
const Profile = require("../web/profile.js");
const Inventory = require("../web/inventory.js");

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

// Beat 1: first-run setup asks once, then routes to the enthusiast home.
const backing = {};
const firstOpen = memStore(backing);
ok(Profile.needsSetup(firstOpen) === true, "spine: chooser appears on first run");
Profile.saveProfile(firstOpen, "owner@example.com", "enthusiast");
ok(Profile.needsSetup(firstOpen) === false, "spine: chooser never appears again");
ok(Profile.routeFor("enthusiast") === "inventory", "spine: enthusiast routes to inventory home");

// Beat 2: the demo seed carries the video's cars.
const seedPath = path.join(__dirname, "..", "demo_cache", "inv_seed.demo.json");
const seed = JSON.parse(fs.readFileSync(seedPath, "utf8"));
let inv = Inventory.applySeed(seed);
ok(inv.cars.length === 4, "spine: demo seed holds 4 cars");
const m3 = inv.cars.find((c) => c.id === "car-m3");
ok(!!m3 && /m3/i.test(m3.label), "spine: M3 parts car is in the seed");

// Beat 3: registering a car by hand adds to the same inventory.
const added = Inventory.addCar(inv, {
  label: "Spine donor",
  identity: { year: "1998", make: "BMW", model: "328i", trim: "" },
  source_tags: ["owner-entered"],
});
inv = added.inv;
ok(inv.cars.length === 5 && added.car.identity.category === "BMW · 328i",
  "spine: manual registration lands with an honest category");

// Beat 4: the what-to-look-for moment, from the owner's note only.
const notes = Inventory.notesForCar(inv, "car-m3");
ok(notes.length === 1, "spine: M3 carries exactly one knowledge note");
ok(notes[0].part === "engine computer" && notes[0].value === 200 &&
  /ews/i.test(notes[0].reason),
  "spine: note names the engine computer, $200, no EWS");
ok(Inventory.notesForCar(inv, added.car.id).length === 0,
  "spine: a car with no note surfaces nothing, invents nothing");

// Beat 5: totals count sourced values and name the unknowns.
const before = Inventory.overallTotals(inv);
ok(before.total > 0 && before.counted > 0, "spine: demo totals are plain sourced money");
const withUnknown = Inventory.attachPart(inv, {
  carId: added.car.id, relation: "came from", label: "mystery bracket",
  condition: "unknown", note: "", value: null, valueSource: "",
  source_tags: ["owner-entered"],
});
inv = withUnknown.inv;
const after = Inventory.overallTotals(inv);
ok(after.total === before.total && after.counted === before.counted,
  "spine: an unknown value never leaks into the total");
ok(after.unknown.length === before.unknown.length + 1 &&
  /mystery bracket/.test(after.unknown.join(" ")),
  "spine: the unknown part is named as unknown");
ok(/\$/.test(Inventory.plainTotals(after, "parts")), "spine: totals read in plain money");

// Beat 6: reopening keeps the identity; the chooser stays away.
const later = memStore(backing);
ok(Profile.needsSetup(later) === false, "spine: later opens skip the chooser");
ok(Profile.loadProfile(later).mode === "enthusiast", "spine: enthusiast identity persists");

console.log("ALL " + count + " spine checks passed");
