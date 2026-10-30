"""SAM file_id probe: one real-photo segment call (measurement only).

The SAM leg closed twice on base64 data-URL PNGs of a LINE DRAWING
(HTTP 200, zero geometry both times). The owner-supplied official SAM
code uses a different shape: upload the file first (POST /v1/files),
then reference it by file_id, on a REAL photo. This script tests ONLY
whether that shape plus real content produces geometry. One upload,
one segment call, no retries, no rewire, nothing else.

Probes, each sent at most once (see PROBE_ALLOWLIST):
  sam-fileid-upload   POST /v1/files, multipart form purpose=user_data
                      plus the JPEG. Records the returned file id.
  sam-fileid-segment  POST /v1/responses, model sam-3.1, one user
                      message (input_text "driver mirror" plus
                      input_image carrying the file_id), stream true,
                      metadata mask_encoding lossless. Records the
                      stream and the geometry verdict.

The photo lives OUTSIDE the repo at C:\\Temp\\sam-probe-photo.jpg and
is never committed, added, or copied into the repo. Only its byte
size, dimensions, and sha256 are recorded.

Key handling: .env values are loaded into the process environment so a
fresh shell works; the key NAME used is recorded, values never printed.

Usage:
  python scripts/eval_sam_fileid.py    probe once, write JSON
"""

import base64
import hashlib
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meta_client import MetaAPIError  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_NAME = "eval_sam_fileid_results.json"
PHOTO_PATH = "C:\\Temp\\sam-probe-photo.jpg"
API_BASE = "https://api.meta.ai/v1"
SAM_MODEL = "sam-3.1"
PHRASE = "driver mirror"
TIMEOUT_SECONDS = 60

# The only live probes this file may send. Tests pin this exact set.
PROBE_ALLOWLIST = ("sam-fileid-upload", "sam-fileid-segment")

FRAME_MARK = re.compile(r"<(\d+)f(?:;[^>]*)?>")
BOX_TOKEN = re.compile(r"<\|box;([^|]*)\|>")
MASK_TOKEN = re.compile(r"<\|mask;([^|]*)\|>")


def _ms(started):
    return int((time.time() - started) * 1000)


def _request_id(headers):
    for name in ("x-request-id", "request-id", "x-meta-request-id"):
        value = headers.get(name) or headers.get(name.title())
        if value:
            return value
    return ""


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


