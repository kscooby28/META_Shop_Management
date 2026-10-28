"""Bay side (shop-manager core): intake, test-plan engine, parts, labor, KB.

Additive to the Yard side: same honesty rules (source tags or an honest
"we lack reliable data"), same demo-cache law, same Shop Copilot panel.
No bundled factory content anywhere: plans come from Spark live, from the
anonymized demo cache, or from shop-entered tests. Labor times come only
from shop standards or shop-set estimates at $180/hr.
"""

import glob
import json
import os

from verdict import render_decline

LABOR_RATE = 180
SHOP_MAKES = ("bmw", "porsche", "volvo")

# Live VIN identification stays OFF until the owner confirms the Meta API key
# has been rotated. While False, every VIN path serves demo cache / manual
# entry and never calls the live API. Flipping this flag later changes the
# data source only; the interface does not change.
VIN_LIVE = False
AREAS = ("engine", "gearbox", "electrical", "brakes", "suspension", "maintenance", "other", "not sure")

# Visible keyword lists the decline matcher uses. Small and plain on purpose:
# matching is a shop policy gate, not a diagnosis.
NO_START_KEYWORDS = (
    "no-start",
    "no start",
    "won't start",
    "wont start",
    "doesn't start",
    "doesnt start",
    "crank no start",
    "cranks but won't start",
    "not starting",
)
OIL_CHANGE_KEYWORDS = ("oil change", "oil-change", "oil service")

# Score weights: visible beside every test, same idea as verdict rule inputs.
WEIGHTS = {
    "symptom_match": 3,
    "code_match": 3,
    "rules_out_expensive": 2,
    "quick": 1,
    "suspected_cause": 5,
    "eliminated_penalty": -1000,
}


def load_bay_case(kind, case, root):
    """Load demo_cache/bay_<kind>.<case>.json (anonymized Bay samples)."""
    path = os.path.join(root, "demo_cache", "bay_%s.%s.json" % (kind, case))
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# -- intake ------------------------------------------------------------

def validate_intake(manual):
    """Return a list of plain-words problems; empty means valid."""
    problems = []
    if not isinstance(manual, dict):
        return ["the case form arrived empty"]
    vehicle = manual.get("vehicle", manual)
    if not isinstance(vehicle, dict):
        return ["the vehicle block arrived broken"]
    year = vehicle.get("year")
    if year in (None, ""):
        problems.append("add the model year")
    else:
        try:
            year = int(year)
            if year < 1990 or year > 2031:
                problems.append("the year %r looks wrong" % (vehicle.get("year"),))
        except (TypeError, ValueError):
            problems.append("the year %r looks wrong" % (vehicle.get("year"),))
    for field in ("make", "model"):
        if not (vehicle.get(field) or "").strip():
            problems.append("add the vehicle %s" % field)
    if not (manual.get("symptom") or "").strip():
        problems.append("describe the symptom in your own words")
    codes = manual.get("codes")
    if codes is None:
        pass
    elif not isinstance(codes, list) or any(not isinstance(c, str) for c in codes):
        problems.append("fault codes must arrive as a list of text codes")
    area = (manual.get("area") or "not sure").strip().lower()
    if area not in AREAS:
        problems.append("area must be one of: %s" % ", ".join(AREAS))
    return problems


def categorize(vehicle):
    """Put the car into its category. Returns category + notes + source tags."""
    make = (vehicle.get("make") or "").strip()
    model = (vehicle.get("model") or "").strip()
    year = vehicle.get("year", "")
    line = model or "unknown line"
    category = "%s · %s" % (make or "unknown make", line)
    notes = []
    make_key = make.split("(")[0].strip().lower()  # "BMW (demo sample)" still matches BMW
    shop_make = make_key in SHOP_MAKES
    if not shop_make:
        notes.append(
            "This make is outside the shop's BMW / Porsche / Volvo focus, "
            "so treat the plan as general guidance and confirm everything."
        )
    trim = (vehicle.get("trim") or "").strip()
    if not trim:
        notes.append("Trim stays unknown: no badge is readable, so none is claimed.")
    return {
        "category": category,
        "year": year,
        "make": make or "unknown",
        "model": model or "unknown",
        "trim": trim or "unknown",
        "engine": (vehicle.get("engine") or "").strip() or "unknown",
        "shop_make": shop_make,
        "notes": notes,
        "source_tags": vehicle.get("source_tags") or ["manual-entry"],
    }


