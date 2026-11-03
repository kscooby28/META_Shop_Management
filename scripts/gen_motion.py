"""Motion-asset generation: photorealistic cutouts for the living landing.

Renders car side-view cutouts through Muse Image (same confirmed
model + path as the art set), saved full-size under web/assets/
(no webify: cutouts need their pixels for clean keying), with the
manifest eval_motion_results.json. The app keys the flat backdrop
out client-side once at load, then slides the car across the shop
half (translation only — rigid bodies need no articulation).

Usage:
  python scripts/gen_motion.py             render the cutout set
  python scripts/gen_motion.py --only NAME  render one cutout
"""

import base64
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import studio  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "web", "assets")
MANIFEST_NAME = "eval_motion_results.json"
COST_PER_IMAGE = 0.01

CUTOUT = ("Photorealistic side view, full vehicle centered with clear "
          "margin on all sides, wheels straight, on a flat solid "
          "pure-green studio backdrop, even daylight, sharp focus, honest "
          "used condition, no text, no words, no letters, no logos, no "
          "readable plates, no watermark, no people, no other objects.")

PROMPTS = {
    "move-car-shop": ("Dark gray 2000s German sports sedan, side view "
                      "facing right, driving posture. " + CUTOUT),
    "move-car-alt": ("Navy blue 2000s station wagon, side view facing "
                     "right, driving posture. " + CUTOUT),
}


def _dims(blob):
    if len(blob) >= 24 and blob[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            return struct.unpack(">II", blob[16:24])
        except struct.error:
            return 0, 0
    return 0, 0


def render_one(name):
    prompt = PROMPTS[name]
    started = time.time()
    result = studio.request_art_render(prompt)
    raw = base64.b64decode(result["body"].split(",", 1)[1])
    width, height = _dims(raw)
    filename = "%s.png" % name
    with open(os.path.join(ASSETS, filename), "wb") as fh:
        fh.write(raw)
    return {
        "prompt": prompt,
        "file": "web/assets/" + filename,
        "format": "png",
        "bytes": len(raw),
        "dims": ("%dx%d" % (width, height)) if width else "unparsed",
        "latency_ms": int((time.time() - started) * 1000),
    }


def main(argv):
    only = ""
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]
        if only not in PROMPTS:
            raise SystemExit("unknown cutout name: %s" % only)
    names = [only] if only else list(PROMPTS)
    os.makedirs(ASSETS, exist_ok=True)
    studio.IMAGE_LIVE = True  # in-process only; source default untouched
    images = {}
    attempts = {}
    failures = {}
    for name in names:
        attempts[name] = attempts.get(name, 0) + 1
        try:
            images[name] = render_one(name)
            print("%s: ok, %s bytes, %s" % (
                name, images[name]["bytes"], images[name]["dims"]),
                flush=True)
        except Exception as exc:  # noqa: BLE001 - recorded, never secrets
            failures[name] = "%s: %s" % (type(exc).__name__, exc)
            print("%s: FAILED (%s)" % (name, failures[name][:160]),
                  flush=True)
    total_calls = sum(attempts.values())
    manifest = {
        "order": "Living landing: photorealistic motion cutouts",
        "model": "muse-image-1.0",
        "path": "/responses",
        "images": images,
        "attempts": attempts,
        "failures": failures,
        "image_count": len(images),
        "total_bytes": sum(i["bytes"] for i in images.values()),
        "live_calls_sent": total_calls,
        "cost_estimate_usd": round(total_calls * COST_PER_IMAGE, 2),
    }
    with open(os.path.join(ROOT, MANIFEST_NAME), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print("motion set: %d images, %d bytes, $%.2f, %d failures" % (
        len(images), manifest["total_bytes"],
        manifest["cost_estimate_usd"], len(failures)),
        flush=True)


if __name__ == "__main__":
    main(sys.argv)