def _load_key():
    names = ("META_API_KEY", "MODEL_API_KEY")
    vals = {}
    try:
        with open(os.path.join(ROOT, ".env"), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and value:
                    vals[key] = value
    except OSError:
        pass
    for name in names:
        key = (os.environ.get(name) or vals.get(name) or "").strip()
        if key:
            return key, name
    raise MetaAPIError("no API key in local .env or environment", kind="auth")


def step0_photo():
    """Fingerprint the outside-repo photo. No calls, no copies."""
    try:
        with open(PHOTO_PATH, "rb") as fh:
            raw = fh.read()
    except OSError:
        return {"photo_ok": False,
                "cause": ("No real photo at %s" % PHOTO_PATH),
                "photo": {}, "raw": b""}
    is_jpeg = raw[:3] == b"\xff\xd8\xff"
    width, height = _jpeg_dims(raw) if is_jpeg else (0, 0)
    if not is_jpeg or not raw:
        return {"photo_ok": False,
                "cause": "photo is not a readable JPEG; no converter "
                         "attempted on a non-JPEG real photo",
                "photo": {}, "raw": b""}
    return {"photo_ok": True, "cause": "",
            "photo": {"path": PHOTO_PATH,
                      "bytes": len(raw),
                      "dims": "%dx%d" % (width, height),
                      "sha256": hashlib.sha256(raw).hexdigest(),
                      "jpeg": True},
            "raw": raw}


def step1_upload(key, raw):
    """ONE files upload call. Returns the upload record."""
    boundary = "samprobe%s" % os.urandom(8).hex()
    body = (
        "--%s\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\n"
        "user_data\r\n"
        "--%s\r\nContent-Disposition: form-data; name=\"file\"; "
        "filename=\"upload.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
        % (boundary, boundary)).encode("utf-8") + raw + (
            "\r\n--%s--\r\n" % boundary).encode("utf-8")
    request = urllib.request.Request(
        API_BASE + "/files", data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(request,
                                    timeout=TIMEOUT_SECONDS) as response:
            payload = response.read().decode("utf-8", "replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:2000]
        except Exception:
            detail = ""
        return {"call_sent": True, "latency_ms": _ms(started),
                "http_status": exc.code, "file_id": "",
                "cause": "upload error %s: %s" % (exc.code, detail)}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"call_sent": True, "latency_ms": _ms(started),
                "http_status": 0, "file_id": "",
                "cause": "upload unreachable: %s: %s" % (
                    type(exc).__name__, exc)}
    try:
        file_id = json.loads(payload).get("id") or ""
    except ValueError:
        file_id = ""
    if not file_id or not isinstance(file_id, str):
        return {"call_sent": True, "latency_ms": _ms(started),
                "http_status": status, "file_id": "",
                "cause": "upload returned no file id: %s" % payload[:500]}
    return {"call_sent": True, "latency_ms": _ms(started),
            "http_status": status, "file_id": file_id, "cause": ""}


def _box_fields(text):
    fields = {}
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        fields[key.strip()] = value.strip()
    try:
        box = {k: int(fields[k]) for k in ("x1", "y1", "x2", "y2")}
        box["w"] = int(fields["w"])
        box["h"] = int(fields["h"])
    except (KeyError, ValueError):
        return None
    if "c" in fields:
        try:
            box["c"] = float(fields["c"])
        except ValueError:
            pass
    return box


def _mask_summary(text):
    fields = {}
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        fields[key.strip()] = value.strip()
    data = fields.get("data", "")
    parts = data.split(",", 2)
    if len(parts) != 3:
        return None
    try:
        height, width = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    payload = parts[2]
    encoding = ("lossless" if payload.startswith("~")
                else ("one_bit" if payload.startswith("!") else "unknown"))
    return {"h": height, "w": width, "encoding": encoding,
            "payload_chars": len(payload), "payload_head": payload[:64]}


def parse_geometry(output_text):
    """Minimal honest parse of SAM special-token text per protocol/sam3.md.

    One line per frame: <Nf> plus comma-separated records, each one
    box token plus one mask token. Returns counts plus extracted
    boxes; malformed lines are counted, never silently fixed.
    """
    boxes, masks, frames, malformed = [], [], [], 0
    lines = [ln for ln in output_text.splitlines() if ln.strip()]
    for line in lines:
        frames.extend(FRAME_MARK.findall(line))
        found_boxes = [b for b in (_box_fields(t) for t in
                                   BOX_TOKEN.findall(line))]
        found_masks = [m for m in (_mask_summary(t) for t in
                                   MASK_TOKEN.findall(line))]
        raw_boxes = len(BOX_TOKEN.findall(line))
        raw_masks = len(MASK_TOKEN.findall(line))
        if (raw_boxes != len([b for b in found_boxes if b])
                or raw_masks != len([m for m in found_masks if m])
                or raw_boxes != raw_masks):
            malformed += 1
        boxes.extend(b for b in found_boxes if b)
        masks.extend(m for m in found_masks if m)
    paired = min(len(boxes), len(masks))
    return {"lines": len(lines), "frames": frames,
            "box_count": len(boxes), "mask_count": len(masks),
            "paired_records": paired, "malformed_lines": malformed,
            "boxes": boxes, "masks": masks}


def step2_segment(key, file_id):
    """ONE responses segment call on the file_id. No retries."""
    payload = {
        "model": SAM_MODEL,
        "input": [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": PHRASE},
                {"type": "input_image", "file_id": file_id},
            ],
        }],
        "stream": True,
        "metadata": {"mask_encoding": "lossless"},
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_BASE + "/responses", data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "Accept": "text/event-stream"},
        method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(request,
                                    timeout=TIMEOUT_SECONDS) as response:
            text = response.read().decode("utf-8", "replace")
            heads = dict(response.headers.items())
            status = response.status
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:2000]
        except Exception:
            detail = ""
        heads = dict(exc.headers.items()) if exc.headers else {}
        return {"call_sent": True, "latency_ms": _ms(started),
                "http_status": exc.code, "request_id": _request_id(heads),
                "cause": "API error %s: %s" % (exc.code, detail),
                "geometry": {}, "verdict": "failed"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"call_sent": True, "latency_ms": _ms(started),
                "http_status": 0, "request_id": "",
                "cause": "API unreachable: %s: %s" % (
                    type(exc).__name__, exc),
                "geometry": {}, "verdict": "failed"}
    if status != 200:
        return {"call_sent": True, "latency_ms": _ms(started),
                "http_status": status, "request_id": _request_id(heads),
                "cause": "API error %s: %s" % (status, text[:500]),
                "geometry": {}, "verdict": "failed"}
    event_types, deltas, complete = [], [], False
    for line in text.splitlines():
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
        etype = event.get("type", "") if isinstance(event, dict) else ""
        if etype and etype not in event_types:
            event_types.append(etype)
        if etype == "response.output_text.delta":
            delta = event.get("delta", "")
            if delta:
                deltas.append(delta)
    output_text = "".join(deltas)
    geometry = parse_geometry(output_text)
    verdict = "PROVEN" if geometry["paired_records"] > 0 else "ZERO"
    return {"call_sent": True, "latency_ms": _ms(started),
            "http_status": status, "request_id": _request_id(heads),
            "cause": "", "phrase": PHRASE,
            "stream_complete": complete,
            "event_types": sorted(event_types),
            "delta_count": len(deltas),
            "output_len": len(output_text),
            "output_head": output_text[:400],
            "output_truncated": len(output_text) > 400,
            "geometry": geometry, "verdict": verdict}


