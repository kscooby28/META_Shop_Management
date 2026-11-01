"""Art set generation: the overhaul scene illustrations, rendered live.

One-shot measurement-style driver, not product code and never imported
by tests. Renders each scene prompt through Muse Image (confirmed
model + path from Phase 0), saves the bytes as committed app assets
under web/assets/, and writes the manifest eval_art_results.json.

Live is enabled in-process only (the eval-script pattern): the
studio.py source default stays False, so the product listing flow
and every existing studio test are untouched.

Usage:
  python scripts/gen_art.py             render the full set
  python scripts/gen_art.py --only NAME  render one image (regens)
  python scripts/gen_art.py --webify     downscale assets offline, no calls
  python scripts/gen_art.py --case       render the case-art set
  python scripts/gen_art.py --case-only NAME  render one case image
  python scripts/gen_art.py --case-webify     downscale case assets
"""

import base64
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import studio  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "web", "assets")
MANIFEST_NAME = "eval_art_results.json"
CASE_MANIFEST_NAME = "eval_caseart_results.json"
COST_PER_IMAGE = 0.01

STYLE = ("Digital painting, cohesive art direction, deliberate cinematic "
         "lighting, warm amber work light, rich but disciplined color, "
         "polished finish, no watermark.")

PROMPTS = {
    "landing": ("Quiet small-town commercial street at dusk: an auto repair "
                "shop storefront on the left, a house with a home garage in "
                "the middle, a fenced parts yard gate on the right, a few "
                "parked cars as background scenery only. No text, no words, "
                "no letters, no signs with writing. " + STYLE),
    "door-shop": ("Front view of an obvious commercial auto repair shop "
                  "entrance: wide glass door and windows, one plain "
                  "rectangular sign above the door reading exactly the word "
                  "Shop, warm light spilling out, workbench silhouette "
                  "inside. No other text, no business name, no logos. "
                  + STYLE),
    "door-garage": ("Front view of a closed home garage door on a house: "
                    "paneled door, warm lamp beside it, driveway, evening. "
                    "No text, no words, no letters. " + STYLE),
    "door-yard": ("Front view of a metal parts-yard gate: chain-link gate "
                  "slightly open, rows of parts cars behind the fence in "
                  "daylight. No readable text, no words, no letters. "
                  + STYLE),
    "band-shop": ("Wide interior of an auto repair shop: car lift, "
                  "workbench with tools, tool wall, warm amber work lamps. "
                  "No text, no words, no letters. " + STYLE),
    "band-yard": ("Wide view of an auto parts yard lot in daylight: rows "
                  "of parts cars, fence, gravel ground. No text, no words, "
                  "no letters. " + STYLE),
    "band-garage": ("Wide interior of a cozy home garage: one car, shelves "
                    "with parts bins, warm lamp glow. No text, no words, "
                    "no letters. " + STYLE),
}


PHOTO = ("Photorealistic, sharp focus, honest used condition, no text, "
         "no words, no letters, no watermarks, no readable license plates, "
         "no visible brand badges or logos.")

PART = ("Clean photorealistic e-commerce studio photo of a used car part "
        "(%s): seamless warm-gray backdrop, soft shadow, centered, honest "
        "used condition, no text, no words, no letters, no watermark.")

