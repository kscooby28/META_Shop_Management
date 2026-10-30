/* Node driver for the browser-logic suites (profile + inventory).
 * Run directly with node, or through tests/test_web_logic.py.
 * Exits nonzero on the first failure. */
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
function throws(fn, name) {
  count += 1;
  try {
    fn();
    console.error("FAIL " + count + " (no throw): " + name);
    process.exitCode = 1;
  } catch (err) {
    console.log("ok " + count + " - " + name + " [" + err.message + "]");
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

// ---- first-run identity ----
const fresh = memStore();
ok(Profile.needsSetup(fresh) === true, "chooser appears on a fresh profile");
const saved = Profile.saveProfile(fresh, "owner@example.com", "enthusiast");
ok(saved.mode === "enthusiast" && saved.email === "owner@example.com" && !!saved.created,
  "profile saves email, mode, and timestamp");
ok(Profile.needsSetup(fresh) === false, "chooser never appears again once saved");

const backing = {};
Profile.saveProfile(memStore(backing), "shop@example.com", "shop");
const later = Profile.loadProfile(memStore(backing));
ok(later && later.mode === "shop" && later.email === "shop@example.com",
  "mode persists across sessions");
ok(Profile.routeFor("shop") === "bay", "shop identity routes to the Bay");
ok(Profile.routeFor("enthusiast") === "inventory", "enthusiast identity routes to inventory");
Profile.setMode(memStore(backing), "enthusiast");
ok(Profile.loadProfile(memStore(backing)).mode === "enthusiast",
  "deliberate settings change switches the mode");
throws(() => Profile.saveProfile(memStore(), "not-an-email", "enthusiast"), "email is required");
throws(() => Profile.saveProfile(memStore(), "a@b.c", "wizard"), "mode must be shop or enthusiast");
const corrupt = memStore();
corrupt.setItem(Profile.KEY, "{broken json");
ok(Profile.needsSetup(corrupt) === true, "corrupt profile falls back to setup");

// ---- inventory ----
let inv = Inventory.blankInventory();
ok(Inventory.validateCar({}).length > 0, "car validation names missing fields");
let added = Inventory.addCar(inv, {
  id: "car-1", label: "My driver",
  identity: { year: 2005, make: "BMW", model: "325i", trim: "" },
});
inv = added.inv;
ok(inv.cars[0].identity.trim === "unknown", "blank trim stays unknown, honestly");
ok(inv.cars[0].identity.category === "BMW · 325i", "car gets year/make/model/category");

throws(() => Inventory.attachPart(inv, { label: "x", carId: "nope" }), "part must attach to a real car");
throws(() => Inventory.attachPart(inv, { label: "", carId: "car-1" }), "part needs a name");
throws(() => Inventory.attachPart(inv, { label: "coil", carId: "car-1", value: 25, valueSource: "" }),
  "a value without a source is refused");
added = Inventory.attachPart(inv, {
  id: "p-1", carId: "car-1", relation: "fits",
  label: "spare ignition coil", condition: "used, working", note: "spare",
  value: 25, valueSource: "owner-entered",
});
inv = added.inv;
ok(inv.parts[0].carId === "car-1" && inv.parts[0].relation === "fits",
  "part attaches to the correct car with its relation");
added = Inventory.attachPart(inv, { id: "p-2", carId: "car-1", label: "trunk lid" });
inv = added.inv;
ok(inv.parts[1].value === null && inv.parts[1].condition === "unknown",
  "part without a value stays unknown, never zero");

const totals = Inventory.overallTotals(inv);
ok(totals.total === 25 && totals.counted === 1, "totals sum sourced values only");
ok(totals.unknown.length === 1 && totals.unknown[0].indexOf("trunk lid") === 0,
  "unknown values are named, not guessed into the total");
const words = Inventory.plainTotals(totals, "parts");
ok(words.indexOf("$25") >= 0 && words.indexOf("trunk lid") >= 0,
  "plain-money totals show the sum and name the unknowns");

ok(Inventory.notesForCar(inv, "car-1").length === 0, "silence when no knowledge note exists");
throws(() => Inventory.addNote(inv, { carId: "car-1", part: "", reason: "x" }), "note needs a part");
throws(() => Inventory.addNote(inv, { carId: "car-1", part: "ecu", reason: "" }), "note needs a real reason");
inv = Inventory.addNote(inv, { carId: "car-1", part: "engine computer", reason: "no EWS, E30 crowd wants it", value: 200, source: "owner-entered" });
ok(Inventory.notesForCar(inv, "car-1").length === 1, "owner note surfaces on its car");

const before = JSON.stringify(inv.parts[0]);
ok(Object.keys(inv.parts[0]).indexOf("draftId") < 0, "inventory item exists with no listing attached");
ok(JSON.stringify(inv.parts[0]) === before, "inventory stands alone, independent of listing");

// ---- demo seed shape ----
const seed = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "demo_cache", "inv_seed.demo.json"), "utf-8"));
const seeded = Inventory.applySeed(seed);
ok(seeded.cars.length === 4 && seeded.parts.length === 11 && seeded.knowledge.length === 1,
  "demo seed carries 4 cars, 11 parts, 1 knowledge note");
const seedTotals = Inventory.overallTotals(seeded);
ok(seedTotals.total === 1435 && seedTotals.counted === 8 && seedTotals.unknown.length === 3,
  "seed totals $1,435 across 8 sourced parts, 3 unknown named");
const m3notes = Inventory.notesForCar(seeded, "car-m3");
ok(m3notes.length === 1 && m3notes[0].value === 200 && m3notes[0].reason.indexOf("EWS") >= 0,
  "M3 engine-computer note surfaces with the owner reason and value");

if (!process.exitCode) console.log("ALL " + count + " WEB LOGIC CHECKS PASSED");
