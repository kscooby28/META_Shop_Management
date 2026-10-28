"""Sold-comp adapter + valuation engine: isolated per-service feed, mock for demo.

The verdict engine prices parts only from comps that carry a source. This
module is the single place comp sources plug in:

- ``MockCompsAdapter`` (this build): runs the tagged demo-sample board
  through the valuation engine in demo mode, and reports "no reliable
  data" in live mode. It never invents a price and never touches a real
  account.
- ``EbaySoldCompsAdapter`` (later step): same interface, credentials from
  its own env keys, real SOLD listings. Not built in this work order.

Valuation engine (fresh, from plain-words patterns): sold prices in get a
median-centered range with width from the data's own spread, net money
after a visible fee share, a money grade with a plain-words reason, and
named handling for thin, stale, and contradictory feeds. Unknowns are
named, never guessed. The money grade is advisory beside the rule grade
in rules.json, which stays the single grading authority.

A comp entry shape: demand, demand_source, price_low, price_high,
price_median, price_source, price_note, net_low, net_high, money_grade,
money_reason, sold_count, reliable, pull_minutes, pull_source. Any price
without a ``*_source`` is ignored downstream.
"""

import json
import os

# Visible valuation constants. The fee share is the typical eBay
# final-value bite, shop-adjustable; the rest are the engine's honesty
# floors, all named in notes when they bite.
EBAY_FEE_RATE = 0.1325
MIN_SOLDS_FOR_RANGE = 3
STALE_DAYS = 400
DISAGREE_RATIO = 3.0
MONEY_GRADE_A_NET = 100
MONEY_GRADE_B_NET = 40


def _round_money(value):
    return round(float(value), 2)


def net_after_fees(price):
    """What a sold price keeps after the visible fee share."""
    return _round_money(price * (1 - EBAY_FEE_RATE))


def _median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def build_valuation(solds):
    """Value one part from a list of sold prices. Pure.

    Each sold is {"price": number, "age_days": optional days since sold}.
    Returns range, median, nets, money grade + reason, sold count,
    reliability, and plain-words notes. Empty or unusable feeds yield no
    range and say so; nothing is ever guessed.
    """
    notes = []
    valid = []
    dropped = 0
    stale = 0
    for sold in solds or []:
        price = (sold or {}).get("price")
        if not isinstance(price, (int, float)) or not (price > 0):
            dropped += 1
            continue
        age = (sold or {}).get("age_days")
        if isinstance(age, (int, float)) and age > STALE_DAYS:
            stale += 1
            continue
        valid.append(float(price))
    unaged = sum(1 for s in (solds or [])
                 if isinstance((s or {}).get("price"), (int, float))
                 and (s or {}).get("price") > 0
                 and not isinstance((s or {}).get("age_days"), (int, float)))
    if dropped:
        notes.append("%d entr%s carried no usable price and %s left out."
                     % (dropped, "y" if dropped == 1 else "ies",
                        "was" if dropped == 1 else "were"))
    if stale:
        notes.append("%d sold%s older than %d days %s too stale to trust."
                     % (stale, "" if stale == 1 else "s", STALE_DAYS,
                        "was" if stale == 1 else "were"))
    if unaged:
        notes.append("%d of %d solds carry no age, so staleness is unknown."
                     % (unaged, len(valid) + stale))
    count = len(valid)
    if not count:
        return {
            "price_low": None, "price_high": None, "price_median": None,
            "net_low": None, "net_high": None,
            "money_grade": "C",
            "money_reason": "No solds to price from, so no range and no grade above C.",
            "sold_count": 0, "reliable": False,
            "valuation_notes": notes or ["No solds on file for this part."],
        }
    low, high = min(valid), max(valid)
    median = _median(valid)
    if count < MIN_SOLDS_FOR_RANGE:
        notes.append("Only %d sold%s: enough for a span, too thin to trust."
                     % (count, "" if count == 1 else "s"))
    if low > 0 and high / low >= DISAGREE_RATIO:
        notes.append("Solds span %.0fx from low to high, so check the condition "
                     "mix before trusting the middle." % (high / low))
    net_low, net_high = net_after_fees(low), net_after_fees(high)
    if count < MIN_SOLDS_FOR_RANGE:
        grade, reason = "C", "Only %d sold%s: too thin for better than C." % (
            count, "" if count == 1 else "s")
    elif net_high >= MONEY_GRADE_A_NET:
        grade, reason = "A", "Top net about $%d over %d solds." % (round(net_high), count)
    elif net_high >= MONEY_GRADE_B_NET:
        grade, reason = "B", "Top net about $%d over %d solds." % (round(net_high), count)
    else:
        grade, reason = "C", "Top net only about $%d over %d solds." % (
            round(net_high), count)
    return {
        "price_low": low, "price_high": high, "price_median": median,
        "net_low": net_low, "net_high": net_high,
        "money_grade": grade, "money_reason": reason,
        "sold_count": count, "reliable": count >= MIN_SOLDS_FOR_RANGE,
        "valuation_notes": notes,
    }


