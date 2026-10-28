"""Verdict engine: visible, changeable A/B/C rules — no black box.

Every part is graded by the ordered rules in ``rules.json`` (first match
wins). Each verdict reports the rule that fired plus every input value used,
so the page can show the reasoning next to the grade.

Verdicts:
  A — pull and list now
  B — worth it if you are standing there
  C — leave it

Honesty rule: prices, demand, and pull minutes only count when they carry a
source (shop-entered comps or tagged demo samples). Anything without a source
is treated as unknown and named as missing in plain words.
"""

import copy
import json

VERDICT_MEANING = {
    "A": "pull and list now",
    "B": "worth it if you are standing there",
    "C": "leave it",
}

DEFAULT_RULES = {
    "version": 1,
    "labor_rate_per_hour": 180,
    "thresholds": {
        "min_frames_a": 2,
        "min_list_price_a": 40,
        "min_coverage_a": 0.02,
        "small_part_price_floor": 10,
    },
    "rules": [
        {
            "id": "r_damaged",
            "name": "Broken in the photo",
            "verdict": "C",
            "enabled": True,
            "explain": "The part looks broken, so leave it no matter what else is true.",
            "when": [{"field": "intact", "op": "eq", "value": "no"}],
        },
        {
            "id": "r_thin_evidence",
            "name": "Seen once and unclear",
            "verdict": "C",
            "enabled": True,
            "explain": "Seen in only one frame and condition is unclear: not enough reliable evidence.",
            "when": [
                {"field": "intact", "op": "eq", "value": "unknown"},
                {"field": "frames_seen", "op": "lt", "threshold": "min_frames_a"},
            ],
        },
        {
            "id": "r_pull_now",
            "name": "Clear, wanted, worth listing",
            "verdict": "A",
            "enabled": True,
            "explain": "Intact, seen across frames, wanted, and priced above the list floor.",
            "when": [
                {"field": "intact", "op": "eq", "value": "yes"},
                {"field": "frames_seen", "op": "gte", "threshold": "min_frames_a"},
                {"field": "demand", "op": "in", "value": ["high", "medium"]},
                {"field": "price_high", "op": "gte", "threshold": "min_list_price_a"},
            ],
        },
        {
            "id": "r_worth_it_seen",
            "name": "Good part, softer demand",
            "verdict": "B",
            "enabled": True,
            "explain": "Intact and not unwanted: grab it while you are there.",
            "when": [
                {"field": "intact", "op": "eq", "value": "yes"},
                {"field": "demand", "op": "ne", "value": "low"},
            ],
        },
        {
            "id": "r_worth_it_twice",
            "name": "Unclear but seen twice and wanted",
            "verdict": "B",
            "enabled": True,
            "explain": "Condition unclear but tracked in two or more frames with real demand.",
            "when": [
                {"field": "intact", "op": "eq", "value": "unknown"},
                {"field": "frames_seen", "op": "gte", "threshold": "min_frames_a"},
                {"field": "demand", "op": "in", "value": ["high", "medium"]},
            ],
        },
        {
            "id": "r_default",
            "name": "Does not clear the bar",
            "verdict": "C",
            "enabled": True,
            "explain": "Catches everything left: low demand, cheap, or lacking reliable data.",
            "when": [],
        },
    ],
}


def load_rules(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rules = json.load(fh)
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULT_RULES)
    return _normalize(rules)


def save_rules(path, submitted):
    rules = _normalize(submitted)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, indent=2)
        fh.write("\n")
    return rules


def _normalize(submitted):
    if not isinstance(submitted, dict):
        raise ValueError("rules must be an object")
    base = copy.deepcopy(DEFAULT_RULES)
    if "labor_rate_per_hour" in submitted:
        rate = submitted["labor_rate_per_hour"]
        if not isinstance(rate, (int, float)) or rate <= 0:
            raise ValueError("labor_rate_per_hour must be a positive number")
        base["labor_rate_per_hour"] = rate
    thresholds = submitted.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be an object")
    for key, default in base["thresholds"].items():
        value = thresholds.get(key, default)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("threshold %s must be a non-negative number" % key)
        base["thresholds"][key] = value
    rules = submitted.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules must be a non-empty list")
    known = {rule["id"]: rule for rule in base["rules"]}
    cleaned = []
    for entry in rules:
        if not isinstance(entry, dict) or entry.get("id") not in known:
            raise ValueError("unknown rule id: %r" % (entry.get("id") if isinstance(entry, dict) else entry))
        template = known[entry["id"]]
        enabled = entry.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("rule %s: enabled must be true/false" % template["id"])
        cleaned.append(
            {
                "id": template["id"],
                "name": template["name"],
                "verdict": template["verdict"],
                "enabled": enabled,
                "explain": template["explain"],
                "when": template["when"],
            }
        )
    if not any(rule["id"] == "r_default" and rule["enabled"] for rule in cleaned):
        raise ValueError("the default rule must stay enabled so every part gets a verdict")
    base["rules"] = cleaned
    return base


