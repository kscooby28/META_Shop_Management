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

  return {
    saveDraft, loadDraft, clearDraft,
    guideKey, isGuideHidden, hideGuide, showGuide, guideSteps,
    emptyState, guardedDelete,
  };
})();

if (typeof module !== "undefined" && module.exports) module.exports = UX;