CASE_PROMPTS = {
    "case-front": ("Front-left three-quarter view of a silver 1990s German "
                   "sports sedan parked inside a home garage, warm lamp "
                   "light, honest used condition with light dust. " + PHOTO),
    "case-side": ("Left side view of a silver 1990s German sports sedan "
                  "parked inside a home garage, warm lamp light, honest "
                  "used condition. " + PHOTO),
    "case-rear": ("Rear-left three-quarter view of a silver 1990s German "
                  "sports sedan in a home garage, taillight visible, warm "
                  "lamp light, honest used condition. " + PHOTO),
    "case-bench": ("Auto shop workbench with several pulled used car parts "
                   "arranged neatly: a side mirror, a headlight, an alloy "
                   "wheel leaning beside the bench, warm amber work lamp. "
                   + PHOTO),
    "part-mirror": PART % "driver side mirror, silver cap, intact glass",
    "part-bumper": PART % "front bumper cover, silver, light scuffs",
    "part-wheel": PART % "silver five-spoke alloy wheel, light brake dust",
    "part-headlight": PART % "driver headlight, clear lens",
    "part-handle": PART % "exterior door handle, black",
    "part-taillight": PART % "red rear taillight with one small visible crack",
    "part-diff": PART % "rear differential, greasy honest wear",
    "part-coil": PART % "ignition coil with a short rubber boot",
    "part-ecu": PART % ("black engine control module with connector pins "
                        "and a blank silver label area"),
    "part-trunklid": ("Silver sedan trunk lid panel leaning against a "
                      "warm-gray studio wall, soft shadow, honest used "
                      "condition. " + PHOTO),
    "part-m3bumper": PART % "sporty front bumper with a lower air lip, black",
    "head-notes": ("Gloved hand holding a bright inspection lamp over an "
                   "open car engine bay, close-up. " + PHOTO),
    "head-trail": ("Repair-order clipboard with a blank checklist and a pen "
                   "lying on a workbench. " + PHOTO),
    "head-parts": ("Wooden shelf of parts bins in a home garage, warm lamp "
                   "glow. " + PHOTO),
    "head-grade": ("Gloved hand holding a blank paper price tag tied with "
                   "string to a used car side mirror. " + PHOTO),
    "head-plan": ("Clipboard with a blank repair checklist leaning against "
                  "an open car hood in a repair shop. " + PHOTO),
    "head-compare": ("Two silver 1990s sedans parked side by side in a "
                     "gravel lot at dusk. " + PHOTO),
    "head-wrench": ("Combination wrench and socket set laid on a fender "
                    "cover over a car fender. " + PHOTO),
    "empty-garage": ("Tidy empty home garage bay, open concrete floor, "
                     "shelves on the wall, warm lamp, no car. " + PHOTO),
    "empty-shelf": ("Clean empty metal parts shelf in a garage, warm "
                    "light. " + PHOTO),
    "bay-engine": ("Open car engine bay close-up in a repair shop, warm "
                   "work light. " + PHOTO),
}



