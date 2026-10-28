/* First-run identity: local-only profile. Never sent anywhere.
 * Pure functions over a storage-like {getItem, setItem, removeItem}.
 * Usable both as a browser global and under Node for tests. */
"use strict";

const Profile = (() => {
  const KEY = "copilot.profile";
  const MODES = ["shop", "enthusiast"];

  function loadProfile(storage) {
    try {
      const raw = storage.getItem(KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || MODES.indexOf(parsed.mode) < 0 || !parsed.email) return null;
      return parsed;
    } catch (err) {
      return null;
    }
  }

  function saveProfile(storage, email, mode) {
    const cleanEmail = (email || "").trim();
    if (!cleanEmail || cleanEmail.indexOf("@") < 0) {
      throw new Error("add an email address so the profile knows it is yours");
    }
    if (MODES.indexOf(mode) < 0) {
      throw new Error("pick shop or enthusiast");
    }
    const profile = { email: cleanEmail, mode, created: new Date().toISOString() };
    storage.setItem(KEY, JSON.stringify(profile));
    return profile;
  }

  function needsSetup(storage) {
    return loadProfile(storage) === null;
  }

  function routeFor(mode) {
    if (mode === "shop") return "bay";
    if (mode === "enthusiast") return "inventory";
    return "yard";
  }

  function setMode(storage, mode) {
    const current = loadProfile(storage);
    if (!current) throw new Error("no profile yet: finish first-run setup first");
    return saveProfile(storage, current.email, mode);
  }

  function clearProfile(storage) {
    storage.removeItem(KEY);
  }

  return { KEY, MODES, loadProfile, saveProfile, needsSetup, routeFor, setMode, clearProfile };
})();

if (typeof module !== "undefined" && module.exports) module.exports = Profile;
