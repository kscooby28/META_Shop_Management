"""Scale evaluation (WO13): every demo case through both engines.

Measurement, not product. No screens, no flows, no features. Runs the
anonymized Yard demo case, the three anonymized Bay demo cases, and the
inventory demo parts through the deterministic rules engine
(verdict.evaluate over rules.json, which stays untouched) and through
Muse Spark Open live through Baseten, one live call per case, no
retries. A failed live call is recorded honestly for that case; a demo
grade is never substituted or presented as live.

Evidence each engine sees: the rules engine grades part dicts plus
shop-style comps through the unchanged product path; the model gets the
same Compare-view shape ({car, parts: [{part_id, label, inputs}]}) plus
the case's own written notes (Bay part notes, inventory owner notes and
car labels), because the rules have no note field and the gap between
what the rules can read and what the model can read is part of what is
measured. Bay job parts carry no pull-grade semantics in the product;
they run here to measure thin-evidence behavior, and the README note
says so in plain words. Inventory condition maps to intact yes unless
the text says unknown, untested, or equivalent; anything else stays
unknown, never guessed.

Zero live Meta API calls: the only network attempt in this script is
spark_open.request_grades (Baseten). It makes no demo substitution on
failure; failures land in the result file with their exact cause.

Usage:
  python scripts/eval_scale.py                 run live, write the JSON file
  python scripts/eval_scale.py --write-readme  also refresh the README table
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bay import load_bay_case  # noqa: E402
from comps import get_adapter as get_comps_adapter  # noqa: E402
from demo_cache import StepCache  # noqa: E402
from verdict import evaluate, load_rules  # noqa: E402
import spark_open  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_NAME = "eval_scale_results.json"
META_LEGS = ("Muse Spark 1.3", "SAM 3.1", "Muse Image", "Muse Voice", "Muse Wonder")

CASE_ORDER = ("yard-demo", "bay-case1", "bay-case2", "bay-case3",
              "inventory-demo")


def _comps(root, part_ids):
    return get_comps_adapter(root).lookup(list(part_ids), True)


def build_yard(root):
    """Yard demo case: the 7 harvest parts through the product path."""
    cache = StepCache(root)
    car = cache.load_demo("intake").get("car", {})
    harvest = cache.load_demo("harvest")
    parts = harvest["parts"]
    rules = load_rules(os.path.join(root, "rules.json"))
    verdicts = evaluate(parts, rules, _comps(root, [p["id"] for p in parts]))["verdicts"]
    evidence = {
        "case": "yard-demo",
        "car": car,
        "parts": [{"part_id": v["part_id"], "label": v["label"],
                   "inputs": v["inputs"]} for v in verdicts],
    }
    return {"label": "Yard demo case (7 harvest parts)", "verdicts": verdicts,
            "evidence": evidence}


def build_bay(root, case):
    """Bay demo case: job-list entries as thin-evidence parts."""
    raw = load_bay_case("parts", case, root).get("parts", [])
    parts, notes = [], {}
    for index, entry in enumerate(raw):
        pid = "bp-%s-%d" % (case, index + 1)
        parts.append({"id": pid, "label": entry.get("name", "part"),
                      "category": "other", "intact": "unknown",
                      "sightings": [], "count": 1})
        notes[pid] = entry.get("note", "")
    rules = load_rules(os.path.join(root, "rules.json"))
    verdicts = evaluate(parts, rules, _comps(root, [p["id"] for p in parts]))["verdicts"]
    evidence = {
        "case": "bay-%s" % case,
        "car": {"label": "Bay demo %s (anonymized sample)" % case},
        "parts": [{"part_id": v["part_id"], "label": v["label"],
                   "inputs": v["inputs"],
                   "case_note": notes.get(v["part_id"], "")} for v in verdicts],
    }
    return {"label": "Bay demo %s (%d job part%s)" % (
        case, len(parts), "" if len(parts) == 1 else "s"),
        "verdicts": verdicts, "evidence": evidence}


def _inventory_intact(condition):
    text = (condition or "").lower()
    if not text or "unknown" in text or "untested" in text or "haven't" in text:
        return "unknown"
    return "yes"


def build_inventory(root):
    """Inventory demo parts: owner values as sourced prices, gaps unknown."""
    # Frozen inputs: the recorded results (scale, meta, followup) pin the
    # seed exactly as it stood at WO16. The live demo seed evolves under
    # WO21 P4, so this case reads the frozen fixture; the recompute tests
    # prove rules and verdicts are stable, not that the demo never grows.
    with open(os.path.join(root, "demo_cache", "inv_seed.eval.json"),
              encoding="utf-8") as fh:
        seed = json.load(fh)
    cars = {c["id"]: c.get("label", c["id"]) for c in seed.get("cars", [])}
    parts, shop, extra = [], {}, {}
    for entry in seed.get("parts", []):
        pid = entry["id"]
        parts.append({"id": pid, "label": entry.get("label", "part"),
                      "category": "other",
                      "intact": _inventory_intact(entry.get("condition")),
                      "sightings": [], "count": 1})
        value = entry.get("value")
        source = entry.get("valueSource", "")
        if isinstance(value, (int, float)) and source:
            shop[pid] = {"price_low": value, "price_high": value,
                         "price_source": source}
        extra[pid] = {"car_label": cars.get(entry.get("carId"), "unknown car"),
                      "owner_note": entry.get("note", ""),
                      "condition": entry.get("condition", "unknown")}
    merged = _comps(root, [p["id"] for p in parts])
    for pid, overlay in shop.items():
        merged.setdefault(pid, {}).update(overlay)
    rules = load_rules(os.path.join(root, "rules.json"))
    verdicts = evaluate(parts, rules, merged)["verdicts"]
    evidence = {
        "case": "inventory-demo",
        "car": {"label": "demo inventory cars (4 anonymized samples)"},
        "parts": [{"part_id": v["part_id"], "label": v["label"],
                   "inputs": v["inputs"],
                   "car_label": extra[v["part_id"]]["car_label"],
                   "owner_note": extra[v["part_id"]]["owner_note"],
                   "condition": extra[v["part_id"]]["condition"]}
                  for v in verdicts],
    }
    return {"label": "Inventory demo parts (%d parts)" % len(parts),
            "verdicts": verdicts, "evidence": evidence}


BUILDERS = {
    "yard-demo": build_yard,
    "bay-case1": lambda root: build_bay(root, "case1"),
    "bay-case2": lambda root: build_bay(root, "case2"),
    "bay-case3": lambda root: build_bay(root, "case3"),
    "inventory-demo": build_inventory,
}


def grade_live(case_id, evidence, part_ids):
    """One live Baseten call, timed. Failures return their exact cause."""
    if not part_ids:
        return {"live_ok": False, "call_sent": False, "latency_ms": 0,
                "cause": "no parts to grade, so no call was sent",
                "grades": [], "dropped": 0}
    started = time.time()
    try:
        result = spark_open.request_grades(evidence)
    except spark_open.MetaAPIError as exc:
        return {"live_ok": False, "call_sent": True,
                "latency_ms": int((time.time() - started) * 1000),
                "cause": str(exc), "grades": [], "dropped": 0}
    latency_ms = int((time.time() - started) * 1000)
    known = set(part_ids)
    kept, dropped = [], 0
    for entry in result["grades"]:
        if entry["part_id"] in known:
            kept.append(entry)
        else:
            dropped += 1
    return {"live_ok": True, "call_sent": True, "latency_ms": latency_ms,
            "cause": "", "grades": kept, "dropped": dropped}


def run_case(root, case_id):
    built = BUILDERS[case_id](root)
    verdicts = built["verdicts"]
    live = grade_live(case_id, built["evidence"],
                      [v["part_id"] for v in verdicts])
    open_by_id = {g["part_id"]: g for g in live["grades"]}
    parts = []
    for v in verdicts:
        side = open_by_id.get(v["part_id"])
        parts.append({
            "part_id": v["part_id"],
            "label": v["label"],
            "rule_grade": v["verdict"],
            "rule_id": v["rule_id"],
            "rule_name": v["rule_name"],
            "rule_explain": v["rule_explain"],
            "open_grade": side["grade"] if side else None,
            "open_reason": side["reason"] if side else "",
            "open_mode": "live" if side else ("live, ungraded" if live["live_ok"]
                                              else "no live grade"),
            "agree": (side["grade"] == v["verdict"]) if side else None,
        })
    return {
        "case": case_id,
        "label": built["label"],
        "live_ok": live["live_ok"],
        "call_sent": live["call_sent"],
        "latency_ms": live["latency_ms"],
        "live_cause": live["cause"],
        "dropped_unknown_ids": live["dropped"],
        "cost": "the endpoint reports no cost, so none is estimated",
        "parts": parts,
    }


def measure(root):
    cases = [run_case(root, case_id) for case_id in CASE_ORDER]
    agree = sum(1 for c in cases for p in c["parts"] if p["agree"] is True)
    total = sum(1 for c in cases for p in c["parts"] if p["agree"] is not None)
    calls = sum(1 for c in cases if c["call_sent"])
    return {
        "order": "Work Order 13: live evaluation at scale, Baseten first",
        "cases": cases,
        "agreement": {"agree": agree, "total": total,
                      "rate": "%d/%d" % (agree, total)},
        "live_baseten_calls_sent": calls,
        "live_meta_calls_attempted": 0,
        "engines_live": ["Muse Spark Open through Baseten "
                         "(meta-models/muse-spark-open-1026)"],
        "engines_demo": ["%s (Meta key rotation unconfirmed)" % leg
                         for leg in META_LEGS],
    }


def _cell(text):
    return " ".join(str(text or "").replace("|", "/").split())


def render_section(results):
    agree = results["agreement"]
    lines = [
        "## Live evaluation at scale (Work Order 13)",
        "",
        "Every demo case through both engines: the deterministic rules grade",
        "and the Muse Spark Open live grade side by side, one live Baseten",
        "call per case, no retries. Spark Open ran live because its key is",
        "present and proven; Spark 1.3, SAM, Image, Voice, and Wonder stayed",
        "on demo because the Meta key rotation is still unconfirmed. Bay job",
        "parts carry no pull-grade meaning in the product; they run here to",
        "measure thin-evidence behavior from name and note alone. Inventory",
        "conditions map to intact unless the text says unknown or untested.",
        "Regenerate with `python scripts/eval_scale.py --write-readme`.",
        "",
        "| case | part | rule grade | rule reason | Spark Open live grade | Spark Open reason | match |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in results["cases"]:
        for part in case["parts"]:
            if part["agree"] is None:
                match = "no live grade"
            else:
                match = "yes" if part["agree"] else "NO"
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                _cell(case["case"]), _cell(part["label"]),
                _cell(part["rule_grade"]),
                _cell("%s: %s" % (part["rule_name"], part["rule_explain"])),
                _cell(part["open_grade"] or "—"), _cell(part["open_reason"]),
                match))
    lines += [
        "",
        "Agreement: %s parts (%d agree, %d compared). Live Baseten calls "
        "sent: %d. Live Meta calls attempted: 0." % (
            agree["rate"], agree["agree"], agree["total"],
            results["live_baseten_calls_sent"]),
        "",
    ]
    for case in results["cases"]:
        if not case["call_sent"]:
            lines.append("- %s: no call sent (%s)." % (
                case["case"], _cell(case["live_cause"])))
        elif case["live_ok"]:
            graded = sum(1 for p in case["parts"] if p["open_grade"])
            lines.append("- %s: Spark Open live in %d ms, %d/%d parts "
                         "graded." % (case["case"], case["latency_ms"],
                                      graded, len(case["parts"])))
        else:
            lines.append("- %s: live call failed (%s)." % (
                case["case"], _cell(case["live_cause"])))
    disagreements = [(c["case"], p) for c in results["cases"]
                     for p in c["parts"] if p["agree"] is False]
    if disagreements:
        lines += ["",
                  "Disagreements, with both reasons:"]
        for case_id, part in disagreements:
            lines.append("- %s / %s: rules say %s (%s); Spark Open live "
                         "says %s (%s)." % (
                             case_id, _cell(part["label"]),
                             part["rule_grade"],
                             _cell("%s: %s" % (part["rule_name"],
                                               part["rule_explain"])),
                             part["open_grade"], _cell(part["open_reason"])))
    else:
        lines += ["", "No disagreements: every live grade matched its rule grade."]
    lines.append("")
    return "\n".join(lines)


START = "<!-- EVAL-SCALE:START -->"
END = "<!-- EVAL-SCALE:END -->"
LAB_END = "<!-- EVAL-LAB:END -->"


def write_readme(results):
    path = os.path.join(ROOT, "README.md")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    block = START + "\n" + render_section(results) + END
    if START in text and END in text:
        before, _, rest = text.partition(START)
        _, _, after = rest.partition(END)
        text = before + block + after
    elif LAB_END in text:
        before, _, after = text.partition(LAB_END)
        text = before + LAB_END + "\n\n" + block + after
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


def main(argv):
    results = measure(ROOT)
    path = write_results(results)
    agree = results["agreement"]
    print("wrote %s" % path)
    for case in results["cases"]:
        if not case["call_sent"]:
            print("- %s: no call (%s)" % (case["case"], case["live_cause"]))
        elif case["live_ok"]:
            print("- %s: live ok in %d ms" % (case["case"], case["latency_ms"]))
        else:
            print("- %s: FAILED (%s)" % (case["case"], case["live_cause"]))
    print("agreement %s, live Baseten calls %d, live Meta calls 0" % (
        agree["rate"], results["live_baseten_calls_sent"]))
    if "--write-readme" in argv:
        write_readme(results)
        print("README table refreshed.")


if __name__ == "__main__":
    main(sys.argv[1:])