def valuation_from_board(entry):
    """Run one demo-board entry (with a solds list) through the engine."""
    return build_valuation((entry or {}).get("solds") or [])


def valuation_from_shop(low, high):
    """Value a shop-typed range: the shop's numbers stand as the range.

    Sold count is honestly unknown, so the grade follows the net
    thresholds with a note saying the count is unknown.
    """
    try:
        low_f = float(low) if low not in (None, "") else None
        high_f = float(high) if high not in (None, "") else None
    except (TypeError, ValueError):
        low_f, high_f = None, None
    if low_f is None and high_f is None:
        return {
            "price_low": None, "price_high": None, "price_median": None,
            "net_low": None, "net_high": None,
            "money_grade": "C", "money_reason": "No shop numbers to price from.",
            "sold_count": None, "reliable": False,
            "valuation_notes": ["Shop range is blank."],
        }
    if low_f is None:
        low_f = high_f
    if high_f is None:
        high_f = low_f
    if low_f > high_f:
        low_f, high_f = high_f, low_f
    median = (low_f + high_f) / 2
    net_low, net_high = net_after_fees(low_f), net_after_fees(high_f)
    if net_high >= MONEY_GRADE_A_NET:
        grade = "A"
    elif net_high >= MONEY_GRADE_B_NET:
        grade = "B"
    else:
        grade = "C"
    return {
        "price_low": low_f, "price_high": high_f, "price_median": median,
        "net_low": net_low, "net_high": net_high,
        "money_grade": grade,
        "money_reason": "Shop range nets about $%d at the top; sold count unknown." % round(net_high),
        "sold_count": None, "reliable": True,
        "valuation_notes": ["Shop-entered range stands as the range."],
    }


def _empty_comp(note):
    return {
        "demand": "unknown",
        "demand_source": "",
        "price_low": None,
        "price_high": None,
        "price_median": None,
        "price_source": "",
        "price_note": note,
        "net_low": None,
        "net_high": None,
        "money_grade": "C",
        "money_reason": note,
        "sold_count": 0,
        "reliable": False,
        "valuation_notes": [note],
        "pull_minutes": None,
        "pull_source": "",
    }


class MockCompsAdapter:
    name = "mock-comps"

    def __init__(self, root):
        self.root = root

    def lookup(self, part_ids, allow_samples):
        """Return {part_id: comp}. Samples only when allow_samples is true."""
        if not allow_samples:
            return {
                pid: _empty_comp("No comp adapter with real sold data is connected, so there is no reliable price.")
                for pid in part_ids
            }
        path = os.path.join(self.root, "demo_cache", "comps.demo.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                board = json.load(fh)
        except (OSError, ValueError):
            board = {}
        result = {}
        for pid in part_ids:
            entry = board.get(pid)
            if not isinstance(entry, dict):
                result[pid] = _empty_comp("No sample comp on the demo board for this part.")
                continue
            valued = dict(entry)
            valued.pop("solds", None)
            valued.update(valuation_from_board(entry))
            result[pid] = valued
        return result


def get_adapter(root):
    # One adapter per service; the demo always uses the mock so no real
    # account is ever touched. A real adapter slots in here later.
    return MockCompsAdapter(root)