def match_decline(intake):
    """Return a decline code when shop policy declines the job, else None."""
    service = (intake.get("service_requested") or "").lower()
    if any(key in service for key in OIL_CHANGE_KEYWORDS):
        return "oil-change"
    engine = (intake.get("engine") or "").lower()
    if "n63" in engine:
        area = (intake.get("area") or "not sure").strip().lower()
        symptom = (intake.get("symptom") or "").lower()
        if area == "engine" or any(key in symptom for key in NO_START_KEYWORDS):
            return "n63-engine"
    return None


def build_case(case_id, vehicle, intake):
    """Assemble the case record, or a decline card when policy declines."""
    code = match_decline(intake)
    if code:
        card = render_decline(code)
        categorized = categorize(vehicle)
        card["case_id"] = case_id
        card["vehicle"] = categorized
        return {"declined": True, "decline": card, "vehicle": categorized, "case_id": case_id}
    return {
        "declined": False,
        "case_id": case_id,
        "vehicle": categorize(vehicle),
        "symptom": (intake.get("symptom") or "").strip(),  # verbatim: evidence, not noise
        "codes": [c for c in (intake.get("codes") or []) if c],
        "observations": [o for o in (intake.get("observations") or []) if o],
        "area": (intake.get("area") or "not sure").strip().lower(),
        "service_requested": (intake.get("service_requested") or "").strip(),
        "stakes": intake.get("stakes") or "",
        "stakes_source": intake.get("stakes_source") or "",
    }


def _is_vin_key(key):
    lowered = str(key).lower()
    return lowered == "vin" or lowered.endswith("_vin")


def strip_vin(payload):
    """Remove any VIN before a payload is written to disk cache."""
    if isinstance(payload, dict):
        return {k: strip_vin(v) for k, v in payload.items() if not _is_vin_key(k)}
    if isinstance(payload, list):
        return [strip_vin(v) for v in payload]
    return payload


# -- test-plan engine --------------------------------------------------

def normalize_test(raw, index):
    test = {
        "id": str(raw.get("id") or "t%d" % (index + 1)),
        "title": str(raw.get("title") or "Untitled test"),
        "what": str(raw.get("what") or ""),
        "how": str(raw.get("how") or ""),
        "expected": str(raw.get("expected") or ""),
        "causes": list(raw.get("causes") or []),
        "eliminates_on_pass": list(raw.get("eliminates_on_pass") or []),
        "eliminates_on_fail": list(raw.get("eliminates_on_fail") or []),
        "suspects_on_fail": list(raw.get("suspects_on_fail") or []),
        "symptom_match": 1 if raw.get("symptom_match") else 0,
        "code_match": 1 if raw.get("code_match") else 0,
        "rules_out_expensive": 1 if raw.get("rules_out_expensive") else 0,
        "quick": 1 if raw.get("quick") else 0,
        "shop_boost": int(raw.get("shop_boost") or 0),
        "minutes": raw.get("minutes"),
        "minutes_source": raw.get("minutes_source") or "",
        "final_gate": bool(raw.get("final_gate")),
    }
    minutes = test["minutes"]
    if minutes is not None:
        try:
            test["minutes"] = float(minutes)
        except (TypeError, ValueError):
            test["minutes"] = None
            test["minutes_source"] = ""
    if test["minutes"] is None:
        test["minutes_source"] = ""
    return test


def new_plan(case, raw_tests):
    tests = [normalize_test(raw, i) for i, raw in enumerate(raw_tests or [])]
    state = {
        "case_id": case["case_id"],
        "tests": tests,
        "results": {},
        "notes": {},
        "eliminated": [],
        "suspected": [],
        "trail": [],
        "manual_order": [t["id"] for t in tests],
        "seq": 0,
    }
    _rescore(state, None)
    return state


