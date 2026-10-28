"""Enthusiast inventory helpers (server side).

The inventory itself lives in the browser (local-only demo profile): cars,
parts, owner notes, and owner-entered values never touch this server. What
the server provides: the anonymized demo seed, photo identification help,
VIN reads, and comps-adapter value lookups. Every served value carries a
source; anything without one is unknown, never guessed into a total.
"""

import json
import os


def load_seed(root):
    """Load demo_cache/inv_seed.demo.json (anonymized demo inventory)."""
    path = os.path.join(root, "demo_cache", "inv_seed.demo.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _label_key(label):
    return (label or "").lower().replace("(demo sample)", "").strip()


def comp_for_label(seed, label, allow_samples):
    """Value lookup for one part label.

    Demo mode consults the seed board; live mode has no connected comps and
    must say so. A miss in either mode is no-data, never a made-up number.
    """
    if not allow_samples:
        return {
            "value": None,
            "source": "",
            "note": "No live comps are connected, so there is no reliable value. Enter one or leave it unknown.",
        }
    board = (seed or {}).get("partComps") or {}
    for key, comp in board.items():
        if _label_key(key) == _label_key(label) and isinstance(comp, dict):
            return {
                "value": comp.get("value"),
                "source": comp.get("source") or "",
                "note": comp.get("note") or "",
            }
    return {
        "value": None,
        "source": "",
        "note": "No sample comp for this part on the demo board.",
    }
