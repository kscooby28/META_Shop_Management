"""In-process end-to-end flow test: same steps as scripts/smoke_demo.py.

Drives the real backend modules in session order (intake cache → harvest
cache → comps adapter → verdicts → listing draft → mock post → decline),
without binding sockets. Run scripts/smoke_demo.py against a live server
for the HTTP-level 10-out-of-10 check.
"""

import json
import os
import tempfile
import unittest

from comps import get_adapter as get_comps_adapter
from demo_cache import StepCache
from listing import demo_draft, get_post_adapter
from verdict import evaluate, load_rules, render_decline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FlowTest(unittest.TestCase):
    def test_full_demo_flow(self):
        cache = StepCache(ROOT)

        # Intake: demo car, trim honestly unknown.
        intake = cache.load_demo("intake")
        self.assertEqual(intake["car"]["trim"], "unknown")
        self.assertEqual(len(intake["parts"]), 7)

        # Harvest: every part tracked, every sighting source-tagged.
        harvest = cache.load_demo("harvest")
        parts = harvest["parts"]
        self.assertTrue(all(p["sightings"] for p in parts))
        self.assertTrue(all(s.get("source_tag") for p in parts for s in p["sightings"]))

        # Comps: samples in demo mode, honest no-data in live mode.
        adapter = get_comps_adapter(ROOT)
        ids = [p["id"] for p in parts]
        comps = adapter.lookup(ids, allow_samples=True)
        self.assertEqual(comps["p_diff"]["price_low"], 900)
        live = adapter.lookup(ids, allow_samples=False)
        self.assertTrue(all(not c["price_source"] for c in live.values()))

        # Verdicts + totals.
        rules = load_rules(os.path.join(ROOT, "rules.json"))
        report = evaluate(parts, rules, comps)
        grades = {v["part_id"]: v["verdict"] for v in report["verdicts"]}
        self.assertEqual(
            grades,
            {
                "p_mirror": "A",
                "p_bumper": "A",
                "p_wheel": "A",
                "p_headlight": "B",
                "p_handle": "C",
                "p_taillight": "C",
                "p_diff": "A",
            },
        )
        totals = report["totals"]
        self.assertEqual((totals["A"]["low"], totals["A"]["high"]), (1145, 1465))
        self.assertIn("sure money", totals["A"]["plain_words"])
        self.assertIn("maybe money", totals["B"]["plain_words"])

        # Listing draft + mock post (redirected to a temp dir).
        diff = next(p for p in parts if p["id"] == "p_diff")
        diff_verdict = next(v for v in report["verdicts"] if v["part_id"] == "p_diff")
        draft = demo_draft(diff, comps["p_diff"], diff_verdict, harvest["car"])
        self.assertIn("differential", draft["title"].lower())
        self.assertTrue(draft["price_hint"])
        with tempfile.TemporaryDirectory() as tmp:
            receipt = get_post_adapter(tmp).post("test-session", draft, ["ebay"])
            self.assertEqual(receipt["adapter"], "mock-outbox")
            self.assertIn("Nothing was sent", receipt["note"])

    def test_engine_deterministic_ten_runs(self):
        cache = StepCache(ROOT)
        parts = cache.load_demo("harvest")["parts"]
        comps = get_comps_adapter(ROOT).lookup([p["id"] for p in parts], True)
        rules = load_rules(os.path.join(ROOT, "rules.json"))
        first = json.dumps(evaluate(parts, rules, comps), sort_keys=True)
        for _ in range(9):
            self.assertEqual(json.dumps(evaluate(parts, rules, comps), sort_keys=True), first)

    def test_cache_notices_cover_every_failure(self):
        cache = StepCache(ROOT)

        class FakeErr:
            def __init__(self, kind):
                self.kind = kind

        for kind in ("demo", "credits", "auth", "bad_response", "unreachable"):
            note = cache.notice("intake", FakeErr(kind))
            self.assertTrue(note, kind)
        self.assertIn("declining", render_decline("n63-engine")["body"])


if __name__ == "__main__":
    unittest.main()
