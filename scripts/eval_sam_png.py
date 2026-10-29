"""SAM PNG resend: one segment call on yard frame 1 as PNG.

Measurement, not product. The WO16 follow-up confirmed the SAM path
from official sources (POST /v1/responses, model sam-3.1, Responses
input shape) and proved the request parses, but the call returned
HTTP 400: image/svg+xml is not an accepted media type. Yard frame 1
exists only as an SVG, so this script converts that exact SVG to PNG
faithfully in-session (headless Chrome screenshot at native size, no
redraw, no substitution) and sends the segment call ONCE on the PNG.
No call is sent when no faithful PNG exists; the SVG is never resent.

The one probe, sent at most once (see PROBE_ALLOWLIST):
  sam-png-segment  POST /v1/responses, model sam-3.1, the confirmed
                   Responses input shape, yard frame 1 as a base64
                   data URL PNG, phrase = the first yard label,
                   deterministic, same as the follow-up. 60s timeout.
                   Geometry is recorded raw and unparsed (no parser
                   in stdlib), or the exact error text on failure.

This script rewires nothing: a proven segment is reported as a
finding for a future rewire order, which gets its own order and
its own tests.

Key handling: .env values are loaded into the process environment so a
fresh shell works; names only are ever reported, values never printed.

Usage:
  python scripts/eval_sam_png.py    convert, send once, write JSON
"""

import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import eval_meta  # noqa: E402 (WO16 helpers reused, WO16 file untouched)
import eval_meta_followup  # noqa: E402 (same POST + path, file untouched)
import eval_scale  # noqa: E402  (same demo set, same builders, same evidence)
from demo_cache import StepCache  # noqa: E402
from meta_client import MetaAPIError  # noqa: E402
import meta_client  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_NAME = "eval_sam_png_results.json"

# The only live probe this file may send. Tests pin this exact set.
PROBE_ALLOWLIST = ("sam-png-segment",)

SAM_TIMEOUT_SECONDS = 60
FRAME_SVG = os.path.join("web", "demo", "frame1.svg")
FRAME_SIZE = 1000  # native viewBox edge; the PNG matches it exactly

CHROME_PATHS = (
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
)


def _ms(started):
    return int((time.time() - started) * 1000)


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _png_dims(raw):
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    try:
        return struct.unpack(">II", raw[16:24])
    except struct.error:
        return 0, 0


