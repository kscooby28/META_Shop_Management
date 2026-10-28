"""Verdict engine tests: grades, totals, overrides, rules, declines."""

import json
import os
import tempfile
import unittest

import verdict
from verdict import evaluate, load_rules, render_decline, save_rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_demo(name):
    with open(os.path.join(ROOT, "demo_cache", name), "r", encoding="utf-8") as fh:
        return json.load(fh)


class VerdictTest(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(ROOT, "rules.json"))
        self.parts = load_demo("harvest.demo.json")["parts"]
        self.comps = load_demo("comps.demo.json")

    def grades(self, inputs="use-comps"):
        if inputs == "use-comps":
            inputs = self.comps
        report = evaluate(self.parts, self.rules, inputs)
        return {v["part_id"]: v["verdict"] for v in report["verdicts"]}, report

    def test_demo_spread(self):
        grades, _ = self.grades()
        self.assertEqual(grades["p_diff"], "A")
        self.assertEqual(grades["p_mirror"], "A")
        self.assertEqual(grades["p_bumper"], "A")
        self.assertEqual(grades["p_wheel"], "A")
        self.assertEqual(grades["p_headlight"], "B")
        self.assertEqual(grades["p_handle"], "C")
        self.assertEqual(grades["p_taillight"], "C")

    def test_damaged_rule_fires(self):
        _, report = self.grades()
        tail = next(v for v in report["verdicts"] if v["part_id"] == "p_taillight")
        self.assertEqual(tail["rule_id"], "r_damaged")

    def test_thin_evidence_rule_fires(self):
        _, report = self.grades()
        handle = next(v for v in report["verdicts"] if v["part_id"] == "p_handle")
        self.assertEqual(handle["rule_id"], "r_thin_evidence")

    def test_totals_math(self):
        _, report = self.grades()
        totals = report["totals"]
        self.assertEqual(totals["A"]["low"], 45 + 120 + 80 + 900)
        self.assertEqual(totals["A"]["high"], 65 + 180 + 120 + 1100)
        self.assertEqual(totals["B"]["low"], 55)
        self.assertEqual(totals["B"]["high"], 75)
        self.assertIn("sure money", totals["A"]["plain_words"])
        self.assertIn("maybe money", totals["B"]["plain_words"])

    def test_unpriced_parts_excluded_by_name(self):
        _, report = self.grades()
        note = report["totals"]["excluded_note"]
        self.assertIn("driver door handle", note)
        self.assertIn("left taillight", note)

    def test_no_comps_means_no_total(self):
        _, report = self.grades({})
        totals = report["totals"]
        self.assertEqual(totals["A"]["high"], 0)
        self.assertIn("no A parts", totals["A"]["plain_words"])
        self.assertIn("7 parts have no reliable price", totals["excluded_note"])

    def test_unsourced_price_ignored(self):
        inputs = {"p_handle": {"price_low": 10, "price_high": 20}}  # no price_source
        _, report = self.grades(inputs)
        handle = next(v for v in report["verdicts"] if v["part_id"] == "p_handle")
        self.assertFalse(handle["inputs"]["price_known"])

    def test_override_wins_and_marks(self):
        inputs = dict(self.comps)
        inputs["p_headlight"] = dict(self.comps["p_headlight"], override="A")
        _, report = self.grades(inputs)
        head = next(v for v in report["verdicts"] if v["part_id"] == "p_headlight")
        self.assertEqual(head["verdict"], "A")
        self.assertTrue(head["overridden"])
        self.assertEqual(head["rule_id"], "override")
        self.assertEqual(report["totals"]["A"]["low"], 45 + 120 + 80 + 900 + 55)

    def test_rules_roundtrip_and_validation(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            path = fh.name
        try:
            saved = save_rules(path, self.rules)
            self.assertEqual(saved["labor_rate_per_hour"], 180)
            reloaded = load_rules(path)
            self.assertEqual(reloaded["thresholds"], saved["thresholds"])
            with self.assertRaises(ValueError):
                save_rules(path, {"thresholds": {}, "rules": []})
            bad = json.loads(json.dumps(self.rules))
            bad["rules"] = [r for r in bad["rules"] if r["id"] != "r_default"]
            with self.assertRaises(ValueError):
                save_rules(path, bad)
        finally:
            os.unlink(path)

    def test_decline_renders_cleanly(self):
        card = render_decline("n63-engine")
        self.assertEqual(card["verdict"], "declined")
        self.assertIn("declining", card["body"])
        self.assertTrue(card["next_step"])
        self.assertEqual(render_decline("oil-change")["verdict"], "declined")
        with self.assertRaises(KeyError):
            render_decline("nope")


if __name__ == "__main__":
    unittest.main()