def _jpeg_dims(blob):
    pos = 2
    while pos + 9 < len(blob):
        if blob[pos] != 0xFF:
            pos += 1
            continue
        marker = blob[pos + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", blob[pos + 5:pos + 9])
            return width, height
        if marker == 0xD8 or (0xD0 <= marker <= 0xD9):
            pos += 2
            continue
        size = struct.unpack(">H", blob[pos + 2:pos + 4])[0]
        if size < 2:
            return 0, 0
        pos += 2 + size
    return 0, 0


def _dims(blob, fmt):
    if fmt == "png" and len(blob) >= 24:
        try:
            return struct.unpack(">II", blob[16:24])
        except struct.error:
            return 0, 0
    if fmt == "jpg":
        return _jpeg_dims(blob)
    return 0, 0


WEB_MAX_DIM = 960

CHROME_PATHS = (
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
)


def webify_one(path):
    """Downscale one PNG via a headless render. Offline, no live calls.

    Same pixels, fewer of them: the file is rendered at max 960 on
    the long edge and the screenshot replaces the original. Returns
    (bytes, dims) of the final file, or None on any failure (the
    original is kept untouched and the failure is recorded).
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        width, height = struct.unpack(">II", raw[16:24])
    except struct.error:
        return None
    if max(width, height) <= WEB_MAX_DIM:
        return len(raw), "%dx%d" % (width, height)
    binary = next((p for p in CHROME_PATHS if os.path.isfile(p)), "")
    if not binary:
        return None
    if width >= height:
        out_w = WEB_MAX_DIM
        out_h = max(1, round(WEB_MAX_DIM * height / width))
    else:
        out_h = WEB_MAX_DIM
        out_w = max(1, round(WEB_MAX_DIM * width / height))
    workdir = tempfile.mkdtemp(prefix="art-webify-")
    shot = os.path.join(workdir, "shot.png")
    page = os.path.join(workdir, "page.html")
    file_url = "file:///" + os.path.abspath(path).replace(os.sep, "/")
    html = ("<html><body style='margin:0'>"
            "<img src='%s' style='width:%dpx;display:block'></body></html>"
            % (file_url, out_w))
    try:
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(html)
        done = subprocess.run(
            [binary, "--headless", "--disable-gpu", "--no-sandbox",
             "--disable-crashpad", "--hide-scrollbars",
             "--user-data-dir=" + os.path.join(workdir, "profile"),
             "--window-size=%d,%d" % (out_w, out_h),
             "--screenshot=" + shot,
             "file:///" + page.replace(os.sep, "/")],
            capture_output=True, timeout=120)
        if done.returncode != 0:
            return None
        with open(shot, "rb") as fh:
            small = fh.read()
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if len(small) < 24 or small[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        got_w, got_h = struct.unpack(">II", small[16:24])
    except struct.error:
        return None
    if (got_w, got_h) != (out_w, out_h):
        return None
    with open(path, "wb") as fh:
        fh.write(small)
    return len(small), "%dx%d" % (got_w, got_h)


def webify_all(manifest_name=None):
    manifest = load_manifest(manifest_name)
    images = manifest.get("images", {})
    failures = {}
    for name, info in sorted(images.items()):
        path = os.path.join(ROOT, info["file"])
        before = info["bytes"]
        got = webify_one(path)
        if got is None:
            failures[name] = "downscale failed; full-size kept"
            print("%s: webify FAILED, kept %d bytes" % (name, before))
            continue
        info["bytes"], info["dims"] = got
        info["webified_from"] = before
        print("%s: %d -> %d bytes, %s" % (name, before, got[0], got[1]))
    manifest["images"] = images
    manifest["total_bytes"] = sum(i["bytes"] for i in images.values())
    manifest["webify"] = {
        "method": "headless render at max 960 on the long edge",
        "failures": failures,
    }
    path = os.path.join(ROOT, manifest_name or MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print("webified %d images, %d bytes total, %d failures" % (
        len(images), manifest["total_bytes"], len(failures)))


def load_manifest(name=None):
    path = os.path.join(ROOT, name or MANIFEST_NAME)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def render_one(name, prompts=None):
    prompt = (prompts or PROMPTS)[name]
    started = time.time()
    result = studio.request_art_render(prompt)
    raw = base64.b64decode(result["body"].split(",", 1)[1])
    ext = result["format"]
    width, height = _dims(raw, ext)
    filename = "%s.%s" % (name, ext)
    with open(os.path.join(ASSETS, filename), "wb") as fh:
        fh.write(raw)
    return {
        "prompt": prompt,
        "file": "web/assets/" + filename,
        "format": ext,
        "bytes": len(raw),
        "dims": ("%dx%d" % (width, height)) if width else "unparsed",
        "latency_ms": int((time.time() - started) * 1000),
    }


def main(argv):
    case = ("--case" in argv or "--case-only" in argv
            or "--case-webify" in argv)
    prompts = CASE_PROMPTS if case else PROMPTS
    manifest_name = CASE_MANIFEST_NAME if case else MANIFEST_NAME
    order = ("Case-art set: demo cars, parts, and section art (presentation)"
             if case else "Overhaul Phase 1: scene illustration art set")
    if "--webify" in argv or "--case-webify" in argv:
        webify_all(manifest_name)
        return
    only = ""
    flag = "--case-only" if case else "--only"
    if flag in argv:
        only = argv[argv.index(flag) + 1]
        if only not in prompts:
            raise SystemExit("unknown art name: %s" % only)
    names = [only] if only else list(prompts)
    os.makedirs(ASSETS, exist_ok=True)
    studio.IMAGE_LIVE = True  # in-process only; source default untouched
    manifest = load_manifest(manifest_name)
    images = manifest.get("images", {})
    attempts = manifest.get("attempts", {})
    failures = {}
    for name in names:
        attempts[name] = attempts.get(name, 0) + 1
        try:
            images[name] = render_one(name, prompts)
            print("%s: ok, %s bytes, %s" % (
                name, images[name]["bytes"], images[name]["dims"]))
        except Exception as exc:  # noqa: BLE001 - recorded, never secrets
            failures[name] = "%s: %s" % (type(exc).__name__, exc)
            print("%s: FAILED (%s)" % (name, failures[name][:160]))
    total_calls = sum(attempts.values())
    manifest = {
        "order": order,
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
    path = os.path.join(ROOT, manifest_name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print("wrote %s (%d images, %d bytes, $%.2f, %d failures)" % (
        path, manifest["image_count"], manifest["total_bytes"],
        manifest["cost_estimate_usd"], len(failures)))
    if failures and not only:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