def _chrome_version(binary):
    try:
        done = subprocess.run(
            [binary, "--version"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (done.stdout or b"").decode("utf-8", "replace").strip()


def render_png(root):
    """Step 0: yard frame 1 as a faithful PNG, or an honest no-PNG.

    Renders the exact SVG bytes at native size with an installed
    headless browser. The PNG is validated (magic plus dimensions)
    before it may be sent. Temp files live outside the repo and are
    removed afterwards; only hashes and sizes are recorded.
    """
    svg_path = os.path.join(root, FRAME_SVG)
    try:
        with open(svg_path, "rb") as fh:
            svg_raw = fh.read()
    except OSError as exc:
        return {"png_ok": False, "cause": "frame SVG missing: %s" % exc,
                "svg_sha256": "", "png": {}, "calls_blocked": True}
    svg_hash = _sha256(svg_raw)
    binary = next((p for p in CHROME_PATHS if os.path.isfile(p)), "")
    if not binary:
        return {"png_ok": False,
                "cause": ("no headless browser available in-session, so "
                          "no faithful PNG could be rendered"),
                "svg_sha256": svg_hash, "png": {}, "calls_blocked": True}
    workdir = tempfile.mkdtemp(prefix="sam-png-")
    out_path = os.path.join(workdir, "frame1.png")
    profile = os.path.join(workdir, "profile")
    url = "file:///" + svg_path.replace(os.sep, "/")
    started = time.time()
    try:
        done = subprocess.run(
            [binary, "--headless", "--disable-gpu", "--no-sandbox",
             "--disable-crashpad", "--hide-scrollbars",
             "--user-data-dir=" + profile,
             "--window-size=%d,%d" % (FRAME_SIZE, FRAME_SIZE),
             "--screenshot=" + out_path, url],
            capture_output=True, timeout=120)
        try:
            with open(out_path, "rb") as fh:
                png_raw = fh.read()
        except OSError:
            return {"png_ok": False,
                    "cause": ("browser render produced no file: %s" % (
                        (done.stderr or b"")[:200].decode(
                            "utf-8", "replace"))),
                    "svg_sha256": svg_hash, "png": {},
                    "calls_blocked": True,
                    "latency_ms": _ms(started)}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"png_ok": False,
                "cause": "browser render failed: %s" % exc,
                "svg_sha256": svg_hash, "png": {},
                "calls_blocked": True, "latency_ms": _ms(started)}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    width, height = _png_dims(png_raw)
    if (width, height) != (FRAME_SIZE, FRAME_SIZE):
        return {"png_ok": False,
                "cause": ("rendered PNG has wrong shape %dx%d, want "
                          "%dx%d" % (width, height, FRAME_SIZE, FRAME_SIZE)),
                "svg_sha256": svg_hash, "png": {},
                "calls_blocked": True, "latency_ms": _ms(started)}
    return {"png_ok": True, "cause": "",
            "svg_sha256": svg_hash,
            "png": {"method": "headless-browser screenshot at native size",
                    "browser": binary,
                    "browser_version": _chrome_version(binary),
                    "mime": "image/png",
                    "bytes": len(png_raw),
                    "sha256": _sha256(png_raw),
                    "dims": "%dx%d" % (width, height),
                    "data_url_chars": len("data:image/png;base64,")
                    + len(base64.b64encode(png_raw).decode("ascii"))},
            "calls_blocked": False, "latency_ms": _ms(started),
            "png_raw": png_raw}


def sam_png_call(root, api_base, key, sam_model, png_raw, phrase):
    """ONE segment call on the PNG, on the officially confirmed path."""
    data_url = "data:image/png;base64,%s" % (
        base64.b64encode(png_raw).decode("ascii"))
    payload = {
        "model": sam_model,
        "input": [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": phrase},
                {"type": "input_image", "image_url": data_url},
            ],
        }],
        "stream": True,
    }
    seen = eval_meta_followup.post_capture(
        api_base + eval_meta_followup.SAM_CONFIRMED_PATH, payload, key,
        SAM_TIMEOUT_SECONDS, accept="text/event-stream")
    if seen["transport_error"]:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API unreachable: %s" % seen["transport_error"],
                "frame": "demo-frame-1", "phrase": phrase,
                "verdict": "failed"}
    if seen["status"] in (401, 403):
        return {"live_ok": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API key rejected (%s)" % seen["status"],
                "frame": "demo-frame-1", "phrase": phrase,
                "verdict": "failed"}
    if seen["status"] != 200:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API error %s: %s" % (
                    seen["status"], seen["body"][:2000]),
                "frame": "demo-frame-1", "phrase": phrase,
                "verdict": "failed",
                "request_id": seen["request_id"],
                "http_status": seen["status"]}
    event_types, deltas, complete = [], [], False
    for line in seen["body"].splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            complete = True
            continue
        try:
            event = json.loads(data)
        except ValueError:
            continue
        etype = event.get("type", "")
        if etype and etype not in event_types:
            event_types.append(etype)
        if etype == "response.output_text.delta":
            delta = event.get("delta", "")
            if delta:
                deltas.append(delta)
    output_text = "".join(deltas)
    cache = StepCache(root)
    try:
        harvest = cache.load_demo("harvest")
    except (OSError, ValueError):
        harvest = {}
    demo_hits = 0
    for part in harvest.get("parts", []):
        for sight in part.get("sightings", []):
            if (sight.get("frame") == "demo-frame-1"
                    and part.get("label") == phrase):
                demo_hits += 1
    verdict = "proven-live" if output_text else "responded-empty"
    return {"live_ok": True, "call_sent": True,
            "latency_ms": seen["latency_ms"], "cause": "",
            "frame": "demo-frame-1", "phrase": phrase,
            "image_mime": "image/png",
            "request_id": seen["request_id"],
            "http_status": seen["status"],
            "stream_complete": complete,
            "event_types": sorted(event_types),
            "delta_count": len(deltas),
            "output_len": len(output_text),
            "output_head": output_text[:400],
            "output_truncated": len(output_text) > 400,
            "demo_sightings_for_phrase": demo_hits,
            "verdict": verdict,
            "parse_note": ("raw output_text recorded, not parsed to "
                           "boxes: no parser in stdlib")}


