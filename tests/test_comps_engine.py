"""Comps engine tests (WO8 phase B): fresh valuation from solds + shop ranges."""

import os
import unittest

from comps import (
    build_valuation,
    get_adapter,
    net_after_fees,
    valuation_from_board,
    valuation_from_shop,
)
from demo_cache import StepCache
from verdict import evaluate, load_rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def solds(*prices, **kw):
    age = kw.get("age_days", 30)
    return [{"price": p, "age_days": age} for p in prices]


class EngineRangeTest(unittest.TestCase):
    def test_range_median_nets(self):
        v = build_valuation(solds(900, 950, 1000, 1050, 1100))
        self.assertEqual((v["price_low"], v["price_high"], v["price_median"]),
                         (900.0, 1100.0, 1000.0))
        self.assertEqual(v["net_high"], net_after_fees(1100))
        self.assertEqual(v["sold_count"], 5)
        self.assertTrue(v["reliable"])
        self.assertEqual(v["valuation_notes"], [])

    def test_fee_math_exact(self):
        self.assertEqual(net_after_fees(100), 86.75)

    def test_empty_feed_has_no_range(self):
        v = build_valuation([])
        self.assertIsNone(v["price_low"])
        self.assertIsNone(v["net_high"])
        self.assertEqual(v["money_grade"], "C")
        self.assertFalse(v["reliable"])
        self.assertTrue(v["valuation_notes"])

    def test_thin_feed_ranges_but_grades_c(self):
        v = build_valuation(solds(50, 60))
        self.assertEqual((v["price_low"], v["price_high"]), (50.0, 60.0))
        self.assertEqual(v["money_grade"], "C")
        self.assertFalse(v["reliable"])
        self.assertTrue(any("thin" in n for n in v["valuation_notes"]))

    def test_stale_solds_excluded_and_named(self):
        v = build_valuation(
            [{"price": 50, "age_days": 500}, {"price": 60, "age_days": 10},
             {"price": 70, "age_days": 20}, {"price": 80, "age_days": 30}]
        )
        self.assertEqual((v["price_low"], v["price_high"]), (60.0, 80.0))
        self.assertEqual(v["sold_count"], 3)
        self.assertTrue(any("stale" in n for n in v["valuation_notes"]))

    def test_all_stale_means_no_range(self):
        v = build_valuation([{"price": 50, "age_days": 500}])
        self.assertIsNone(v["price_low"])
        self.assertFalse(v["reliable"])

    def test_contradictory_span_named_range_stands(self):
        v = build_valuation(solds(50, 60, 200))
        self.assertEqual((v["price_low"], v["price_high"]), (50.0, 200.0))
        self.assertTrue(any("condition" in n for n in v["valuation_notes"]))

    def test_bad_prices_dropped_and_named(self):
        v = build_valuation([{"price": 50}, {"price": -5}, {"price": "x"},
                             {"price": 60}, {"price": 70}])
        self.assertEqual(v["sold_count"], 3)
        self.assertTrue(any("usable price" in n for n in v["valuation_notes"]))

    def test_missing_ages_named(self):
        v = build_valuation([{"price": 50}, {"price": 60}, {"price": 70}])
        self.assertEqual(v["sold_count"], 3)
        self.assertTrue(any("no age" in n for n in v["valuation_notes"]))


class EngineGradeTest(unittest.TestCase):
    def test_money_thresholds(self):
        self.assertEqual(build_valuation(solds(900, 1000, 1100))["money_grade"], "A")
        self.assertEqual(build_valuation(solds(45, 55, 65))["money_grade"], "B")
        self.assertEqual(build_valuation(solds(10, 12, 14))["money_grade"], "C")

    def test_reasons_carry_numbers(self):
        v = build_valuation(solds(900, 1000, 1100))
        self.assertIn("954", v["money_reason"])
        self.assertIn("3 solds", v["money_reason"])


