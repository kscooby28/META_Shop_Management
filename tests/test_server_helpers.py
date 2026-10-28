"""Server helper tests: exercise real Handler method bodies without sockets."""

import json
import os
import unittest

import server
from server import Handler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_demo(name):
    with open(os.path.join(ROOT, "demo_cache", name), "r", encoding="utf-8") as fh:
        return json.load(fh)


class ServerHelperTest(unittest.TestCase):
    def setUp(self):
        harvest = load_demo("harvest.demo.json")
        self.session = {
            "harvest": harvest,
            "comps": load_demo("comps.demo.json"),
            "verdicts": {"verdicts": [], "totals": {}},
        }

    def test_case_summary_before_and_after_verdicts(self):
        early = Handler._case_summary(None, self.session)
        self.assertIn("no verdicts yet", early)
        from verdict import evaluate, load_rules

        rules = load_rules(os.path.join(ROOT, "rules.json"))
        report = evaluate(self.session["harvest"]["parts"], rules, self.session["comps"])
        self.session["verdicts"] = report
        full = Handler._case_summary(None, self.session)
        self.assertIn("grade A", full)
        self.assertIn("Total A:", full)

    def test_local_chat_answers(self):
        self.assertIn("No car yet", Handler._local_chat_answer(None, None, "Identify this car"))
        car = Handler._local_chat_answer(None, self.session, "Identify this car")
        self.assertIn("325", car)
        self.assertIn("unknown", car)
        self.assertIn("No verdicts yet", Handler._local_chat_answer(None, self.session, "Why is this part a B?"))
        from verdict import evaluate, load_rules

        rules = load_rules(os.path.join(ROOT, "rules.json"))
        self.session["verdicts"] = evaluate(
            self.session["harvest"]["parts"], rules, self.session["comps"]
        )
        why = Handler._local_chat_answer(None, self.session, "Why is this part a B?")
        self.assertIn("headlight", why.lower())
        self.assertIn("listing", Handler._local_chat_answer(None, self.session, "Draft the listing").lower())

    def test_cutout_and_merge(self):
        diff = next(p for p in self.session["harvest"]["parts"] if p["id"] == "p_diff")
        cut = Handler._cutout_spec(None, diff)
        self.assertEqual(cut["frame"], "demo-frame-4")
        self.assertEqual(cut["box"], [300, 360, 700, 570])
        merged = Handler._merged_inputs(None, self.session, {"p_diff": {"price_low": 1}})
        self.assertEqual(merged["p_diff"]["price_low"], 1)  # shop-typed wins
        self.assertEqual(merged["p_diff"]["price_high"], 1100)  # comp fills the rest

    def test_module_imports_cleanly(self):
        self.assertTrue(server.ROOT.endswith("META_Shop_Management") or server.ROOT)


if __name__ == "__main__":
    unittest.main()
