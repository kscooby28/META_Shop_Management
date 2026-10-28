/* Gallery: photo strip + viewer model. Pure functions; the page renders.
 * Usable both as a browser global and under Node for tests. */
"use strict";

const Gallery = (() => {
  function stripModel(frames) {
    // Walk-around order in, strip order out. Never re-sorted.
    return (frames || []).map((f, i) => ({ name: f.name, src: f.src, index: i }));
  }

  function selectFrame(frames, name) {
    const list = frames || [];
    return list.find((f) => f.name === name) || list[0] || null;
  }

  function sightingsForFrame(parts, frameName) {
    const out = [];
    for (const part of parts || []) {
      for (const s of part.sightings || []) {
        if (s.frame === frameName) out.push({ part, s });
      }
    }
    return out;
  }

  function partThumb(part) {
    // Every part entry links to its first sighting's frame and box.
    const s = part && part.sightings && part.sightings[0];
    if (!s || !s.box) return null;
    return { frame: s.frame, box: s.box, source_tag: s.source_tag || s.frame };
  }

  function isDemoFrame(name) {
    return /^demo-frame-/.test(name || "");
  }

  return { stripModel, selectFrame, sightingsForFrame, partThumb, isDemoFrame };
})();

if (typeof module !== "undefined" && module.exports) module.exports = Gallery;