def probe():
    try:
        key, key_name = _load_key()
        key_cause = ""
    except MetaAPIError as exc:
        key, key_name, key_cause = "", "", str(exc)
    step0 = step0_photo()
    raw = step0.pop("raw", b"")
    if key_cause:
        upload = {"call_sent": False, "latency_ms": 0, "http_status": 0,
                  "file_id": "", "cause": key_cause}
        call = {"call_sent": False, "latency_ms": 0, "http_status": 0,
                "request_id": "", "cause": key_cause,
                "geometry": {}, "verdict": "no-call"}
    elif not step0["photo_ok"]:
        upload = {"call_sent": False, "latency_ms": 0, "http_status": 0,
                  "file_id": "", "cause": step0["cause"]}
        call = {"call_sent": False, "latency_ms": 0, "http_status": 0,
                "request_id": "", "cause": step0["cause"],
                "geometry": {}, "verdict": "no-call"}
    else:
        upload = step1_upload(key, raw)
        if upload["file_id"]:
            call = step2_segment(key, upload["file_id"])
        else:
            call = {"call_sent": False, "latency_ms": 0, "http_status": 0,
                    "request_id": "", "cause": upload["cause"],
                    "geometry": {}, "verdict": "no-call"}
    sam_verdict = ("PROVEN" if call["verdict"] == "PROVEN"
                   else "CLOSED AGAIN")
    return {
        "order": "SAM file_id probe: one real-photo segment call",
        "key_name": key_name,
        "key_cause": key_cause,
        "photo": step0.get("photo", {}),
        "photo_ok": step0["photo_ok"],
        "photo_cause": step0["cause"],
        "upload": upload,
        "call": call,
        "sam_verdict": sam_verdict,
        "sam_state": ("PROVEN live: file_id shape plus real photo "
                      "returned geometry" if sam_verdict == "PROVEN" else
                      "CLOSED AGAIN: %s" % (
                          call["cause"] or call["verdict"])),
        "vin_live": False,
        "live_vin_calls_sent": 0,
        "live_calls_sent_total": (1 if upload["call_sent"] else 0)
        + (1 if call["call_sent"] else 0),
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
    results = probe()
    path = write_results(results)
    print("wrote %s" % path)
    print("photo: %s" % ("ok" if results["photo_ok"]
                         else "MISSING (%s)" % results["photo_cause"]))
    upload = results["upload"]
    print("upload: %s" % (
        "ok, %s" % upload["file_id"] if upload["file_id"]
        else ("no call (%s)" % upload["cause"] if not upload["call_sent"]
              else "FAILED (%s)" % upload["cause"][:200])))
    call = results["call"]
    print("segment: %s" % (
        "%s, %d records" % (call["verdict"],
                            call["geometry"].get("paired_records", 0))
        if call["call_sent"] and not call["cause"]
        else ("no call (%s)" % call["cause"] if not call["call_sent"]
              else "FAILED (%s)" % call["cause"][:200])))
    print("SAM verdict: %s" % results["sam_verdict"])
    print("live calls sent: %d" % results["live_calls_sent_total"])


if __name__ == "__main__":
    main(sys.argv[1:])