def _score_one(test, state):
    parts = {
        "symptom_match": WEIGHTS["symptom_match"] * test["symptom_match"],
        "code_match": WEIGHTS["code_match"] * test["code_match"],
        "rules_out_expensive": WEIGHTS["rules_out_expensive"] * test["rules_out_expensive"],
        "quick": WEIGHTS["quick"] * test["quick"],
        "shop_boost": test["shop_boost"],
        "suspected_cause": 0,
        "eliminated_penalty": 0,
    }
    causes = set(test["causes"])
    if causes and causes.issubset(set(state["eliminated"])):
        parts["eliminated_penalty"] = WEIGHTS["eliminated_penalty"]
    elif causes & set(state["suspected"]):
        parts["suspected_cause"] = WEIGHTS["suspected_cause"]
    return sum(parts.values()), parts


def _rescore(state, caused_by):
    order_before = [t["id"] for t in ranked_tests(state, rescore=False)] if state["trail"] or caused_by else None
    for test in state["tests"]:
        score, parts = _score_one(test, state)
        test["score"] = score
        test["score_parts"] = parts
        causes = set(test["causes"])
        if causes and causes.issubset(set(state["eliminated"])):
            test["standing"] = "eliminated"
        elif test["id"] in state["results"]:
            test["standing"] = "done"
        else:
            test["standing"] = "pending"
    if caused_by is not None:
        order_after = [t["id"] for t in ranked_tests(state, rescore=False)]
        moved = [tid for tid in order_after if order_before is not None and order_before.index(tid) != order_after.index(tid)]
        state["seq"] += 1
        state["trail"].append(
            {
                "seq": state["seq"],
                "caused_by": caused_by,
                "moved": moved,
                "order": order_after,
            }
        )


def ranked_tests(state, rescore=True):
    if rescore:
        for test in state["tests"]:
            score, parts = _score_one(test, state)
            test["score"] = score
            test["score_parts"] = parts
    manual = {tid: i for i, tid in enumerate(state.get("manual_order") or [])}
    pending = [t for t in state["tests"] if t.get("standing", "pending") == "pending"]
    rest = [t for t in state["tests"] if t.get("standing", "pending") != "pending"]
    pending.sort(key=lambda t: (-t.get("score", 0), manual.get(t["id"], 9999)))
    rest.sort(key=lambda t: manual.get(t["id"], 9999))
    return pending + rest


def record_result(state, test_id, result, note=""):
    """Record pass/fail, update causes, re-rank, and trail the change."""
    test = next((t for t in state["tests"] if t["id"] == test_id), None)
    if test is None:
        raise KeyError("unknown test: %s" % test_id)
    result = (result or "").strip().lower()
    if result not in ("pass", "fail"):
        raise ValueError("result must be pass or fail")
    state["results"][test_id] = result
    if note:
        state["notes"][test_id] = note
    if result == "pass":
        fresh = [c for c in test["eliminates_on_pass"] if c not in state["eliminated"]]
        state["eliminated"].extend(fresh)
        if fresh:
            caused_by = "%s passed, so ruled out: %s." % (test["title"], "; ".join(fresh))
        else:
            caused_by = "%s passed; no causes ruled out by this step." % test["title"]
    else:
        fresh_suspect = [c for c in test["suspects_on_fail"] if c not in state["suspected"]]
        state["suspected"].extend(fresh_suspect)
        fresh_out = [c for c in test["eliminates_on_fail"] if c not in state["eliminated"]]
        state["eliminated"].extend(fresh_out)
        bits = []
        if fresh_out:
            bits.append("ruled out: %s" % "; ".join(fresh_out))
        if fresh_suspect:
            bits.append("now suspected: %s" % "; ".join(fresh_suspect))
        if bits:
            caused_by = "%s failed, so %s." % (test["title"], "; ".join(bits))
        else:
            caused_by = "%s failed; suspicion unchanged." % test["title"]
    _rescore(state, caused_by)
    return state


