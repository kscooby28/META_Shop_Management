/* Credentials settings + mock integrations (WO15): local-only, mock by design.
 *
 * Two profiles: shop (distributor login + email API credential) and DIY
 * (parts-store login + marketplace accounts incl. the eBay developer slot).
 * Values live in the browser store only, next to the first-run profile, and
 * are NEVER sent anywhere: this file makes zero network calls (no fetch, no
 * XHR, no sockets), the server has no credential endpoint, and the UI shows
 * presence only — set or not set, never the value.
 *
 * Every adapter below is a MOCK in the shape of the real API so the demo can
 * walk the loop honestly: picture, analyze, value new-vs-used, draft, human
 * Approve tap, API posts. Mock results are always labeled demo. Automatic
 * means the API does the posting work after the human tap — nothing posts
 * without approval, ever, and mockEbayPost throws without one.
 *
 * Pure functions over a storage-like {getItem, setItem, removeItem}.
 * Usable both as a browser global and under Node for tests. */
"use strict";

const Credentials = (() => {
  const KEY = "copilot.credentials";

  const PROFILES = {
    shop: [
      { field: "distributorUser", label: "Distributor username" },
      { field: "distributorPass", label: "Distributor password", secret: true },
      { field: "emailApiKey", label: "Email API credential", secret: true },
    ],
    diy: [
      { field: "storeUser", label: "Parts-store username" },
      { field: "storePass", label: "Parts-store password", secret: true },
      { field: "ebayDevKey", label: "eBay developer key", secret: true },
      { field: "ebayAuth", label: "eBay account authorization", secret: true },
    ],
  };

  // Mock new-price book: openly fiction for the mock demo, never a price
  // claim. Anything not on the book reads unknown — never guessed.
  const MOCK_NEW_PRICES = {
    "driver mirror": 120,
    "rear differential": 1400,
    "alloy wheel": 210,
    "engine computer": 650,
    "driver headlight": 180,
    "spare ignition coil": 60,
  };
  const MOCK_SOURCE = "demo-mock: fiction for the mock demo, not a price";

  function blankStore() {
    return { shop: {}, diy: {} };
  }

  function loadCreds(storage) {
    try {
      const raw = storage.getItem(KEY);
      if (!raw) return blankStore();
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return blankStore();
      return {
        shop: parsed.shop && typeof parsed.shop === "object" ? parsed.shop : {},
        diy: parsed.diy && typeof parsed.diy === "object" ? parsed.diy : {},
      };
    } catch (err) {
      return blankStore();
    }
  }

  function saveCreds(storage, profile, fields) {
    if (!PROFILES[profile]) throw new Error("unknown profile: " + profile);
    const creds = loadCreds(storage);
    const slot = creds[profile];
    for (const spec of PROFILES[profile]) {
      const value = (fields[spec.field] || "").trim();
      if (value) slot[spec.field] = value;
      else delete slot[spec.field];
    }
    storage.setItem(KEY, JSON.stringify(creds));
    return presence(storage, profile);
  }

  function clearCreds(storage, profile) {
    if (!PROFILES[profile]) throw new Error("unknown profile: " + profile);
    const creds = loadCreds(storage);
    creds[profile] = {};
    storage.setItem(KEY, JSON.stringify(creds));
  }

  // Presence only: { field: true/false }. Values never leave this module
  // except into the browser store. Anything rendering credentials must use
  // this, never loadCreds.
  function presence(storage, profile) {
    if (!PROFILES[profile]) throw new Error("unknown profile: " + profile);
    const slot = loadCreds(storage)[profile];
    const out = {};
    for (const spec of PROFILES[profile]) {
      out[spec.field] = !!(slot[spec.field] || "").trim();
    }
    return out;
  }

  function presenceLines(storage) {
    const lines = [];
    for (const profile of Object.keys(PROFILES)) {
      const got = presence(storage, profile);
      for (const spec of PROFILES[profile]) {
        lines.push({
          profile,
          label: spec.label,
          set: got[spec.field],
          text: spec.label + ": " + (got[spec.field] ? "set" : "not set"),
        });
      }
    }
    return lines;
  }

  function _slot(storage, profile) {
    return loadCreds(storage)[profile];
  }

  function mockDistributorLogin(storage) {
    const slot = _slot(storage, "shop");
    if (!(slot.distributorUser || "").trim() || !(slot.distributorPass || "").trim()) {
      throw new Error("add your distributor login in settings first (demo mock: nothing is checked anywhere)");
    }
    return {
      demo: true,
      supplier: "Mock Distributor (demo)",
      account: "demo account (username withheld: presence only)",
      sessionId: "mock-distributor-session",
      note: "Mock login in the shape of a real supplier login. No network, no check, demo only.",
    };
  }

  function mockStoreLogin(storage) {
    const slot = _slot(storage, "diy");
    if (!(slot.storeUser || "").trim() || !(slot.storePass || "").trim()) {
      throw new Error("add your parts-store login in settings first (demo mock: nothing is checked anywhere)");
    }
    return {
      demo: true,
      store: "Mock Parts Store (demo)",
      account: "demo account (username withheld: presence only)",
      sessionId: "mock-store-session",
      note: "Mock login in the shape of a parts-store website login. No network, no check, demo only.",
    };
  }

  function mockNewPrice(label) {
    const name = (label || "").trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(MOCK_NEW_PRICES, name)) {
      return {
        known: true,
        demo: true,
        label: (label || "").trim(),
        newPrice: MOCK_NEW_PRICES[name],
        source: MOCK_SOURCE,
      };
    }
    return {
      known: false,
      demo: true,
      label: (label || "").trim(),
      note: "No mock new price for this part. Unknown is unknown — never guessed.",
    };
  }

  // Mock eBay Developer API post: draft + human approval + the user's own
  // developer key and account authorization. The approval is the same human
  // tap the listing card already requires; without it this throws and
  // nothing posts. Returns a mock listing plus the mock cha-ching.
  function mockEbayPost({ draft, approval, storage }) {
    if (!approval || approval.approved !== true) {
      throw new Error("approve the listing first — nothing posts without your tap, not even the mock");
    }
    const slot = _slot(storage, "diy");
    const missing = [];
    if (!(slot.ebayDevKey || "").trim()) missing.push("eBay developer key");
    if (!(slot.ebayAuth || "").trim()) missing.push("eBay account authorization");
    if (missing.length) {
      throw new Error("add " + missing.join(" and ") + " in settings first (demo mock: presence only, values stay here)");
    }
    const title = (draft && draft.title) || "mock listing";
    return {
      demo: true,
      adapter: "mock-ebay-developer-api",
      listing: {
        id: "mock-ebay-" + Date.now(),
        title,
        status: "listed (demo mock)",
      },
      chaching: "Cha-ching (demo mock): a buyer just paid for '" + title + "'. None of this is real — the loop is the demo.",
    };
  }

  return {
    KEY, PROFILES,
    loadCreds, saveCreds, clearCreds, presence, presenceLines,
    mockDistributorLogin, mockStoreLogin, mockNewPrice, mockEbayPost,
  };
})();

if (typeof module !== "undefined" && module.exports) module.exports = Credentials;
