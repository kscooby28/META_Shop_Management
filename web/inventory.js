/* Enthusiast inventory: pure state logic. The browser owns the data;
 * the server only identifies photos and serves the demo seed.
 * Usable both as a browser global and under Node for tests. */
"use strict";

const Inventory = (() => {
  function blankInventory() {
    return { cars: [], parts: [], knowledge: [] };
  }

  function newId(prefix) {
    return prefix + "-" + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
  }

  function validateCar(car) {
    const problems = [];
    if (!car || !(car.label || "").trim()) problems.push("name the car (driver, parts car 1, …)");
    const identity = (car && car.identity) || {};
    if (!identity.year) problems.push("add the model year");
    if (!(identity.make || "").trim()) problems.push("add the make");
    if (!(identity.model || "").trim()) problems.push("add the model");
    return problems;
  }

  function addCar(inv, car) {
    const problems = validateCar(car);
    if (problems.length) throw new Error(problems.join("; "));
    const entry = {
      id: car.id || newId("car"),
      label: car.label.trim(),
      identity: {
        year: car.identity.year,
        make: car.identity.make.trim(),
        model: car.identity.model.trim(),
        trim: (car.identity.trim || "").trim() || "unknown",
        category: (car.identity.make.trim() + " · " + car.identity.model.trim()),
      },
      source_tags: car.source_tags && car.source_tags.length ? car.source_tags : ["owner-entered"],
    };
    return { inv: { cars: inv.cars.concat([entry]), parts: inv.parts, knowledge: inv.knowledge }, car: entry };
  }

  function validatePart(inv, part) {
    const problems = [];
    if (!part || !(part.label || "").trim()) problems.push("name the part");
    if (!part || !part.carId || !inv.cars.some((c) => c.id === part.carId)) {
      problems.push("attach the part to one of your cars");
    }
    if (part && part.value !== null && part.value !== undefined && part.value !== "") {
      if (isNaN(Number(part.value)) || Number(part.value) < 0) {
        problems.push("the value must be a positive number or left blank");
      } else if (!((part.valueSource || "").trim())) {
        problems.push("a value needs a source (comps or owner-entered)");
      }
    }
    return problems;
  }

  function attachPart(inv, part) {
    const problems = validatePart(inv, part);
    if (problems.length) throw new Error(problems.join("; "));
    const hasValue = part.value !== null && part.value !== undefined && part.value !== "";
    const entry = {
      id: part.id || newId("ip"),
      carId: part.carId,
      relation: part.relation === "fits" ? "fits" : "came from",
      label: part.label.trim(),
      condition: (part.condition || "").trim() || "unknown",
      note: (part.note || "").trim(),
      value: hasValue ? Number(part.value) : null,
      valueSource: hasValue ? part.valueSource.trim() : "",
      source_tags: part.source_tags && part.source_tags.length ? part.source_tags : ["owner-entered"],
    };
    return { inv: { cars: inv.cars, parts: inv.parts.concat([entry]), knowledge: inv.knowledge }, part: entry };
  }

  function setPartValue(inv, partId, value, source) {
    const parts = inv.parts.map((p) => {
      if (p.id !== partId) return p;
      if (value === null || value === undefined || value === "") {
        return Object.assign({}, p, { value: null, valueSource: "" });
      }
      if (isNaN(Number(value)) || Number(value) < 0) throw new Error("the value must be a positive number");
      if (!(source || "").trim()) throw new Error("a value needs a source");
      return Object.assign({}, p, { value: Number(value), valueSource: source.trim() });
    });
    return { cars: inv.cars, parts, knowledge: inv.knowledge };
  }

  function carLabel(inv, carId) {
    const car = inv.cars.find((c) => c.id === carId);
    return car ? car.label : "unknown car";
  }

  function carTotals(inv, carId) {
    const mine = inv.parts.filter((p) => p.carId === carId);
    const priced = mine.filter((p) => p.value !== null && p.valueSource);
    return {
      total: priced.reduce((sum, p) => sum + p.value, 0),
      counted: priced.length,
      unknown: mine.filter((p) => !(p.value !== null && p.valueSource)).map((p) => p.label),
    };
  }

  function overallTotals(inv) {
    const priced = inv.parts.filter((p) => p.value !== null && p.valueSource);
    return {
      total: priced.reduce((sum, p) => sum + p.value, 0),
      counted: priced.length,
      unknown: inv.parts
        .filter((p) => !(p.value !== null && p.valueSource))
        .map((p) => p.label + " (" + carLabel(inv, p.carId) + ")"),
    };
  }

  function plainTotals(totals, what) {
    let line;
    if (totals.counted === 0) {
      line = "No " + what + " has a sourced value yet, so there is no total.";
    } else if (totals.counted === 1) {
      line = "About $" + totals.total + " across 1 part with a sourced value.";
    } else {
      line = "About $" + totals.total + " across " + totals.counted + " parts with sourced values.";
    }
    if (totals.unknown.length) {
      line += " Unknown and left out: " + totals.unknown.join("; ") + ".";
    }
    return line;
  }

  function notesForCar(inv, carId) {
    return inv.knowledge.filter((n) => n.carId === carId);
  }

  function addNote(inv, note) {
    if (!note || !note.carId || !inv.cars.some((c) => c.id === note.carId)) {
      throw new Error("pin the note to one of your cars");
    }
    if (!(note.part || "").trim()) throw new Error("name the part to look for");
    if (!(note.reason || "").trim()) throw new Error("say why it is worth pulling (never invent a reason)");
    if (note.value !== null && note.value !== undefined && note.value !== "") {
      if (isNaN(Number(note.value)) || Number(note.value) < 0) throw new Error("the note value must be positive");
      if (!(note.source || "").trim()) throw new Error("a note value needs a source");
    }
    const entry = {
      carId: note.carId,
      part: note.part.trim(),
      reason: note.reason.trim(),
      value: note.value === "" || note.value === null || note.value === undefined ? null : Number(note.value),
      source: (note.source || "").trim() || "owner-entered",
    };
    return { cars: inv.cars, parts: inv.parts, knowledge: inv.knowledge.concat([entry]) };
  }

  function applySeed(seed) {
    const inv = blankInventory();
    for (const car of (seed && seed.cars) || []) {
      const problems = validateCar(car);
      if (problems.length) throw new Error("seed car invalid: " + problems.join("; "));
      inv.cars.push({
        id: car.id,
        label: car.label,
        identity: {
          year: car.identity.year,
          make: car.identity.make,
          model: car.identity.model,
          trim: car.identity.trim || "unknown",
          category: car.identity.category || (car.identity.make + " · " + car.identity.model),
        },
        source_tags: car.source_tags || ["demo-seed"],
      });
    }
    for (const part of (seed && seed.parts) || []) {
      const problems = validatePart(inv, part);
      if (problems.length) throw new Error("seed part invalid: " + problems.join("; "));
      inv.parts.push({
        id: part.id,
        carId: part.carId,
        relation: part.relation === "fits" ? "fits" : "came from",
        label: part.label,
        condition: part.condition || "unknown",
        note: part.note || "",
        value: part.value === null || part.value === undefined ? null : Number(part.value),
        valueSource: part.valueSource || "",
        source_tags: part.source_tags || ["demo-seed"],
      });
    }
    for (const note of (seed && seed.knowledge) || []) {
      inv.knowledge.push({
        carId: note.carId,
        part: note.part,
        reason: note.reason,
        value: note.value === null || note.value === undefined ? null : Number(note.value),
        source: note.source || "demo-sample",
      });
    }
    return inv;
  }

  return {
    blankInventory, newId, validateCar, addCar, validatePart, attachPart,
    setPartValue, carLabel, carTotals, overallTotals, plainTotals,
    notesForCar, addNote, applySeed,
  };
})();

if (typeof module !== "undefined" && module.exports) module.exports = Inventory;
