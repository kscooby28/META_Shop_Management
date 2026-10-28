"""Eval lab: run the anonymized demo set through each engine, offline.

Case set (demo only, never real customer cases): the 7 Yard demo parts,
Bay demo case 1's ranking, and the Bay KB samples already in the repo.
Each engine row reports what is measurable today plus exactly what would
run it live. Live legs are all flagged off; this harness makes zero
network calls. Key checks read key NAMES only and never print values.

Usage:
  python scripts/eval_lab.py              print the results table
  python scripts/eval_lab.py --write-readme
                                         refresh the README table in place
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bay import build_case, load_bay_case, new_plan, ranked_tests
from comps import get_adapter as get_comps_adapter
from demo_cache import StepCache
from verdict import evaluate, load_rules
from wonder import escalate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPARK_OPEN_ENDPOINT = "https://inference.baseten.co/v1"
SPARK_OPEN_MODEL = "meta-models/muse-spark-open-1026"
BASETEN_KEY_NAME = "BASETEN_API_KEY"
META_KEY_NAMES = ("META_API_KEY", "MODEL_API_KEY")
GLIMMER_ENDPOINT_NAME = "GLIMMER_ENDPOINT"


def _key_present(*names):
    return any(os.environ.get(n, "").strip() for n in names)


def _dotenv_has(*names):
    try:
        with open(os.path.join(ROOT, ".env"), "r", encoding="utf-8") as fh:
            keys = set()
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    keys.add(line.partition("=")[0].strip())
        return any(n in keys for n in names)
    except OSError:
        return False


def measure():
    """Run every offline-measurable leg. Returns rows + unblock notes."""
    cache = StepCache(ROOT)
    owner = cache.load_demo("eval_owner")
    t0 = time.time()

    intake = cache.load_demo("intake")
    grounded = [p for p in intake["parts"] if p.get("box")]
    grounding = "%d/%d boxes valid" % (
        sum(1 for p in grounded
            if len(p["box"]) == 4 and p["box"][2] > p["box"][0]
            and p["box"][3] > p["box"][1]),
        len(intake["parts"]),
    )

    parts = cache.load_demo("harvest")["parts"]
    comps = get_comps_adapter(ROOT).lookup([p["id"] for p in parts], True)
    rules = load_rules(os.path.join(ROOT, "rules.json"))
    verdicts = evaluate(parts, rules, comps)["verdicts"]
    expected = owner["yard"]
    agree = sum(1 for v in verdicts if expected.get(v["part_id"]) == v["verdict"])
    agreement = "%d/%d owner grades" % (agree, len(verdicts))

    router_ok, router_n = 0, 0
    for verdict in verdicts:
        router_n += 1
        inputs = verdict.get("inputs", {})
        expect = (
            verdict.get("verdict") == "B" or not inputs.get("price_known")
            or not inputs.get("demand_source") or inputs.get("intact") == "unknown"
        )
        got = escalate("yard", verdict, verdict["part_id"], ROOT)["escalated"]
        router_ok += expect == got
    router = "%d/%d router outcomes" % (router_ok, router_n)

    bay_in = load_bay_case("intake", "case1", ROOT)
    vehicle = bay_in["vehicle"]
    case = build_case(
        "b-eval", vehicle,
        {"symptom": bay_in["symptom"], "codes": bay_in["codes"],
         "observations": bay_in["observations"], "area": bay_in["area"],
         "service_requested": bay_in["service_requested"],
         "engine": vehicle.get("engine", "")},
    )
    plan = new_plan(case, load_bay_case("plan", "case1", ROOT)["tests"])
    ranked = ranked_tests(plan)
    order_ok = [t["id"] for t in ranked] == owner["bay"]["case1"]["order"]
    score_ok = ranked[0]["score"] == owner["bay"]["case1"]["top_score"]
    ranking = "order %s, top score %s" % (
        "match" if order_ok else "DRIFT", "match" if score_ok else "DRIFT")

    elapsed_ms = int((time.time() - t0) * 1000)
    meta_key = _key_present(*META_KEY_NAMES) or _dotenv_has(*META_KEY_NAMES)
    baseten_key = _key_present(BASETEN_KEY_NAME) or _dotenv_has(BASETEN_KEY_NAME)
    glimmer_ep = _key_present(GLIMMER_ENDPOINT_NAME) or _dotenv_has(GLIMMER_ENDPOINT_NAME)

    rows = [
        {
            "engine": "muse-spark-1.3 (demo leg)",
            "cases": "%d yard parts + intake" % len(verdicts),
            "grounding": grounding,
            "agreement": "%s; bay %s" % (agreement, ranking),
            "cost": "$0.00 (demo)",
            "latency": "%d ms (sampled)" % elapsed_ms,
            "status": "live blocked: needs Meta key rotation confirmed",
        },
        {
            "engine": "wonder-standard (demo leg)",
            "cases": "%d verdicts routed" % router_n,
            "grounding": "n/a (reviewer, not grounder)",
            "agreement": router,
            "cost": "$0.00 (demo)",
            "latency": "shares the run above",
            "status": "live blocked: needs Meta key rotation confirmed",
        },
        {
            "engine": "muse-spark-open-1026",
            "cases": "same demo set, when live",
            "grounding": "—",
            "agreement": "—",
            "cost": "—",
            "latency": "—",
            "status": "blocked: needs %s in the local environment "
                      "(endpoint %s, model %s)" % (
                          BASETEN_KEY_NAME, SPARK_OPEN_ENDPOINT, SPARK_OPEN_MODEL),
        },
        {
            "engine": "glimmer",
            "cases": "same demo set, when live",
            "grounding": "—",
            "agreement": "—",
            "cost": "—",
            "latency": "—",
            "status": "blocked: needs a confirmed hosted endpoint "
                      "(%s); will not run local on a 12GB card" % GLIMMER_ENDPOINT_NAME,
        },
    ]
    notes = [
        "Meta key names checked (%s): %s." % (
            ", ".join(META_KEY_NAMES), "present" if meta_key else "missing"),
        "%s: %s." % (BASETEN_KEY_NAME, "present" if baseten_key else "missing"),
        "%s: %s." % (GLIMMER_ENDPOINT_NAME,
                     "set" if glimmer_ep else "unset, endpoint unconfirmed"),
        "Key names only were read; no values were printed or logged.",
    ]
    return rows, notes


def render_table(rows):
    lines = [
        "| engine | cases | grounding | agreement | cost | latency | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            row["engine"], row["cases"], row["grounding"], row["agreement"],
            row["cost"], row["latency"], row["status"]))
    return "\n".join(lines)


START = "<!-- EVAL-LAB:START -->"
END = "<!-- EVAL-LAB:END -->"


def write_readme(rows, notes):
    path = os.path.join(ROOT, "README.md")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    section = (
        "## Eval lab\n\n"
        "The same anonymized demo set through each engine. Demo legs are "
        "measured below; live legs are flagged off with exactly what would "
        "run them. Regenerate with `python scripts/eval_lab.py --write-readme`.\n\n"
        + render_table(rows) + "\n\n"
        + "\n".join("- " + n for n in notes) + "\n"
    )
    block = START + "\n" + section + END
    if START in text and END in text:
        before, _, rest = text.partition(START)
        _, _, after = rest.partition(END)
        text = before + block + after
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main():
    rows, notes = measure()
    print(render_table(rows))
    print()
    for note in notes:
        print("- " + note)
    if "--write-readme" in sys.argv[1:]:
        write_readme(rows, notes)
        print("\nREADME table refreshed.")


if __name__ == "__main__":
    main()
