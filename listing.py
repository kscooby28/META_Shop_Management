"""Listing factory: draft card with Edit / Approve / Post.

Spark writes the draft from harvest evidence plus sourced comps, flaws
included. In demo mode a local template builds the same card shape so the
flow runs offline. Posting goes through an isolated adapter; this build
ships only the mock adapter, which writes the approved draft to a local
outbox file. Nothing leaves the machine. Post without Approve is refused.
"""

import json
import os
import time

from meta_client import MetaAPIError


def _money_range(comp):
    low = comp.get("price_low")
    high = comp.get("price_high")
    if low is None and high is None:
        return None
    if low is None:
        return "$%d" % round(high)
    if high is None:
        return "$%d" % round(low)
    if round(low) == round(high):
        return "$%d" % round(high)
    return "$%d to $%d" % (round(low), round(high))


def demo_draft(part, comp, verdict_info, car):
    """Local template draft: same card shape as the Spark draft, offline."""
    label = part.get("label", "part")
    intact = part.get("intact", "unknown")
    intact_note = part.get("intact_note", "")
    frames = [s.get("frame", "?") for s in (part.get("sightings") or [])]
    price = _money_range(comp)
    car_bits = [car.get("year"), car.get("make"), car.get("model")]
    car_line = " ".join(str(b) for b in car_bits if b and b != "unknown")
    if intact == "yes":
        condition = "Used, looks intact in the photos. %s" % intact_note
    elif intact == "no":
        condition = "For parts or repair: flaw visible in the photos. %s" % intact_note
    else:
        condition = "Condition unclear from the photos: %s" % (intact_note or "please ask for more photos.")
    lines = [
        "Used %s from a %s (harvest find)." % (label, car_line or "parts car"),
        "",
        "Condition: %s" % condition.strip(),
        "Seen in: %s." % (", ".join(frames) if frames else "photos"),
    ]
    if verdict_info:
        lines.append(
            "Shop note: graded %s (%s)."
            % (verdict_info.get("verdict", "?"), verdict_info.get("verdict_means", ""))
        )
    if price and comp.get("price_source"):
        lines.append("Asking about %s based on %s." % (price, comp.get("price_source")))
    else:
        lines.append("No reliable price found yet, so make an offer and we will check comps.")
    lines += ["", "Flaws are shown in the photos. Ask for more angles before you buy."]
    return {
        "title": "Used %s — %s" % (label, car_line or "parts car find"),
        "description": "\n".join(lines).strip(),
        "condition": condition.strip(),
        "price_hint": price,
        "price_source": comp.get("price_source") or "",
        "source": "demo-cache",
    }


def build_live_draft(part, comp, verdict_info, car):
    """Ask Spark to write the listing; raises MetaAPIError on any problem."""
    from meta_client import draft_listing

    return draft_listing(part, comp, verdict_info, car)


class MockPostAdapter:
    """The only post adapter in this build: local outbox, no network."""

    name = "mock-outbox"

    def __init__(self, root):
        self.root = root

    def post(self, session_id, draft, destinations):
        folder = os.path.join(self.root, "demo_cache", "live", session_id or "no-session", "outbox")
        os.makedirs(folder, exist_ok=True)
        receipt = {
            "posted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "adapter": self.name,
            "destinations": destinations,
            "title": draft.get("title"),
            "note": "Mock post: saved on this machine only. Nothing was sent anywhere.",
        }
        path = os.path.join(folder, "post-%d.json" % int(time.time() * 1000))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"draft": draft, "receipt": receipt}, fh, indent=2)
        return receipt


def get_post_adapter(root):
    return MockPostAdapter(root)