def edit_plan(state, tests=None, order=None):
    """Shop edits: replace test fields and/or reorder. Re-scores, trails it."""
    if tests is not None:
        by_id = {t["id"]: t for t in state["tests"]}
        merged = []
        for i, raw in enumerate(tests):
            test = normalize_test(raw, i)
            old = by_id.get(test["id"], {})
            for key in ("score", "score_parts", "standing"):
                test[key] = old.get(key)
            merged.append(test)
        state["tests"] = merged
        # Drop results for tests that no longer exist.
        live = {t["id"] for t in merged}
        state["results"] = {k: v for k, v in state["results"].items() if k in live}
        state["notes"] = {k: v for k, v in state["notes"].items() if k in live}
    if order is not None:
        live = [tid for tid in order if any(t["id"] == tid for t in state["tests"])]
        live += [t["id"] for t in state["tests"] if t["id"] not in live]
        state["manual_order"] = live
    _rescore(state, "You edited the plan, so it re-ranked.")
    return state


# -- parts + labor -----------------------------------------------------

def normalize_part(raw):
    name = (raw.get("name") or "").strip()
    if not name:
        return None
    return {
        "name": name,
        "note": (raw.get("note") or "").strip(),
        "source": (raw.get("source") or "").strip(),
    }


def labor_math(state, standards):
    """Plain-words labor math. Only sourced minutes count; the rest is named."""
    lines = []
    known_minutes = 0.0
    for test in state["tests"]:
        entry = (standards or {}).get(test["id"], {}) or {}
        minutes = entry.get("minutes", test.get("minutes"))
        source = entry.get("source", test.get("minutes_source") or "")
        try:
            minutes = float(minutes) if minutes is not None else None
        except (TypeError, ValueError):
            minutes = None
        if minutes is None or not source:
            lines.append(
                {
                    "test_id": test["id"],
                    "title": test["title"],
                    "minutes": None,
                    "source": "",
                    "line": "%s: no shop time on file yet, so set one before quoting." % test["title"],
                }
            )
            continue
        known_minutes += minutes
        lines.append(
            {
                "test_id": test["id"],
                "title": test["title"],
                "minutes": minutes,
                "source": source,
                "line": "%s: about %d minutes (%s)." % (test["title"], round(minutes), source),
            }
        )
    missing = [entry for entry in lines if entry["minutes"] is None]
    cost = known_minutes / 60.0 * LABOR_RATE
    if lines and not missing:
        total = "Labor comes to about %d minutes, about $%d at $%d an hour." % (
            round(known_minutes),
            round(cost),
            LABOR_RATE,
        )
    elif lines:
        total = (
            "Labor with times on file comes to about %d minutes, about $%d at $%d an hour. "
            "%d step(s) still need a shop time: %s."
            % (
                round(known_minutes),
                round(cost),
                LABOR_RATE,
                len(missing),
                ", ".join(entry["title"] for entry in missing),
            )
        )
    else:
        total = "No steps in the plan, so there is no labor math yet."
    return {"lines": lines, "total_minutes": known_minutes or None, "plain_words": total}


# -- knowledge base ----------------------------------------------------

def load_kb(root):
    """Anonymized samples plus the owner's local shop files (slot ships empty).

    Only *.json note files inside shop_kb/ are read, each
    {"title": ..., "body": ...}. Missing directory means samples only.
    """
    notes = []
    try:
        path = os.path.join(root, "demo_cache", "bay_kb.json")
        with open(path, "r", encoding="utf-8") as fh:
            for entry in json.load(fh):
                notes.append(
                    {
                        "title": entry.get("title", ""),
                        "body": entry.get("body", ""),
                        "source": "demo-sample: Bay KB",
                    }
                )
    except (OSError, ValueError):
        pass
    folder = os.path.join(root, "shop_kb")
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError):
            continue
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("title"):
                continue
            notes.append(
                {
                    "title": entry.get("title", ""),
                    "body": entry.get("body", ""),
                    "source": "local shop file: %s" % os.path.basename(path),
                }
            )
    return notes


def search_kb(root, query):
    query = (query or "").strip().lower()
    notes = load_kb(root)
    if not query:
        return notes
    return [n for n in notes if query in n["title"].lower() or query in n["body"].lower()]
