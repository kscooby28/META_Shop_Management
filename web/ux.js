/* Usability state logic: drafts, guides, empty states, guarded deletes.
 * Pure functions over caller-provided storage; the page wires them to
 * localStorage and window.confirm. Usable under Node for tests. */
"use strict";

const UX = (() => {
  // ---- drafts: a draft is never eaten by a reload ----
  function saveDraft(storage, key, obj) {
    storage.setItem("copilot.draft." + key, JSON.stringify(obj || {}));
  }

  function loadDraft(storage, key) {
    try {
      const raw = storage.getItem("copilot.draft." + key);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (err) {
      return null;
    }
  }

  function clearDraft(storage, key) {
    storage.removeItem("copilot.draft." + key);
  }

  // ---- guided first tasks: dismissible, never reappearing ----
  function guideKey(mode) {
    return "copilot.guide." + mode;
  }

  function isGuideHidden(storage, mode) {
    return storage.getItem(guideKey(mode)) === "1";
  }

  function hideGuide(storage, mode) {
    storage.setItem(guideKey(mode), "1");
  }

  function showGuide(storage, mode) {
    storage.removeItem(guideKey(mode));
  }

  function guideSteps(mode, facts) {
    const f = facts || {};
    if (mode === "shop") {
      return [
        {
          id: "symptom",
          text: "Describe the symptom in your own words, so the plan starts from what you saw.",
          done: !!f.hasCase,
        },
        {
          id: "plan",
          text: "Draft the ranked plan, so every suspect has a test in order.",
          done: !!(f.planTests && f.planTests > 0),
        },
        {
          id: "record",
          text: "Record a pass or fail, so the plan re-ranks on evidence.",
          done: !!(f.results && f.results > 0),
        },
      ];
    }
    return [
      {
        id: "car",
        text: "Register a first parts car below, so the app knows what you own.",
        done: !!(f.cars && f.cars > 0),
      },
      {
        id: "part",
        text: "Attach a part with its honest condition, so you know what you have.",
        done: !!(f.parts && f.parts > 0),
      },
      {
        id: "worth",
        text: "Put a sourced value on it, so you know what it is worth.",
        done: !!(f.valued && f.valued > 0),
      },
    ];
  }

  // ---- empty states: every one names a next action ----
  const EMPTY = {
    gallery: {
      title: "No photos yet",
      message: "Upload walk-around photos or load the demo car to begin.",
      action: "Load demo car",
    },
    parts: {
      title: "No parts found yet",
      message: "Run Identify on your photos and the parts land here.",
      action: "Identify car",
    },
    verdicts: {
      title: "No verdicts yet",
      message: "Grade the harvest and every part gets its A, B, or C here.",
      action: "Run whole flow",
    },
    baycase: {
      title: "No case open",
      message: "Describe the symptom below and the case opens here.",
      action: "Create case",
    },
    bayplan: {
      title: "No plan yet",
      message: "Draft the plan and the ranked tests land here.",
      action: "Draft plan",
    },
    bayparts: {
      title: "No parts listed",
      message: "Add what the fix needs, one sourced entry at a time.",
      action: "Add part",
    },
    invcars: {
      title: "No cars yet",
      message: "Register your driver or a parts car to begin.",
      action: "Register a car",
    },
    invparts: {
      title: "No parts yet",
      message: "Photograph a part and attach it to its car.",
      action: "Add a part",
    },
    comps: {
      title: "No reliable value",
      message: "No comps back this one. Enter your own number or leave it unknown.",
      action: "Enter a value",
    },
  };

  function emptyState(key) {
    const found = EMPTY[key];
    if (!found) return { title: "Nothing here yet", message: "Take the next step below.", action: "Continue" };
    return { title: found.title, message: found.message, action: found.action };
  }

  // ---- destructive actions confirm first; confirmFn is stubbed in tests ----
  function guardedDelete(confirmFn, message, doFn) {
    let ok = false;
    try {
      ok = !!confirmFn(message);
    } catch (err) {
      ok = false;
    }
    if (!ok) return { done: false, reason: "cancelled" };
    return { done: true, result: doFn() };
  }

  // ---- motion system (WO18): one timing table, direction means something ----
  // Mirrors the :root tokens in styles.css; the Node driver pins the numbers.
  const Motion = {
    ease: "cubic-bezier(0.4, 0, 0.2, 1)",
    tapMs: 150,      // press feedback answers inside this
    doorMs: 150,     // door-to-door crossfade, never a slide
    pageMs: 300,     // full page transitions (300 sweet spot, 400 max)
    pageMaxMs: 400,
    sheetMs: 300,    // modal or sheet rises from the bottom
    flipMs: 300,     // Bay re-rank glide (250-350 window)
    flipMinMs: 250,
    flipMaxMs: 350,
    revealMs: 200,   // one reveal piece lands inside this
    revealStepMs: 120, // stagger between reveal pieces
    quietMs: 350,    // loading ladder: show nothing under this
    skeletonMs: 2000, // skeleton until this, staged text after
    maxMs: 1000,     // nothing functional ever runs longer
  };

  const DOOR_VIEWS = ["bay", "yard", "inventory"];

  // Deeper slides in from the right, back slides in from the left,
  // doors crossfade as equals, compare hangs under yard.
  function transitionFor(from, to) {
    if (!from || !to || from === to) return "none";
    const fromDoor = DOOR_VIEWS.indexOf(from) >= 0;
    const toDoor = DOOR_VIEWS.indexOf(to) >= 0;
    if (fromDoor && toDoor) return "door-fade";
    if (to === "compare" || from === "home") return "page-in-right";
    if (from === "compare" || to === "home") return "page-in-left";
    return "door-fade";
  }

  // ---- staged analysis (WO18): the photo stays on screen, steps tick off ----
  const STAGES = {
    yard: ["Reading photo…", "Identifying…", "Checking sold prices…", "Deciding…"],
    identify: ["Reading photo…", "Identifying…"],
    vin: ["Reading the plate…", "Matching the vehicle…"],
    part: ["Reading photo…", "Describing the part…"],
  };

  function stagesFor(flow) {
    return (STAGES[flow] || STAGES.yard).slice();
  }

  // Result reveal order: answer first, then evidence. Never evidence first.
  function revealOrder() {
    return ["what", "worth", "next", "details"];
  }

  // ---- camera confirm (WO18): guide before capture, confirm after ----
  const SHOTS = {
    hero: { mode: "whole", guide: "Get the whole car in the frame." },
    yard: { mode: "whole", guide: "Get the whole car in the frame." },
    carphoto: { mode: "whole", guide: "Get the whole car in the frame." },
    bayvin: { mode: "part", guide: "Get the VIN plate sharp and readable." },
    carvin: { mode: "part", guide: "Get the VIN plate sharp and readable." },
    part: { mode: "part", guide: "Get the badge or label in the shot." },
  };
  const MODE_LABELS = { whole: "Whole car", part: "Single part" };

  function guideFor(shot) {
    const found = SHOTS[shot] || SHOTS.yard;
    return { mode: found.mode, modeLabel: MODE_LABELS[found.mode], guide: found.guide };
  }

  function captureModes() {
    return [
      { id: "whole", label: MODE_LABELS.whole, blurb: "Walk-around strip, multiple angles." },
      { id: "part", label: MODE_LABELS.part, blurb: "Close-up plus a label shot." },
    ];
  }

  // ---- failure lines (WO18): specific fixes, never generic errors ----
  const FAILURES = {
    blur: "Too blurry to read. Move closer and hold steady, then retake.",
    cropped: "The important part is cut off. Step back so the whole thing fits, then retake.",
    glare: "Glare is washing it out. Angle away from the sun or shade the shot, then retake.",
    subject: "No car or part found in that shot. Get the subject in the frame and retake.",
    low: "Not sure enough to call it — nothing here is a guess. Retake with the guide, or keep it unknown.",
    retry: "That shot did not go through. Check the connection and try again — your photo is saved with the draft.",
  };

  function failureLine(kind) {
    return FAILURES[kind] || FAILURES.retry;
  }

  function failureKinds() {
    return ["blur", "cropped", "glare", "subject", "low", "retry"];
  }

  function classifyFailure(message) {
    const text = (message || "").toLowerCase();
    if (/blur|shak|focus|steady/.test(text)) return "blur";
    if (/crop|cut off|edge of|out of frame/.test(text)) return "cropped";
    if (/glar|wash|bright|sun/.test(text)) return "glare";
    if (/confiden|unsure|uncertain|ambiguous/.test(text)) return "low";
    if (/no car|no part|not found|unknown|identify|identify the|read the|attach|select a|empty/.test(text)) return "subject";
    return "retry";
  }

  // ---- sunlight mode (WO18): browser-local, like the profile ----
  const SUN_KEY = "copilot.sunlight";

  function loadSunlight(storage) {
    try {
      return storage.getItem(SUN_KEY) === "1";
    } catch (err) {
      return false;
    }
  }

  function saveSunlight(storage, on) {
    storage.setItem(SUN_KEY, on ? "1" : "0");
    return !!on;
  }

  return {
    saveDraft, loadDraft, clearDraft,
    guideKey, isGuideHidden, hideGuide, showGuide, guideSteps,
    emptyState, guardedDelete,
    Motion, transitionFor, stagesFor, revealOrder,
    guideFor, captureModes, failureLine, failureKinds, classifyFailure,
    SUN_KEY, loadSunlight, saveSunlight,
  };
})();

if (typeof module !== "undefined" && module.exports) module.exports = UX;
