"""Sold-comp adapter: isolated per-service credentials, mock for demo.

The verdict engine prices parts only from comps that carry a source. This
module is the single place comp sources plug in:

- ``MockCompsAdapter`` (this build): returns the tagged demo-sample board in
  demo mode, and reports "no reliable data" in live mode. It never invents a
  price and never touches a real account.
- ``EbaySoldCompsAdapter`` (later step): same interface, credentials from its
  own env keys, real SOLD listings. Not built in this work order.

A comp entry shape: demand, demand_source, price_low, price_high,
price_source, price_note, pull_minutes, pull_source. Any price without a
``*_source`` is ignored downstream.
"""

import json
import os


def _empty_comp(note):
    return {
        "demand": "unknown",
        "demand_source": "",
        "price_low": None,
        "price_high": None,
        "price_source": "",
        "price_note": note,
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
            if isinstance(entry, dict):
                result[pid] = entry
            else:
                result[pid] = _empty_comp("No sample comp on the demo board for this part.")
        return result


def get_adapter(root):
    # One adapter per service; the demo always uses the mock so no real
    # account is ever touched. A real adapter slots in here later.
    return MockCompsAdapter(root)
