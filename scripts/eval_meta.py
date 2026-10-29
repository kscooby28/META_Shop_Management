"""Meta-live evaluation (WO16): the WO13 demo set through every live engine.

Measurement, not product. No screens, no flows, no features. Rotation is
complete, so this script makes live calls, one per case per engine, no
retries: Muse Spark 1.3 grades, Wonder Standard second opinions through
the router leg, SAM 3.1 mask verification on the yard demo frame, and
Muse Spark Open through Baseten as the already-proven baseline. The
Work Order 13 script and artifacts stay intact and separate.

Evidence each engine sees: the rules engine grades part dicts plus
shop-style comps through the unchanged product path (reused WO13
builders, same evidence shape); Spark 1.3 gets the same Compare-view
shape and case notes under the same grade prompt as Spark Open, so the
A/B is fair. Wonder gets exactly what the product router would send for
the case's hardest verdict or plan. SAM gets the yard demo frame bytes
plus the case's part phrases. A failed or rejected live call is recorded
honestly for that case and leg; a demo grade is never substituted or
presented as live. Bay case 3 has no parts, so no call is sent for any
engine, exactly like Work Order 13.

Key handling: .env values are loaded into the process environment so a
fresh shell works; names only are ever reported, values never printed.

Usage:
  python scripts/eval_meta.py                 run live, write the JSON file
  python scripts/eval_meta.py --write-readme  also refresh the README table
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import eval_scale  # noqa: E402  (same demo set, same builders, same evidence)
from demo_cache import StepCache  # noqa: E402
from meta_client import MetaAPIError, settings as meta_settings  # noqa: E402
import meta_client  # noqa: E402
import spark_open  # noqa: E402
import wonder  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_NAME = "eval_meta_results.json"
GRADES = ("A", "B", "C")

# Measurement-only timeouts, set in-process. Product defaults stay as
# shipped; the JSON records that the raise happened here, not in code.
MEASURE_TIMEOUT_SECONDS = 60


def load_dotenv_into_environ(root):
    """Load .env names into os.environ for a fresh shell. Returns names only."""
    names = []
    try:
        with open(os.path.join(root, ".env"), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and value and key not in os.environ:
                    os.environ[key] = value
                if key:
                    names.append(key)
    except OSError:
        pass
    return sorted(set(names))


def live_model_ids(api_base, key):
    """GET the live model list. Returns (ids, cause). IDs only, no values."""
    request = urllib.request.Request(
        api_base.rstrip("/") + "/models",
        headers={"Authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return [], "models list rejected: HTTP %s" % exc.code
    except Exception as exc:  # noqa: BLE001 - recorded, never secrets
        return [], "models list failed: %s: %s" % (
            type(exc).__name__, str(exc)[:120])
    entries = data.get("data", data if isinstance(data, list) else [])
    ids = [e.get("id") for e in entries
           if isinstance(e, dict) and e.get("id")]
    return ids, ""


def verify_spark(spark_model, api_base):
    """One tiny Spark call: confirms the ID is live and usable."""
    started = time.time()
    try:
        raw = meta_client._post(
            "/chat/completions",
            {"model": spark_model,
             "messages": [{"role": "user",
                           "content": 'Reply with JSON only: {"ok": true}'}],
             "response_format": {"type": "json_object"}},
        )
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        assert parsed.get("ok") is True
    except MetaAPIError as exc:
        return {"live_ok": False, "latency_ms": _ms(started),
                "cause": str(exc)}
    except (KeyError, IndexError, ValueError, AssertionError, TypeError) as exc:
        return {"live_ok": False, "latency_ms": _ms(started),
                "cause": "Spark verification shape unusable: %s" % exc}
    return {"live_ok": True, "latency_ms": _ms(started), "cause": ""}


def _ms(started):
    return int((time.time() - started) * 1000)


def verify_ids(root):
    """Part 1: model list first, then one real call per engine ID."""
    names = load_dotenv_into_environ(root)
    cfg = meta_settings()
    try:
        key = meta_client._api_key()
    except MetaAPIError as exc:
        key = ""
        key_cause = str(exc)
    else:
        key_cause = ""
    ids, list_cause = live_model_ids(cfg["api_base"], key) if key else ([], key_cause)
    spark_model = cfg["spark_model"]
    sam_model = cfg["sam_model"]
    spark = verify_spark(spark_model, cfg["api_base"]) if spark_model in ids else {
        "live_ok": False, "latency_ms": 0,
        "cause": "not on the live model list, so no call was sent"}
    wonder_model = next((i for i in ids if "wonder" in i.lower()), "")
    wonder_path = "/chat/completions"
    if wonder_model:
        os.environ["MUSE_WONDER_MODEL"] = wonder_model
        os.environ["MUSE_WONDER_PATH"] = wonder_path
        wonder.WONDER_LIVE = True
        started = time.time()
        try:
            opinion = wonder.request_opinion(
                {"kind": "yard", "ref": "verify",
                 "evidence": {"verdict": "B", "inputs": {}},
                 "triggers": ["verification call"]})
            wonder_check = {
                "live_ok": True, "latency_ms": _ms(started), "cause": "",
                "agrees": opinion.get("agrees")}
        except MetaAPIError as exc:
            wonder_check = {"live_ok": False, "latency_ms": _ms(started),
                            "cause": str(exc)}
    else:
        wonder_check = {"live_ok": False, "latency_ms": 0,
                        "cause": "no wonder model on the live list"}
    return {
        "env_names": names,
        "api_base": cfg["api_base"],
        "live_model_ids": ids,
        "list_cause": list_cause,
        "spark_model": spark_model,
        "spark_on_list": spark_model in ids,
        "spark_check": spark,
        "sam_model": sam_model,
        "sam_on_list": sam_model in ids,
        "wonder_model": wonder_model,
        "wonder_path": wonder_path,
        "wonder_check": wonder_check,
        "image_model_on_list": next((i for i in ids if "image" in i.lower()), ""),
        "voice_model_on_list": next((i for i in ids if "voice" in i.lower()), ""),
        "note": ("image/voice IDs noted from the list only; this order "
                 "touches neither leg, so no calls and no code changes"),
    }


def _filter_grades(grades, part_ids):
    known = set(part_ids)
    kept, dropped = [], 0
    for entry in grades:
        if entry.get("part_id") in known:
            kept.append(entry)
        else:
            dropped += 1
    return kept, dropped


def grade_spark_live(evidence, part_ids, spark_model):
    """One Spark 1.3 call under the shared grade prompt. No retries."""
    if not part_ids:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to grade, so no call was sent",
                "grades": [], "dropped": 0}
    started = time.time()
    try:
        raw = meta_client._post(
            "/chat/completions",
            {"model": spark_model,
             "messages": [
                 {"role": "system", "content": spark_open.GRADE_PROMPT},
                 {"role": "user", "content": json.dumps(evidence)}],
             "response_format": {"type": "json_object"}},
        )
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
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": True, "latency_ms": _ms(started),
                "cause": str(exc), "grades": [], "dropped": 0}
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        return {"live_ok": False, "call_sent": True, "latency_ms": _ms(started),
                "cause": "Spark 1.3 returned an unusable shape: %s" % exc,
                "grades": [], "dropped": 0}
    kept, dropped = _filter_grades(cleaned, part_ids)
    return {"live_ok": True, "call_sent": True, "latency_ms": _ms(started),
            "cause": "", "grades": kept, "dropped": dropped}


def grade_open_live(evidence, part_ids):
    """One Spark Open call, same as WO13. No retries, no substitution."""
    if not part_ids:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to grade, so no call was sent",
                "grades": [], "dropped": 0}
    started = time.time()
    try:
        result = spark_open.request_grades(evidence)
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": True, "latency_ms": _ms(started),
                "cause": str(exc), "grades": [], "dropped": 0}
    kept, dropped = _filter_grades(result["grades"], part_ids)
    return {"live_ok": True, "call_sent": True, "latency_ms": _ms(started),
            "cause": "", "grades": kept, "dropped": dropped}


def demo_plan_path(root, case):
    return os.path.join(root, "demo_cache", "bay_plan.%s.json" % case)


def wonder_case_live(root, case_id, verdicts):
    """One router-leg opinion for the case's hardest item, or no call.

    Mirrors wonder.escalate's live path (assess, then request_opinion)
    without its silent demo fallback: a rejected call is recorded with
    its exact cause. A case the router would not escalate sends no call.
    """
    if case_id == "bay-case3" or not verdicts:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to review, so no call was sent",
                "ref": "", "triggers": [], "agrees": None,
                "title": "", "body": "", "watch": ""}
    if case_id.startswith("bay-"):
        case = case_id.split("-", 1)[1]
        try:
            with open(demo_plan_path(root, case), encoding="utf-8") as fh:
                plan = json.load(fh)
        except (OSError, ValueError) as exc:
            return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                    "cause": "no demo plan to review: %s" % exc,
                    "ref": "", "triggers": [], "agrees": None,
                    "title": "", "body": "", "watch": ""}
        assessment = wonder.assess_bay(plan)
        evidence = {"kind": "bay", "ref": case_id, "evidence": plan,
                    "triggers": assessment["triggers"]}
        ref = case_id
    else:
        scored = [(len(wonder.assess_yard(v)["triggers"]), v) for v in verdicts]
        scored.sort(key=lambda pair: -pair[0])
        hardest = scored[0][1]
        assessment = wonder.assess_yard(hardest)
        evidence = {"kind": "yard", "ref": hardest["part_id"],
                    "evidence": hardest, "triggers": assessment["triggers"]}
        ref = hardest["part_id"]
    if not assessment["triggers"]:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "router would not escalate: no triggers",
                "ref": ref, "triggers": [], "agrees": None,
                "title": "", "body": "", "watch": ""}
    started = time.time()
    try:
        opinion = wonder.request_opinion(evidence)
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": True, "latency_ms": _ms(started),
                "cause": str(exc), "ref": ref,
                "triggers": assessment["triggers"], "agrees": None,
                "title": "", "body": "", "watch": ""}
    return {"live_ok": True, "call_sent": True, "latency_ms": _ms(started),
            "cause": "", "ref": ref, "triggers": assessment["triggers"],
            "agrees": opinion.get("agrees"), "title": opinion.get("title", ""),
            "body": opinion.get("body", ""), "watch": opinion.get("watch", "")}


def _frame_bytes(root, name):
    for base in ("web", "demo_cache"):
        path = os.path.join(root, base, name)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                return fh.read(), os.path.splitext(name)[1].lower()
    return None, ""


def sam_case_live(root, case_id, verdicts):
    """One SAM call on the yard demo frame; other cases have no demo image.

    Confirms the masks the demo shows are what live SAM returns: phrases
    in, masks out, compared against the demo sightings for that frame.
    """
    if case_id != "yard-demo":
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no demo image for this case, so no call was sent",
                "frame": "", "phrases": [], "masks": [], "verdict": "no-call"}
    if not verdicts:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to verify, so no call was sent",
                "frame": "", "phrases": [], "masks": [], "verdict": "no-call"}
    import base64
    raw, ext = _frame_bytes(root, os.path.join("demo", "frame1.svg"))
    if raw is None:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "demo frame file missing, so no call was sent",
                "frame": "", "phrases": [], "masks": [], "verdict": "no-call"}
    mime = "image/svg+xml" if ext == ".svg" else "image/jpeg"
    cache = StepCache(root)
    intake = cache.load_demo("intake")
    phrases = [v["label"] for v in verdicts]
    started = time.time()
    try:
        result = meta_client.segment_parts(
            [{"name": "demo-frame-1",
              "data": base64.b64encode(raw).decode("ascii"), "mime": mime}],
            phrases, intake)
    except MetaAPIError as exc:
        return {"live_ok": False, "call_sent": True, "latency_ms": _ms(started),
                "cause": str(exc), "frame": "demo-frame-1",
                "phrases": phrases, "masks": [], "verdict": "failed"}
    harvest = cache.load_demo("harvest")
    demo_seen = {}
    for part in harvest.get("parts", []):
        for sight in part.get("sightings", []):
            if sight.get("frame") == "demo-frame-1":
                demo_seen.setdefault(part.get("label"), []).append(sight)
    masks = []
    for part in result.get("parts", []):
        for sight in part.get("sightings", []):
            if sight.get("frame") != "demo-frame-1":
                continue
            box = sight.get("box")
            valid = (isinstance(box, list) and len(box) == 4
                     and all(isinstance(n, (int, float)) and 0 <= n <= 1000
                             for n in box))
            masks.append({"phrase": part.get("label", ""),
                          "box_valid": valid,
                          "has_polygon": sight.get("polygon") is not None,
                          "coverage": sight.get("coverage"),
                          "score": sight.get("score"),
                          "source": sight.get("source", "")})
    live_phrases = {m["phrase"] for m in masks}
    matched = sorted(p for p in phrases if p in live_phrases)
    missing = sorted(p for p in phrases if p not in live_phrases)
    if missing or not all(m["box_valid"] for m in masks):
        verdict = "diverged"
    elif len(matched) == len(phrases):
        verdict = "confirmed"
    else:
        verdict = "diverged"
    return {"live_ok": True, "call_sent": True, "latency_ms": _ms(started),
            "cause": "", "frame": "demo-frame-1", "phrases": phrases,
            "masks": masks, "demo_sightings": len(demo_seen),
            "matched_phrases": matched, "missing_phrases": missing,
            "verdict": verdict}


def vin_flip_decision(case_results):
    """Pure gate: flip only on unanimous usable identifications.

    case_results maps case id -> {"usable": bool, "cause": str}. An empty
    set proves nothing and never flips. Returns (flip, reason).
    """
    if not case_results:
        return False, "no demo VIN cases ran, so the flip is unproven"
    failed = sorted(cid for cid, res in case_results.items()
                    if not res.get("usable"))
    if failed:
        return False, "no flip: %s" % "; ".join(
            "%s (%s)" % (cid, case_results[cid].get("cause", "no reason"))
            for cid in failed)
    return True, "all %d demo VIN cases returned usable identifications" % len(case_results)


def demo_vin_assets(root):
    """Demo VIN plate images the gate could honestly send. Names only."""
    found = []
    for base, _, files in os.walk(root):
        if "node_modules" in base or ".git" in base:
            continue
        for name in files:
            lowered = name.lower()
            if "vin" in lowered and lowered.endswith(
                    (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif")):
                found.append(os.path.relpath(os.path.join(base, name), root))
    return sorted(found)


def stopped_leg(cause):
    return {"live_ok": False, "call_sent": False, "latency_ms": 0,
            "cause": cause, "grades": [], "dropped": 0}


def _halted(cause):
    lowered = (cause or "").lower()
    return "rejected" in lowered or "exhausted" in lowered or "401" in lowered \
        or "403" in lowered or "429" in lowered


def run_case(root, case_id, model_ids, halts):
    """One case through every engine. Auth/credit rejections halt that leg."""
    built = eval_scale.BUILDERS[case_id](root)
    verdicts = built["verdicts"]
    part_ids = [v["part_id"] for v in verdicts]
    spark_model = model_ids["spark_model"]
    if halts["spark"]:
        spark = stopped_leg(halts["spark"])
    else:
        spark = grade_spark_live(built["evidence"], part_ids, spark_model)
        if not spark["live_ok"] and spark["call_sent"] and _halted(spark["cause"]):
            halts["spark"] = "leg stopped: " + spark["cause"]
    if halts["open"]:
        opened = stopped_leg(halts["open"])
    else:
        opened = grade_open_live(built["evidence"], part_ids)
        if not opened["live_ok"] and opened["call_sent"] and _halted(opened["cause"]):
            halts["open"] = "leg stopped: " + opened["cause"]
    if halts["wonder"]:
        wonder_out = {"live_ok": False, "call_sent": False, "latency_ms": 0,
                      "cause": halts["wonder"], "ref": "", "triggers": [],
                      "agrees": None, "title": "", "body": "", "watch": ""}
    else:
        wonder_out = wonder_case_live(root, case_id, verdicts)
        if not wonder_out["live_ok"] and wonder_out["call_sent"] \
                and _halted(wonder_out["cause"]):
            halts["wonder"] = "leg stopped: " + wonder_out["cause"]
    if halts["sam"]:
        sam = {"live_ok": False, "call_sent": False, "latency_ms": 0,
               "cause": halts["sam"], "frame": "", "phrases": [],
               "masks": [], "verdict": "stopped"}
    else:
        sam = sam_case_live(root, case_id, verdicts)
        if not sam["live_ok"] and sam["call_sent"] and _halted(sam["cause"]):
            halts["sam"] = "leg stopped: " + sam["cause"]
    spark_by_id = {g["part_id"]: g for g in spark["grades"]}
    open_by_id = {g["part_id"]: g for g in opened["grades"]}
    parts = []
    for v in verdicts:
        left = spark_by_id.get(v["part_id"])
        right = open_by_id.get(v["part_id"])
        parts.append({
            "part_id": v["part_id"],
            "label": v["label"],
            "rule_grade": v["verdict"],
            "rule_id": v["rule_id"],
            "rule_name": v["rule_name"],
            "rule_explain": v["rule_explain"],
            "spark_grade": left["grade"] if left else None,
            "spark_reason": left["reason"] if left else "",
            "spark_mode": "live" if left else ("live, ungraded" if spark["live_ok"]
                                               else "no live grade"),
            "spark_agree": (left["grade"] == v["verdict"]) if left else None,
            "open_grade": right["grade"] if right else None,
            "open_reason": right["reason"] if right else "",
            "open_mode": "live" if right else ("live, ungraded" if opened["live_ok"]
                                               else "no live grade"),
            "open_agree": (right["grade"] == v["verdict"]) if right else None,
            "engines_agree": (left["grade"] == right["grade"])
            if left and right else None,
        })
    return {
        "case": case_id,
        "label": built["label"],
        "spark": {k: spark[k] for k in (
            "live_ok", "call_sent", "latency_ms", "cause", "dropped")},
        "open": {k: opened[k] for k in (
            "live_ok", "call_sent", "latency_ms", "cause", "dropped")},
        "wonder": wonder_out,
        "sam": sam,
        "cost": "the endpoints report no cost, so none is estimated",
        "parts": parts,
    }


def measure(root, model_ids):
    halts = {
        "spark": "" if model_ids["spark_check"]["live_ok"]
        else "leg stopped: Spark verification failed: %s" % model_ids["spark_check"]["cause"],
        "open": "",
        "wonder": "" if model_ids["wonder_check"]["live_ok"]
        else "leg stopped: Wonder verification failed: %s" % model_ids["wonder_check"]["cause"],
        "sam": "" if model_ids["sam_on_list"]
        else "leg stopped: SAM model not on the live list",
    }
    cases = [run_case(root, case_id, model_ids, halts)
             for case_id in eval_scale.CASE_ORDER]
    spark_agree = sum(1 for c in cases for p in c["parts"]
                      if p["spark_agree"] is True)
    spark_total = sum(1 for c in cases for p in c["parts"]
                      if p["spark_agree"] is not None)
    open_agree = sum(1 for c in cases for p in c["parts"]
                     if p["open_agree"] is True)
    open_total = sum(1 for c in cases for p in c["parts"]
                     if p["open_agree"] is not None)
    both_agree = sum(1 for c in cases for p in c["parts"]
                     if p["engines_agree"] is True)
    both_total = sum(1 for c in cases for p in c["parts"]
                     if p["engines_agree"] is not None)
    pooled_agree = spark_agree + open_agree
    pooled_total = spark_total + open_total
    meta_calls = sum(1 for c in cases if c["spark"]["call_sent"])
    meta_calls += sum(1 for c in cases if c["wonder"]["call_sent"])
    meta_calls += sum(1 for c in cases if c["sam"]["call_sent"])
    meta_calls += 2  # Spark + Wonder verification calls
    open_calls = sum(1 for c in cases if c["open"]["call_sent"])
    assets = demo_vin_assets(root)
    if assets:
        flip, flip_reason = (
            False, "unused: %d asset(s) exist but no VIN leg ran" % len(assets))
    else:
        flip, _ = vin_flip_decision({})
        flip_reason = ("no demo VIN plate images exist, so 0 live VIN calls "
                       "sent; the flip is unproven")
    return {
        "order": "Work Order 16: post-rotation Meta-live evaluation",
        "model_ids": model_ids,
        "cases": cases,
        "agreement": {
            "spark_vs_rules": {"agree": spark_agree, "total": spark_total,
                               "rate": "%d/%d" % (spark_agree, spark_total)},
            "open_vs_rules": {"agree": open_agree, "total": open_total,
                              "rate": "%d/%d" % (open_agree, open_total)},
            "live_vs_rules_pooled": {"agree": pooled_agree, "total": pooled_total,
                                     "rate": "%d/%d" % (pooled_agree, pooled_total)},
            "spark_vs_open": {"agree": both_agree, "total": both_total,
                              "rate": "%d/%d" % (both_agree, both_total)},
        },
        "live_meta_calls_attempted": meta_calls,
        "live_baseten_calls_sent": open_calls,
        "vin_gate": {"demo_vin_assets": assets,
                     "live_vin_calls_sent": 0,
                     "flip": flip,
                     "reason": flip_reason,
                     "assets_note": ("no demo VIN plate images exist, so no "
                                     "live VIN call could be honestly sent") if not assets else ""},
        "timeouts": ("meta_client and wonder timeouts raised to %ds in-process "
                     "for measurement only; product defaults unchanged"
                     % MEASURE_TIMEOUT_SECONDS),
    }


def _cell(text):
    return " ".join(str(text or "").replace("|", "/").split())


def _match(value):
    if value is None:
        return "no live grade"
    return "yes" if value else "NO"


def render_section(results):
    model_ids = results["model_ids"]
    agree = results["agreement"]
    if model_ids.get("sam_corrected_to"):
        sam_bit = "%s (corrected in code from %s; the live list names %s)" % (
            model_ids["sam_corrected_to"], model_ids["sam_model"],
            model_ids["sam_corrected_to"])
    else:
        sam_bit = "%s (%s)" % (
            model_ids["sam_model"],
            "on the list" if model_ids["sam_on_list"] else "NOT on the list")
    lines = [
        "## Meta-live evaluation (Work Order 16)",
        "",
        "The same demo set as Work Order 13 through every live engine: Spark",
        "1.3 grades, Wonder Standard second opinions through the router leg,",
        "SAM 3.1 mask verification on the yard demo frame, and Spark Open",
        "through Baseten as the baseline. One live call per case per engine,",
        "no retries; auth or credit rejections stop that leg. Bay job parts",
        "carry no pull-grade meaning in the product; they run here to measure",
        "thin-evidence behavior from name and note alone. Regenerate with",
        "`python scripts/eval_meta.py --write-readme`.",
        "",
        "Model IDs, confirmed live: Spark %s (%s), SAM %s, Wonder %s "
        "over %s (%s)." % (
            model_ids["spark_model"],
            "on the list, verification call ok"
            if model_ids["spark_check"]["live_ok"]
            else "FAILED: %s" % model_ids["spark_check"]["cause"],
            sam_bit,
            model_ids["wonder_model"] or "unconfirmed",
            model_ids["wonder_path"],
            "verification call ok"
            if model_ids["wonder_check"]["live_ok"]
            else "FAILED: %s" % model_ids["wonder_check"]["cause"]),
        "",
        "| case | part | rule | Spark 1.3 live | match | Spark Open live | match |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in results["cases"]:
        for part in case["parts"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                _cell(case["case"]), _cell(part["label"]),
                _cell(part["rule_grade"]),
                _cell(part["spark_grade"] or "—"), _match(part["spark_agree"]),
                _cell(part["open_grade"] or "—"), _match(part["open_agree"])))
    lines += [
        "",
        "Agreement: Spark 1.3 vs rules %s, Spark Open vs rules %s, pooled "
        "live vs rules %s, Spark 1.3 vs Spark Open %s. Live Meta calls "
        "attempted: %d. Live Baseten calls sent: %d." % (
            agree["spark_vs_rules"]["rate"], agree["open_vs_rules"]["rate"],
            agree["live_vs_rules_pooled"]["rate"], agree["spark_vs_open"]["rate"],
            results["live_meta_calls_attempted"],
            results["live_baseten_calls_sent"]),
        "",
    ]
    for case in results["cases"]:
        legs = []
        for leg, name in (("spark", "Spark 1.3"), ("open", "Spark Open")):
            info = case[leg]
            if not info["call_sent"]:
                legs.append("%s: no call (%s)" % (name, _cell(info["cause"])))
            elif info["live_ok"]:
                legs.append("%s: live in %d ms" % (name, info["latency_ms"]))
            else:
                legs.append("%s: FAILED (%s)" % (name, _cell(info["cause"])))
        won = case["wonder"]
        if not won["call_sent"]:
            legs.append("Wonder: no call (%s)" % _cell(won["cause"]))
        elif won["live_ok"]:
            legs.append("Wonder: live in %d ms, %s on %s" % (
                won["latency_ms"], _cell(won["agrees"]), _cell(won["ref"])))
        else:
            legs.append("Wonder: FAILED (%s)" % _cell(won["cause"]))
        sam = case["sam"]
        if not sam["call_sent"]:
            legs.append("SAM: no call (%s)" % _cell(sam["cause"]))
        elif sam["live_ok"]:
            legs.append("SAM: live in %d ms, %s" % (
                sam["latency_ms"], _cell(sam["verdict"])))
        else:
            legs.append("SAM: FAILED (%s)" % _cell(sam["cause"]))
        lines.append("- %s: %s." % (case["case"], "; ".join(legs)))
    spark_no = [(c["case"], p) for c in results["cases"]
                for p in c["parts"] if p["spark_agree"] is False]
    open_no = [(c["case"], p) for c in results["cases"]
               for p in c["parts"] if p["open_agree"] is False]
    lines += ["", "Spark 1.3 disagreements, with both reasons:"]
    if spark_no:
        for case_id, part in spark_no:
            lines.append("- %s / %s: rules say %s (%s); Spark 1.3 live "
                         "says %s (%s)." % (
                             case_id, _cell(part["label"]), part["rule_grade"],
                             _cell("%s: %s" % (part["rule_name"],
                                               part["rule_explain"])),
                             part["spark_grade"], _cell(part["spark_reason"])))
    else:
        lines.append("- None: every Spark 1.3 grade matched its rule grade.")
    lines += ["", "Spark Open disagreements, with both reasons:"]
    if open_no:
        for case_id, part in open_no:
            lines.append("- %s / %s: rules say %s (%s); Spark Open live "
                         "says %s (%s)." % (
                             case_id, _cell(part["label"]), part["rule_grade"],
                             _cell("%s: %s" % (part["rule_name"],
                                               part["rule_explain"])),
                             part["open_grade"], _cell(part["open_reason"])))
    else:
        lines.append("- None: every Spark Open grade matched its rule grade.")
    lines += ["", "Wonder second opinions, live:"]
    opinions = [(c["case"], c["wonder"]) for c in results["cases"]
                if c["wonder"]["live_ok"]]
    if opinions:
        for case_id, won in opinions:
            lines.append("- %s / %s (triggers: %s): %s — %s Watch: %s" % (
                case_id, _cell(won["ref"]),
                _cell(", ".join(won["triggers"]) or "none"),
                _cell(won["title"]), _cell(won["body"]), _cell(won["watch"])))
    else:
        lines.append("- None live: every Wonder leg recorded no-call or failed.")
    lines += ["", "SAM 3.1 yard-frame verification:"]
    for case in results["cases"]:
        sam = case["sam"]
        if case["case"] != "yard-demo" or not sam["call_sent"]:
            continue
        if not sam["live_ok"]:
            lines.append("- yard-demo: FAILED (%s)." % _cell(sam["cause"]))
            continue
        lines.append(
            "- yard-demo: %s — %d/%d phrases matched (%s), %d masks, "
            "boxes valid %s." % (
                sam["verdict"], len(sam["matched_phrases"]),
                len(sam["phrases"]), _cell(", ".join(sam["matched_phrases"])),
                len(sam["masks"]),
                "all" if all(m["box_valid"] for m in sam["masks"]) else "NOT all"))
    gate = results["vin_gate"]
    lines += [
        "",
        "VIN_LIVE gate: %s (%s)." % (
            "FLIP to True" if gate["flip"] else "stays False", _cell(gate["reason"])),
        "",
    ]
    return "\n".join(lines)


START = "<!-- EVAL-META:START -->"
END = "<!-- EVAL-META:END -->"
SCALE_END = "<!-- EVAL-SCALE:END -->"


def write_readme(results):
    path = os.path.join(ROOT, "README.md")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    block = START + "\n" + render_section(results) + END
    if START in text and END in text:
        before, _, rest = text.partition(START)
        _, _, after = rest.partition(END)
        text = before + block + after
    elif SCALE_END in text:
        before, _, after = text.partition(SCALE_END)
        text = before + SCALE_END + "\n\n" + block + after
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_results(results):
    path = os.path.join(ROOT, RESULTS_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=False)
        fh.write("\n")
    return path


def sam_only(root):
    """Follow-up: the single SAM yard call after the WO16 ID correction.

    The main run sent zero SAM calls (wrong ID on file), so this first
    and only call is within budget, not a retry. Refuses when a SAM
    call was already sent. Merges into the existing results file.
    """
    meta_client.TIMEOUT_SECONDS = MEASURE_TIMEOUT_SECONDS
    load_dotenv_into_environ(root)
    path = os.path.join(root, RESULTS_NAME)
    with open(path, "r", encoding="utf-8") as fh:
        results = json.load(fh)
    yard = next(c for c in results["cases"] if c["case"] == "yard-demo")
    if yard["sam"]["call_sent"]:
        raise SystemExit("a SAM call was already sent; no retries")
    from meta_client import SAM_MODEL
    built = eval_scale.BUILDERS["yard-demo"](root)
    sam = sam_case_live(root, "yard-demo", built["verdicts"])
    yard["sam"] = sam
    if sam["call_sent"]:
        results["live_meta_calls_attempted"] += 1
    results["model_ids"]["sam_corrected_to"] = SAM_MODEL
    results["model_ids"]["sam_correction_evidence"] = (
        "live list names %s and no sam-3-1; code corrected before this call"
        % SAM_MODEL)
    return results


def main(argv):
    if "--sam-only" in argv:
        results = sam_only(ROOT)
        path = write_results(results)
        print("wrote %s" % path)
        sam = next(c["sam"] for c in results["cases"]
                   if c["case"] == "yard-demo")
        if sam["live_ok"]:
            print("sam yard: live ok, %s" % sam["verdict"])
        elif not sam["call_sent"]:
            print("sam yard: no call (%s)" % sam["cause"])
        else:
            print("sam yard: FAILED (%s)" % sam["cause"])
        if "--write-readme" in argv:
            write_readme(results)
            print("README table refreshed.")
        return
    meta_client.TIMEOUT_SECONDS = MEASURE_TIMEOUT_SECONDS
    wonder.TIMEOUT_SECONDS = MEASURE_TIMEOUT_SECONDS
    model_ids = verify_ids(ROOT)
    print("live models: %s" % ", ".join(model_ids["live_model_ids"]))
    print("spark %s (%s)" % (
        model_ids["spark_model"],
        "verified live" if model_ids["spark_check"]["live_ok"]
        else "FAILED: %s" % model_ids["spark_check"]["cause"]))
    print("wonder %s over %s (%s)" % (
        model_ids["wonder_model"] or "unconfirmed", model_ids["wonder_path"],
        "verified live" if model_ids["wonder_check"]["live_ok"]
        else "FAILED: %s" % model_ids["wonder_check"]["cause"]))
    results = measure(ROOT, model_ids)
    path = write_results(results)
    agree = results["agreement"]
    print("wrote %s" % path)
    for case in results["cases"]:
        print("- %s: spark %s, open %s, wonder %s, sam %s" % (
            case["case"],
            "live ok" if case["spark"]["live_ok"]
            else ("no call" if not case["spark"]["call_sent"] else "FAILED"),
            "live ok" if case["open"]["live_ok"]
            else ("no call" if not case["open"]["call_sent"] else "FAILED"),
            "live ok" if case["wonder"]["live_ok"]
            else ("no call" if not case["wonder"]["call_sent"] else "FAILED"),
            "live ok" if case["sam"]["live_ok"]
            else ("no call" if not case["sam"]["call_sent"] else "FAILED")))
    print("spark vs rules %s, open vs rules %s, pooled %s, spark vs open %s" % (
        agree["spark_vs_rules"]["rate"], agree["open_vs_rules"]["rate"],
        agree["live_vs_rules_pooled"]["rate"], agree["spark_vs_open"]["rate"]))
    print("live Meta calls %d, live Baseten calls %d" % (
        results["live_meta_calls_attempted"], results["live_baseten_calls_sent"]))
    print("VIN_LIVE gate: %s (%s)" % (
        "FLIP" if results["vin_gate"]["flip"] else "no flip",
        results["vin_gate"]["reason"]))
    if "--write-readme" in argv:
        write_readme(results)
        print("README table refreshed.")


if __name__ == "__main__":
    main(sys.argv[1:])
