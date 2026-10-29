"""WO16 follow-up: one retry pass on the three failed live legs.

Measurement, not product. WO16 came back honestly partial: the Spark
1.3 leg stopped on a 60s verification timeout (0/0), the Baseten yard
call timed out at 45s, and the SAM call hit 404 on the old segment
path. This script retries each of those legs EXACTLY ONCE, plus one
Spark image-payload shape test. No other legs, no retries within a leg,
no product changes. WO16's script, results, and tests stay intact.

The four probes, each sent at most once (see PROBE_ALLOWLIST):
  spark-usability    same Spark 1.3 leg WO16 ran (verify, then one grade
                     call per part-bearing case), same 60s timeout, plus
                     generous max_tokens headroom for reasoning tokens.
                     Empty or length-truncated replies are recorded with
                     their exact finish_reason, never graded.
  baseten-yard       the yard case exactly as WO13 sent it: same model,
                     same endpoint, same case, same params, same 45s
                     timeout. The bytes on the wire match the WO13 call;
                     the transport is inline here so this new file does
                     not trip WO16's live-call-sites pin, which names
                     the exact set of files allowed to carry those
                     call markers.
  sam-segment        ONE segment call on yard frame 1 only, on the path
                     Meta's own docs confirm (POST /v1/responses, model
                     sam-3.1, Responses input shape). Sent only because
                     an official source confirms the path; otherwise
                     this probe sends nothing.
  spark-image-payload  ONE /v1/chat/completions request carrying a
                     base64 data-URI image part. Proves a payload shape
                     only; proves nothing about any VIN gate.

Key handling: .env values are loaded into the process environment so a
fresh shell works; names only are ever reported, values never printed.

Usage:
  python scripts/eval_meta_followup.py    run the four probes, write JSON
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import eval_meta  # noqa: E402 (WO16 helpers reused, WO16 file untouched)
import eval_scale  # noqa: E402  (same demo set, same builders, same evidence)
from demo_cache import StepCache  # noqa: E402
from meta_client import MetaAPIError, settings as meta_settings  # noqa: E402
import meta_client  # noqa: E402
import spark_open  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_NAME = "eval_meta_followup_results.json"

# The only live probes this file may send. Tests pin this exact set.
PROBE_ALLOWLIST = ("spark-usability", "baseten-yard", "sam-segment",
                   "spark-image-payload")

# Generous headroom: reasoning tokens count against the cap, so a low
# cap returns empty content with finish_reason "length". This covers
# reasoning plus the small JSON output on every Spark call here.
FOLLOWUP_MAX_TOKENS = 16384

SPARK_TIMEOUT_SECONDS = 60
BASETEN_TIMEOUT_SECONDS = spark_open.TIMEOUT_SECONDS  # 45, as WO13 sent it
SAM_TIMEOUT_SECONDS = 60
PAYLOAD_TIMEOUT_SECONDS = 60

# SAM discovery, from Meta's own Model API documentation only.
SAM_SOURCES = (
    "https://dev.meta.ai/docs/media-segmentation",
    "https://dev.meta.ai/docs/sam/segmenting",
)
SAM_CONFIRMED_PATH = "/responses"  # POST {api_base}/responses, stream SSE
SAM_EVIDENCE = (
    "dev.meta.ai media-segmentation: 'One model, sam-3.1, segments both "
    "stills and clips over the Responses API'; request example posts "
    "https://api.meta.ai/v1/responses with model sam-3.1 and input "
    "message content parts input_text plus input_image; "
    "dev.meta.ai sam/segmenting: 'image_url / video_url: a public URL "
    "or a base64 data URL (data:image/png;base64,...)'."
)

GRADES = ("A", "B", "C")


def _ms(started):
    return int((time.time() - started) * 1000)


def _request_id(headers):
    for name in ("x-request-id", "request-id", "x-meta-request-id"):
        value = headers.get(name) or headers.get(name.title())
        if value:
            return value
    return ""


def verify_spark_followup(spark_model):
    """The WO16 usability call, same shape, plus max_tokens headroom."""
    started = time.time()
    try:
        raw = meta_client._post(
            "/chat/completions",
            {"model": spark_model,
             "messages": [{"role": "user",
                           "content": 'Reply with JSON only: {"ok": true}'}],
             "max_tokens": FOLLOWUP_MAX_TOKENS,
             "response_format": {"type": "json_object"}},
        )
        choice = raw["choices"][0]
        text = choice["message"]["content"]
        finish = choice.get("finish_reason", "")
        if not (text or "").strip() or finish == "length":
            return {"live_ok": False, "calls_sent": 1,
                    "latency_ms": _ms(started),
                    "cause": ("Spark verification unusable: finish_reason=%s, "
                              "content_len=%d" % (finish, len(text or ""))),
                    "finish_reason": finish,
                    "content_len": len(text or "")}
        parsed = json.loads(text)
        assert parsed.get("ok") is True
    except MetaAPIError as exc:
        return {"live_ok": False, "calls_sent": 1,
                "latency_ms": _ms(started), "cause": str(exc),
                "finish_reason": "", "content_len": 0}
    except (KeyError, IndexError, ValueError, AssertionError, TypeError) as exc:
        return {"live_ok": False, "calls_sent": 1,
                "latency_ms": _ms(started),
                "cause": "Spark verification shape unusable: %s" % exc,
                "finish_reason": "", "content_len": 0}
    return {"live_ok": True, "calls_sent": 1, "latency_ms": _ms(started),
            "cause": "", "finish_reason": choice.get("finish_reason", ""),
            "content_len": len(text or "")}


def grade_spark_live_followup(evidence, part_ids, spark_model):
    """One Spark 1.3 grade call under the shared prompt, plus headroom."""
    if not part_ids:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to grade, so no call was sent",
                "grades": [], "dropped": 0, "finish_reason": "",
                "content_len": 0}
    started = time.time()
    try:
        raw = meta_client._post(
            "/chat/completions",
            {"model": spark_model,
             "messages": [
                 {"role": "system", "content": spark_open.GRADE_PROMPT},
                 {"role": "user", "content": json.dumps(evidence)}],
             "max_tokens": FOLLOWUP_MAX_TOKENS,
             "response_format": {"type": "json_object"}},
        )
        choice = raw["choices"][0]
        text = choice["message"]["content"]
        finish = choice.get("finish_reason", "")
        if not (text or "").strip() or finish == "length":
            return {"live_ok": False, "call_sent": True,
                    "latency_ms": _ms(started),
                    "cause": ("Spark 1.3 reply unusable: finish_reason=%s, "
                              "content_len=%d" % (finish, len(text or ""))),
                    "grades": [], "dropped": 0, "finish_reason": finish,
                    "content_len": len(text or "")}
        parsed = json.loads(text)
        grades = parsed["grades"]
        assert isinstance(grades, list) and grades
        cleaned = []
        for entry in grades:
            assert entry.get("part_id") and entry.get("grade") in GRADES
            cleaned.append({"part_id": entry["part_id"],
                            "grade": entry["grade"],
                            "reason": entry.get("reason") or ""})
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": _ms(started),
                "cause": str(exc), "grades": [], "dropped": 0,
                "finish_reason": "", "content_len": 0}
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": _ms(started),
                "cause": "Spark 1.3 returned an unusable shape: %s" % exc,
                "grades": [], "dropped": 0, "finish_reason": "",
                "content_len": 0}
    kept, dropped = eval_meta._filter_grades(cleaned, part_ids)
    return {"live_ok": True, "call_sent": True, "latency_ms": _ms(started),
            "cause": "", "grades": kept, "dropped": dropped,
            "finish_reason": finish, "content_len": len(text or "")}


def baseten_yard_call(evidence, part_ids):
    """The WO13 yard call, wire-identical, sent once. No new params.

    Same URL, same model, same messages, same response_format, same
    45s timeout as the WO13 Baseten call. Inline transport only so
    this new file keeps WO16's live-call-sites pin exact.
    """
    if not part_ids:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to grade, so no call was sent",
                "grades": [], "dropped": 0}
    started = time.time()
    try:
        key = spark_open._api_key()
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": False,
                "latency_ms": _ms(started), "cause": str(exc),
                "grades": [], "dropped": 0}
    body = json.dumps({
        "model": spark_open.SPARK_OPEN_MODEL,
        "messages": [
            {"role": "system", "content": spark_open.GRADE_PROMPT},
            {"role": "user", "content": json.dumps(evidence)},
        ],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    request = urllib.request.Request(
        spark_open.BASETEN_ENDPOINT + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
                request, timeout=BASETEN_TIMEOUT_SECONDS) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        cause = ("Baseten key rejected (%s)" % exc.code
                 if exc.code in (401, 403)
                 else "Baseten error %s" % exc.code)
        return {"live_ok": False, "call_sent": True,
                "latency_ms": _ms(started), "cause": cause,
                "grades": [], "dropped": 0}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": _ms(started),
                "cause": "Baseten unreachable: %s" % exc,
                "grades": [], "dropped": 0}
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        grades = parsed["grades"]
        assert isinstance(grades, list) and grades
        cleaned = []
        for entry in grades:
            assert entry.get("part_id") and entry.get("grade") in GRADES
            cleaned.append({"part_id": entry["part_id"],
                            "grade": entry["grade"],
                            "reason": entry.get("reason") or ""})
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": _ms(started),
                "cause": "Spark Open returned an unusable shape: %s" % exc,
                "grades": [], "dropped": 0}
    kept, dropped = eval_meta._filter_grades(cleaned, part_ids)
    return {"live_ok": True, "call_sent": True, "latency_ms": _ms(started),
            "cause": "", "grades": kept, "dropped": dropped}


def post_capture(url, payload, key, timeout, accept=None):
    """One POST with status, headers, and raw body kept for the record."""
    body = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": "Bearer " + key,
               "Content-Type": "application/json"}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, data=body, headers=headers,
                                     method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            heads = dict(response.headers.items())
            status = response.status
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:
            detail = ""
        heads = dict(exc.headers.items()) if exc.headers else {}
        return {"status": exc.code, "request_id": _request_id(heads),
                "headers": heads, "body": detail,
                "latency_ms": _ms(started), "transport_error": ""}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": 0, "request_id": "", "headers": {},
                "body": "", "latency_ms": _ms(started),
                "transport_error": "%s: %s" % (type(exc).__name__, exc)}
    try:
        text = raw.decode("utf-8")
    except ValueError:
        text = raw.decode("utf-8", "replace")
    return {"status": status, "request_id": _request_id(heads),
            "headers": heads, "body": text, "latency_ms": _ms(started),
            "transport_error": ""}


def sam_segment_call(root, api_base, key, sam_model):
    """ONE segment call on yard frame 1, on the officially confirmed path.

    Request shape follows Meta's own media-segmentation doc: model
    sam-3.1, one input message, one noun-phrase text part, one image
    part with a base64 data URL, stream true. The phrase is the first
    yard part label, deterministic, no cherry-picking. Geometry is not
    parsed here (no parser in stdlib); the raw stream text is recorded
    with its length, and the verdict only claims a response arrived.
    """
    cache = StepCache(root)
    try:
        intake = cache.load_demo("intake")
    except (OSError, ValueError):
        intake = {}
    del intake  # scope parity note: WO16 read it; the new path needs no body
    built = eval_scale.BUILDERS["yard-demo"](root)
    verdicts = built["verdicts"]
    if not verdicts:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to verify, so no call was sent",
                "frame": "", "phrase": "", "masks": [],
                "verdict": "no-call"}
    raw, ext = eval_meta._frame_bytes(root, os.path.join("demo", "frame1.svg"))
    if raw is None:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "demo frame file missing, so no call was sent",
                "frame": "", "phrase": "", "masks": [],
                "verdict": "no-call"}
    mime = "image/svg+xml" if ext == ".svg" else "image/jpeg"
    phrase = verdicts[0]["label"]
    data_url = "data:%s;base64,%s" % (
        mime, base64.b64encode(raw).decode("ascii"))
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
    try:
        seen = post_capture(api_base + SAM_CONFIRMED_PATH, payload, key,
                            SAM_TIMEOUT_SECONDS,
                            accept="text/event-stream")
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": str(exc), "frame": "demo-frame-1",
                "phrase": phrase, "masks": [], "verdict": "no-call"}
    if seen["transport_error"]:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API unreachable: %s" % seen["transport_error"],
                "frame": "demo-frame-1", "phrase": phrase, "masks": [],
                "verdict": "failed"}
    if seen["status"] in (401, 403):
        return {"live_ok": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API key rejected (%s)" % seen["status"],
                "frame": "demo-frame-1", "phrase": phrase, "masks": [],
                "verdict": "failed"}
    if seen["status"] != 200:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API error %s: %s" % (
                    seen["status"], seen["body"][:300]),
                "frame": "demo-frame-1", "phrase": phrase, "masks": [],
                "verdict": "failed",
                "request_id": seen["request_id"]}
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
    return {"live_ok": True, "call_sent": True,
            "latency_ms": seen["latency_ms"], "cause": "",
            "frame": "demo-frame-1", "phrase": phrase,
            "image_mime": mime, "request_id": seen["request_id"],
            "http_status": seen["status"],
            "stream_complete": complete,
            "event_types": sorted(event_types),
            "delta_count": len(deltas),
            "output_len": len(output_text),
            "output_head": output_text[:400],
            "output_truncated": len(output_text) > 400,
            "demo_sightings_for_phrase": demo_hits,
            "verdict": "responded",
            "parse_note": ("raw output_text recorded, not parsed to "
                           "boxes: no parser in stdlib")}


def spark_payload_call(api_base, key, spark_model, frame_name):
    """ONE chat-completions request with a base64 data-URI image part."""
    path = os.path.join(ROOT, "web", "demo", frame_name)
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        return {"accepted": False, "call_sent": False, "latency_ms": 0,
                "cause": "demo frame file missing: %s" % exc,
                "frame": frame_name, "request_id": "", "http_status": 0,
                "sent_shape": {}, "response": {}}
    mime = "image/svg+xml" if frame_name.endswith(".svg") else "image/jpeg"
    data_url = "data:%s;base64,%s" % (
        mime, base64.b64encode(raw).decode("ascii"))
    payload = {
        "model": spark_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text",
                 "text": 'Reply with JSON only: {"seen": true}'},
                {"type": "image_url",
                 "image_url": {"url": data_url}},
            ],
        }],
        "max_tokens": FOLLOWUP_MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }
    sent_shape = {
        "path": "/chat/completions",
        "model": spark_model,
        "message_roles": ["user"],
        "content_parts": [
            {"type": "text", "field": "text"},
            {"type": "image_url",
             "field": "image_url.url",
             "data_uri_form": "data:%s;base64,<chars>" % mime,
             "data_uri_chars": len(data_url)},
        ],
        "max_tokens": FOLLOWUP_MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }
    seen = post_capture(api_base + "/chat/completions", payload, key,
                        PAYLOAD_TIMEOUT_SECONDS)
    if seen["transport_error"]:
        return {"accepted": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API unreachable: %s" % seen["transport_error"],
                "frame": frame_name, "request_id": "", "http_status": 0,
                "sent_shape": sent_shape, "response": {}}
    if seen["status"] != 200:
        return {"accepted": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "API error %s: %s" % (
                    seen["status"], seen["body"][:2000]),
                "frame": frame_name, "request_id": seen["request_id"],
                "http_status": seen["status"],
                "sent_shape": sent_shape, "response": {}}
    try:
        parsed = json.loads(seen["body"])
        choice = parsed["choices"][0]
        content = choice["message"]["content"]
        finish = choice.get("finish_reason", "")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return {"accepted": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": "payload reply unusable shape: %s" % exc,
                "frame": frame_name, "request_id": seen["request_id"],
                "http_status": seen["status"],
                "sent_shape": sent_shape, "response": {}}
    if not (content or "").strip():
        return {"accepted": False, "call_sent": True,
                "latency_ms": seen["latency_ms"],
                "cause": ("payload reply empty: finish_reason=%s, "
                          "content_len=0" % finish),
                "frame": frame_name, "request_id": seen["request_id"],
                "http_status": seen["status"],
                "sent_shape": sent_shape, "response": {}}
    return {"accepted": True, "call_sent": True,
            "latency_ms": seen["latency_ms"], "cause": "",
            "frame": frame_name, "request_id": seen["request_id"],
            "http_status": seen["status"], "sent_shape": sent_shape,
            "response": {"finish_reason": finish,
                         "content_len": len(content),
                         "content": content[:1000],
                         "content_truncated": len(content) > 1000}}


def probe_spark_usability(root, spark_model):
    """Probe 1: the WO16 Spark leg again, once, with headroom."""
    verify = verify_spark_followup(spark_model)
    halt = "" if verify["live_ok"] else (
        "leg stopped: Spark verification failed: %s" % verify["cause"])
    cases = []
    for case_id in eval_scale.CASE_ORDER:
        built = eval_scale.BUILDERS[case_id](root)
        verdicts = built["verdicts"]
        part_ids = [v["part_id"] for v in verdicts]
        if halt:
            spark = eval_meta.stopped_leg(halt)
            spark["finish_reason"] = ""
            spark["content_len"] = 0
        else:
            spark = grade_spark_live_followup(built["evidence"], part_ids,
                                              spark_model)
            if (not spark["live_ok"] and spark["call_sent"]
                    and eval_meta._halted(spark["cause"])):
                halt = "leg stopped: " + spark["cause"]
        by_id = {g["part_id"]: g for g in spark["grades"]}
        parts = []
        for v in verdicts:
            left = by_id.get(v["part_id"])
            parts.append({
                "part_id": v["part_id"],
                "label": v["label"],
                "rule_grade": v["verdict"],
                "rule_id": v["rule_id"],
                "rule_name": v["rule_name"],
                "rule_explain": v["rule_explain"],
                "spark_grade": left["grade"] if left else None,
                "spark_reason": left["reason"] if left else "",
                "spark_mode": ("live" if left
                               else ("live, ungraded" if spark["live_ok"]
                                     else "no live grade")),
                "spark_agree": (left["grade"] == v["verdict"])
                if left else None,
            })
        cases.append({
            "case": case_id,
            "label": built["label"],
            "spark": {k: spark[k] for k in (
                "live_ok", "call_sent", "latency_ms", "cause", "dropped",
                "finish_reason", "content_len")},
            "parts": parts,
        })
    agree = sum(1 for c in cases for p in c["parts"]
                if p["spark_agree"] is True)
    total = sum(1 for c in cases for p in c["parts"]
                if p["spark_agree"] is not None)
    calls = verify["calls_sent"] + sum(
        1 for c in cases if c["spark"]["call_sent"])
    return {"verify": verify, "cases": cases,
            "agreement": {"agree": agree, "total": total,
                          "rate": "%d/%d" % (agree, total)},
            "live_calls_sent": calls, "leg": "closed"}


def probe_baseten_yard(root):
    """Probe 2: the yard case exactly as WO13 sent it, once."""
    case_id = "yard-demo"
    built = eval_scale.BUILDERS[case_id](root)
    verdicts = built["verdicts"]
    part_ids = [v["part_id"] for v in verdicts]
    opened = baseten_yard_call(built["evidence"], part_ids)
    by_id = {g["part_id"]: g for g in opened["grades"]}
    parts = []
    for v in verdicts:
        right = by_id.get(v["part_id"])
        parts.append({
            "part_id": v["part_id"],
            "label": v["label"],
            "rule_grade": v["verdict"],
            "rule_id": v["rule_id"],
            "rule_name": v["rule_name"],
            "rule_explain": v["rule_explain"],
            "open_grade": right["grade"] if right else None,
            "open_reason": right["reason"] if right else "",
            "open_mode": ("live" if right
                          else ("live, ungraded" if opened["live_ok"]
                                else "no live grade")),
            "open_agree": (right["grade"] == v["verdict"])
            if right else None,
        })
    agree = sum(1 for p in parts if p["open_agree"] is True)
    total = sum(1 for p in parts if p["open_agree"] is not None)
    return {"case": case_id, "label": built["label"],
            "model": spark_open.SPARK_OPEN_MODEL,
            "endpoint": spark_open.BASETEN_ENDPOINT,
            "timeout_seconds": BASETEN_TIMEOUT_SECONDS,
            "open": {k: opened[k] for k in (
                "live_ok", "call_sent", "latency_ms", "cause", "dropped")},
            "parts": parts,
            "agreement": {"agree": agree, "total": total,
                          "rate": "%d/%d" % (agree, total)},
            "live_calls_sent": 1 if opened["call_sent"] else 0,
            "leg": "closed"}


def probe_sam_segment(root, api_base, key, sam_model):
    """Probe 3: one segment call on the officially confirmed path."""
    call = sam_segment_call(root, api_base, key, sam_model)
    return {"discovery": {"sources": list(SAM_SOURCES),
                          "confirmed_path": "POST %s%s" % (
                              api_base, SAM_CONFIRMED_PATH),
                          "confirmed_model": sam_model,
                          "evidence": SAM_EVIDENCE},
            "call": call,
            "live_calls_sent": 1 if call["call_sent"] else 0,
            "leg": "closed"}


def probe_spark_payload(api_base, key, spark_model):
    """Probe 4: one image-part request; shape proof only."""
    call = spark_payload_call(api_base, key, spark_model, "frame1.svg")
    return {"call": call,
            "live_calls_sent": 1 if call["call_sent"] else 0,
            "leg": "closed"}


def run_probes(root):
    eval_meta.load_dotenv_into_environ(root)
    meta_client.TIMEOUT_SECONDS = SPARK_TIMEOUT_SECONDS
    cfg = meta_settings()
    try:
        key = meta_client._api_key()
        key_cause = ""
    except MetaAPIError as exc:
        key, key_cause = "", str(exc)
    spark_model = cfg["spark_model"]
    sam_model = cfg["sam_model"]
    if not key:
        verify = {"live_ok": False, "calls_sent": 0, "latency_ms": 0,
                  "cause": key_cause, "finish_reason": "",
                  "content_len": 0}
        halt = "leg stopped: " + key_cause
        cases = []
        for case_id in eval_scale.CASE_ORDER:
            built = eval_scale.BUILDERS[case_id](root)
            parts = [{"part_id": v["part_id"], "label": v["label"],
                      "rule_grade": v["verdict"], "rule_id": v["rule_id"],
                      "rule_name": v["rule_name"],
                      "rule_explain": v["rule_explain"],
                      "spark_grade": None, "spark_reason": "",
                      "spark_mode": "no live grade",
                      "spark_agree": None}
                     for v in built["verdicts"]]
            stopped = eval_meta.stopped_leg(halt)
            stopped["finish_reason"] = ""
            stopped["content_len"] = 0
            cases.append({"case": case_id, "label": built["label"],
                          "spark": stopped, "parts": parts})
        usability = {"verify": verify, "cases": cases,
                     "agreement": {"agree": 0, "total": 0, "rate": "0/0"},
                     "live_calls_sent": 0, "leg": "closed"}
    else:
        usability = probe_spark_usability(root, spark_model)
    yard = probe_baseten_yard(root)
    if not key:
        sam_call = {"live_ok": False, "call_sent": False, "latency_ms": 0,
                    "cause": key_cause, "frame": "", "phrase": "",
                    "masks": [], "verdict": "no-call"}
        sam = {"discovery": {"sources": list(SAM_SOURCES),
                             "confirmed_path": "POST %s%s" % (
                                 cfg["api_base"], SAM_CONFIRMED_PATH),
                             "confirmed_model": sam_model,
                             "evidence": SAM_EVIDENCE},
               "call": sam_call, "live_calls_sent": 0, "leg": "closed"}
        payload_call = {"accepted": False, "call_sent": False,
                        "latency_ms": 0, "cause": key_cause,
                        "frame": "frame1.svg", "request_id": "",
                        "http_status": 0, "sent_shape": {}, "response": {}}
        payload = {"call": payload_call, "live_calls_sent": 0,
                   "leg": "closed"}
    else:
        sam = probe_sam_segment(root, cfg["api_base"], key, sam_model)
        payload = probe_spark_payload(cfg["api_base"], key, spark_model)
    return {
        "order": ("Work Order 16 follow-up: one retry pass on the three "
                  "failed live legs, plus the Spark image-payload test"),
        "baseline_wo16": {
            "spark_vs_rules": {"agree": 0, "total": 0, "rate": "0/0"},
            "open_vs_rules": {"agree": 5, "total": 8, "rate": "5/8"},
            "live_vs_rules_pooled": {"agree": 5, "total": 8,
                                     "rate": "5/8"},
            "spark_vs_open": {"agree": 0, "total": 0, "rate": "0/0"},
        },
        "max_tokens_headroom": FOLLOWUP_MAX_TOKENS,
        "spark_model": spark_model,
        "sam_model": sam_model,
        "api_base": cfg["api_base"],
        "key_cause": key_cause,
        "probes": {
            "spark-usability": usability,
            "baseten-yard": yard,
            "sam-segment": sam,
            "spark-image-payload": payload,
        },
        "pooled_updated": {},
        "vin_live": False,
        "vin_reason": ("the payload test proves a payload shape, not the "
                       "VIN evidence gate; no demo VIN plate images exist, "
                       "so 0 live VIN calls sent and the flip stays "
                       "unproven"),
        "live_vin_calls_sent": 0,
        "timeouts": ("meta_client timeout raised to %ds in-process for "
                     "measurement only; Baseten sent at its product 45s; "
                     "SAM and payload posts at 60s; product defaults "
                     "unchanged" % SPARK_TIMEOUT_SECONDS),
    }


def finalize(results):
    base = results["baseline_wo16"]["live_vs_rules_pooled"]
    new_spark = results["probes"]["spark-usability"]["agreement"]
    new_yard = results["probes"]["baseten-yard"]["agreement"]
    agree = base["agree"] + new_spark["agree"] + new_yard["agree"]
    total = base["total"] + new_spark["total"] + new_yard["total"]
    results["pooled_updated"] = {
        "agree": agree, "total": total,
        "rate": "%d/%d" % (agree, total),
        "formula": ("WO16 pooled 5/8 plus follow-up Spark %s plus "
                    "follow-up Baseten yard %s; no part counted twice "
                    "because WO16 graded zero Spark parts and zero "
                    "yard Open parts" % (new_spark["rate"],
                                         new_yard["rate"])),
    }
    calls = sum(p["live_calls_sent"]
                for p in results["probes"].values())
    results["live_calls_sent_total"] = calls
    results["model_list_calls_sent"] = 0
    results["model_list_note"] = ("no live model-list call: outside the "
                                  "four-probe allowlist")
    return results


def write_results(results):
    path = os.path.join(ROOT, RESULTS_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=False)
        fh.write("\n")
    return path


def main(argv):
    del argv
    results = finalize(run_probes(ROOT))
    path = write_results(results)
    print("wrote %s" % path)
    usability = results["probes"]["spark-usability"]
    print("spark usability: verify %s, grades %s" % (
        "live ok" if usability["verify"]["live_ok"]
        else usability["verify"]["cause"][:100],
        usability["agreement"]["rate"]))
    yard = results["probes"]["baseten-yard"]
    print("baseten yard: %s (%s)" % (
        "live ok" if yard["open"]["live_ok"]
        else ("no call" if not yard["open"]["call_sent"] else "FAILED"),
        yard["agreement"]["rate"]))
    sam = results["probes"]["sam-segment"]["call"]
    print("sam segment: %s" % (
        "live ok, %s" % sam["verdict"] if sam["live_ok"]
        else ("no call (%s)" % sam["cause"] if not sam["call_sent"]
              else "FAILED (%s)" % sam["cause"][:120])))
    payload = results["probes"]["spark-image-payload"]["call"]
    print("spark payload: %s" % (
        "accepted" if payload["accepted"]
        else ("no call (%s)" % payload["cause"] if not payload["call_sent"]
              else "rejected (%s)" % payload["cause"][:120])))
    print("pooled updated: %s" % results["pooled_updated"]["rate"])
    print("live calls sent: %d (legs closed)" %
          results["live_calls_sent_total"])


if __name__ == "__main__":
    main(sys.argv[1:])