def _resolve_expected(condition, thresholds):
    if "threshold" in condition:
        return thresholds.get(condition["threshold"])
    return condition.get("value")


def _check(actual, op, expected):
    if actual is None or expected is None:
        # Missing data never passes a comparison; the default rule catches it.
        return op == "ne" and actual is not None and expected is None
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "in":
        return actual in expected
    if op == "gte":
        return actual >= expected
    if op == "lte":
        return actual <= expected
    if op == "gt":
        return actual > expected
    if op == "lt":
        return actual < expected
    return False


def _matches(rule, inputs, thresholds):
    for condition in rule.get("when", []):
        if not _check(inputs.get(condition.get("field")), condition.get("op"), _resolve_expected(condition, thresholds)):
            return False
    return True


def _sourced(value, source):
    return value if source else None


def part_inputs(part, shop):
    """Merge harvest evidence with shop-entered comps into rule inputs."""
    sightings = part.get("sightings") or []
    coverages = [s.get("coverage") for s in sightings if isinstance(s.get("coverage"), (int, float))]
    demand = (shop.get("demand") or "unknown").lower()
    if demand not in ("high", "medium", "low", "unknown"):
        demand = "unknown"
    price_source = shop.get("price_source") or ""
    pull_source = shop.get("pull_source") or ""
    try:
        low = float(shop.get("price_low")) if shop.get("price_low") not in (None, "") else None
        high = float(shop.get("price_high")) if shop.get("price_high") not in (None, "") else None
    except (TypeError, ValueError):
        low, high = None, None
    try:
        minutes = float(shop.get("pull_minutes")) if shop.get("pull_minutes") not in (None, "") else None
    except (TypeError, ValueError):
        minutes = None
    if low is not None and high is not None and low > high:
        low, high = high, low
    return {
        "intact": part.get("intact", "unknown"),
        "frames_seen": len(sightings),
        "best_coverage": max(coverages) if coverages else None,
        "count": part.get("count", 1),
        "demand": demand,
        "demand_source": shop.get("demand_source") or "",
        "price_low": _sourced(low, price_source),
        "price_high": _sourced(high, price_source),
        "price_source": price_source,
        "price_known": bool(price_source) and (low is not None or high is not None),
        "pull_minutes": _sourced(minutes, pull_source),
        "pull_source": pull_source,
        "frames": [s.get("frame", "?") for s in sightings],
        "price_median": shop.get("price_median"),
        "net_low": shop.get("net_low"),
        "net_high": shop.get("net_high"),
        "money_grade": shop.get("money_grade") or "",
        "money_reason": shop.get("money_reason") or "",
        "sold_count": shop.get("sold_count"),
        "reliable": shop.get("reliable"),
        "valuation_notes": shop.get("valuation_notes") or [],
    }


def _money(value):
    return "$%d" % round(value)


def evaluate(parts, rules, part_inputs_map):
    rules = _normalize(rules)
    thresholds = rules["thresholds"]
    labor_rate = rules["labor_rate_per_hour"]
    verdicts = []
    for part in parts:
        shop = (part_inputs_map or {}).get(part.get("id"), {}) or {}
        # Demo cache and live harvest may already carry shop-style comps.
        for key in ("demand", "demand_source", "price_low", "price_high", "price_source", "pull_minutes", "pull_source"):
            shop.setdefault(key, part.get(key))
        inputs = part_inputs(part, shop)
        fired = None
        for rule in rules["rules"]:
            if rule["enabled"] and _matches(rule, inputs, thresholds):
                fired = rule
                break
        verdict = fired["verdict"]
        rule_id = fired["id"]
        rule_name = fired["name"]
        rule_explain = fired["explain"]
        overridden = False
        override = (shop.get("override") or "").strip().upper()
        if override in VERDICT_MEANING and override != verdict:
            verdict = override
            rule_id = "override"
            rule_name = "Human override"
            rule_explain = "You overruled the %s grade. Your call stands and the totals use it." % fired["verdict"]
            overridden = True
        verdicts.append(
            {
                "part_id": part.get("id"),
                "label": part.get("label", "part"),
                "category": part.get("category", "other"),
                "verdict": verdict,
                "verdict_means": VERDICT_MEANING[verdict],
                "rule_id": rule_id,
                "rule_name": rule_name,
                "rule_explain": rule_explain,
                "overridden": overridden,
                "inputs": inputs,
            }
        )
    totals = _totals(verdicts, labor_rate)
    return {"verdicts": verdicts, "totals": totals, "labor_rate_per_hour": labor_rate}