class ShopRangeTest(unittest.TestCase):
    def test_shop_numbers_stand(self):
        v = valuation_from_shop(200, 300)
        self.assertEqual((v["price_low"], v["price_high"]), (200.0, 300.0))
        self.assertEqual(v["money_grade"], "A")
        self.assertIsNone(v["sold_count"])
        self.assertTrue(v["reliable"])
        self.assertIn("sold count unknown", v["money_reason"])

    def test_shop_single_number(self):
        v = valuation_from_shop(150, None)
        self.assertEqual((v["price_low"], v["price_high"]), (150.0, 150.0))

    def test_shop_blank(self):
        v = valuation_from_shop(None, None)
        self.assertIsNone(v["price_low"])
        self.assertFalse(v["reliable"])


class AdapterIntegrationTest(unittest.TestCase):
    def setUp(self):
        cache = StepCache(ROOT)
        self.parts = cache.load_demo("harvest")["parts"]
        self.comps = get_adapter(ROOT).lookup([p["id"] for p in self.parts], True)

    def test_demo_ranges_reproduced(self):
        self.assertEqual(
            (self.comps["p_diff"]["price_low"], self.comps["p_diff"]["price_high"]),
            (900.0, 1100.0),
        )
        self.assertEqual(self.comps["p_diff"]["price_median"], 1000.0)
        self.assertEqual(self.comps["p_diff"]["sold_count"], 5)
        self.assertTrue(self.comps["p_diff"]["reliable"])

    def test_demo_money_grades(self):
        grades = {pid: c["money_grade"] for pid, c in self.comps.items()}
        self.assertEqual(grades["p_diff"], "A")
        self.assertEqual(grades["p_bumper"], "A")
        self.assertEqual(grades["p_wheel"], "A")
        self.assertEqual(grades["p_mirror"], "B")
        self.assertEqual(grades["p_headlight"], "B")
        self.assertEqual(grades["p_handle"], "C")
        self.assertEqual(grades["p_taillight"], "C")

    def test_no_price_parts_stay_empty(self):
        self.assertIsNone(self.comps["p_handle"]["price_low"])
        self.assertIsNone(self.comps["p_taillight"]["price_high"])
        self.assertFalse(self.comps["p_handle"]["reliable"])

    def test_board_carries_no_raw_solds_downstream(self):
        self.assertNotIn("solds", self.comps["p_diff"])

    def test_static_board_ranges_match_engine(self):
        import json

        with open(os.path.join(ROOT, "demo_cache", "comps.demo.json"),
                  encoding="utf-8") as fh:
            board = json.load(fh)
        for pid, entry in board.items():
            valued = valuation_from_board(entry)
            self.assertEqual(valued["price_low"], entry["price_low"], pid)
            self.assertEqual(valued["price_high"], entry["price_high"], pid)

    def test_rule_grades_and_totals_pinned(self):
        rules = load_rules(os.path.join(ROOT, "rules.json"))
        report = evaluate(self.parts, rules, self.comps)
        grades = {v["part_id"]: v["verdict"] for v in report["verdicts"]}
        self.assertEqual(
            grades,
            {"p_mirror": "A", "p_bumper": "A", "p_wheel": "A",
             "p_headlight": "B", "p_handle": "C", "p_taillight": "C",
             "p_diff": "A"},
        )
        totals = report["totals"]
        self.assertEqual((totals["A"]["low"], totals["A"]["high"]), (1145, 1465))
        diff = next(v for v in report["verdicts"] if v["part_id"] == "p_diff")
        self.assertEqual(diff["inputs"]["money_grade"], "A")
        self.assertIn("954", diff["inputs"]["money_reason"])

    def test_live_mode_still_no_data(self):
        live = get_adapter(ROOT).lookup(["p_diff"], False)
        self.assertIsNone(live["p_diff"]["price_low"])
        self.assertEqual(live["p_diff"]["money_grade"], "C")
        self.assertFalse(live["p_diff"]["reliable"])

    def test_shop_merge_revalues(self):
        from server import Handler

        merged = Handler._merged_inputs(
            None,
            {"harvest": {"parts": self.parts}, "comps": self.comps},
            {"p_diff": {"price_low": 200, "price_high": 300,
                        "price_source": "shop-entered"}},
        )
        entry = merged["p_diff"]
        self.assertEqual((entry["price_low"], entry["price_high"]), (200.0, 300.0))
        self.assertIn("Shop range", entry["money_reason"])
        self.assertIn("shop-entered", entry["price_source"])


if __name__ == "__main__":
    unittest.main()