def probe_sam_png(root):
    """The one probe: Step 0 gates the single segment call."""
    eval_meta.load_dotenv_into_environ(root)
    cfg = meta_client.settings()
    try:
        key = meta_client._api_key()
        key_cause = ""
    except MetaAPIError as exc:
        key, key_cause = "", str(exc)
    built = eval_scale.BUILDERS["yard-demo"](root)
    verdicts = built["verdicts"]
    phrase = verdicts[0]["label"] if verdicts else ""
    png = render_png(root)
    png_raw = png.pop("png_raw", b"")
    if key_cause:
        call = {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": key_cause, "frame": "", "phrase": phrase,
                "verdict": "no-call"}
    elif not png["png_ok"]:
        call = {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": ("no faithful PNG in-session, so no call was "
                          "sent: %s" % png["cause"]),
                "frame": "", "phrase": phrase, "verdict": "no-call"}
    elif not phrase:
        call = {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to verify, so no call was sent",
                "frame": "", "phrase": "", "verdict": "no-call"}
    else:
        call = sam_png_call(root, cfg["api_base"], key,
                            cfg["sam_model"], png_raw, phrase)
    proven = call["verdict"] == "proven-live"
    return {
        "order": "SAM PNG resend: one segment call on yard frame 1 as PNG",
        "baseline_followup": {
            "path": "POST /v1/responses, model sam-3.1",
            "svg_rejection": ("HTTP 400 invalid_request_error: unsupported "
                              "media type image/svg+xml"),
            "svg_request_id": "74ff9f0d-656a-4b63-97f6-1469943a201e",
        },
        "api_base": cfg["api_base"],
        "sam_model": cfg["sam_model"],
        "key_cause": key_cause,
        "png": png,
        "call": call,
        "sam_proven_live": proven,
        "leg": ("proven live: geometry returned for yard frame 1 as PNG"
                if proven else
                "closed: %s" % (call["cause"] or call["verdict"])),
        "rewire_follows": proven,
        "vin_live": False,
        "vin_reason": ("segmentation only, not VIN plates; no demo VIN "
                       "plate images exist, so 0 live VIN calls sent"),
        "live_vin_calls_sent": 0,
        "live_calls_sent_total": 1 if call["call_sent"] else 0,
        "model_list_calls_sent": 0,
    }


def write_results(results):
    path = os.path.join(ROOT, RESULTS_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=False)
        fh.write("\n")
    return path


def main(argv):
    del argv
    results = probe_sam_png(ROOT)
    path = write_results(results)
    print("wrote %s" % path)
    png = results["png"]
    print("png: %s" % ("ok, %s bytes, %s" % (
        png["png"]["bytes"], png["png"]["dims"]) if png["png_ok"]
        else "MISSING (%s)" % png["cause"]))
    call = results["call"]
    print("sam png: %s" % (
        "live ok, %s" % call["verdict"] if call["live_ok"]
        else ("no call (%s)" % call["cause"] if not call["call_sent"]
              else "FAILED (%s)" % call["cause"][:200])))
    print("sam proven live: %s" % results["sam_proven_live"])
    print("live calls sent: %d" % results["live_calls_sent_total"])


if __name__ == "__main__":
    main(sys.argv[1:])