def _totals(verdicts, labor_rate):
    summary = {}
    for grade in ("A", "B"):
        group = [v for v in verdicts if v["verdict"] == grade]
        priced = [v for v in group if v["inputs"]["price_known"]]
        if priced:
            low = sum(v["inputs"]["price_low"] or v["inputs"]["price_high"] or 0 for v in priced)
            high = sum(v["inputs"]["price_high"] or v["inputs"]["price_low"] or 0 for v in priced)
            if round(low) == round(high):
                line = "The %s parts (%s) could bring about %s if they sell at the listed prices." % (
                    grade,
                    VERDICT_MEANING[grade],
                    _money(high),
                )
            else:
                line = "The %s parts (%s) could bring about %s to %s if they sell at the listed prices." % (
                    grade,
                    VERDICT_MEANING[grade],
                    _money(low),
                    _money(high),
                )
            line += " That covers %d of %d %s parts." % (len(priced), len(group), grade)
            line += " This is the sure money." if grade == "A" else " This is the maybe money."
        elif group:
            line = "No %s part has a reliable price yet, so there is no %s total." % (grade, grade)
            low = high = None
        else:
            line = "There are no %s parts, so the %s total is $0." % (grade, grade)
            low = high = 0
        missing = len(group) - len(priced)
        minutes = [v["inputs"]["pull_minutes"] for v in group if v["inputs"]["pull_minutes"] is not None]
        if minutes:
            total_minutes = sum(minutes)
            cost = total_minutes / 60.0 * labor_rate
            shop_line = "Shop time: about %d minutes of pull time on the %s parts, about %s at %s an hour." % (
                round(total_minutes),
                grade,
                _money(cost),
                _money(labor_rate),
            )
        else:
            shop_line = "No pull-time notes on the %s parts yet, so no shop-time cost is shown." % grade
            total_minutes = None
        summary[grade] = {
            "count": len(group),
            "priced_count": len(priced),
            "unpriced_count": missing,
            "low": low,
            "high": high,
            "plain_words": line,
            "shop_time_plain_words": shop_line,
            "pull_minutes": total_minutes,
        }
    left_out = [v for v in verdicts if not v["inputs"]["price_known"]]
    if left_out:
        summary["excluded_note"] = "%d part%s ha%s no reliable price, so %s not in any total: %s." % (
            len(left_out),
            "" if len(left_out) == 1 else "s",
            "s" if len(left_out) == 1 else "ve",
            "it is" if len(left_out) == 1 else "they are",
            ", ".join(v["label"] for v in left_out),
        )
    else:
        summary["excluded_note"] = "Every part has a sourced price, so every part is in a total."
    return summary


# Professional declines the engine can render as verdicts (never errors).
# Shop policy codes; marketing copy must never name engine codes.
DECLINES = {
    "n63-engine": {
        "title": "We cannot take this engine job",
        "body": (
            "This shop does not do engine work on this BMW V8 generation, and a "
            "no-start is treated as possibly engine-related, so we are declining "
            "the job rather than guessing. No charge for the look, and we are "
            "happy to point you to a shop that specializes in these engines."
        ),
        "next_step": "Ask us for a referral, or bring a different concern we can help with.",
    },
    "oil-change": {
        "title": "We do not do oil changes",
        "body": (
            "This shop does not offer oil-change service. We would rather tell "
            "you plainly than book work we do not do well."
        ),
        "next_step": "Ask us about diagnosis, repair, or parts instead.",
    },
}


def render_decline(code):
    """Render a decline policy as a clean verdict card. Unknown code: KeyError."""
    policy = DECLINES[code]
    return {
        "verdict": "declined",
        "code": code,
        "title": policy["title"],
        "body": policy["body"],
        "next_step": policy["next_step"],
    }
