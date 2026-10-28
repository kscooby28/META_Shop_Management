"""README truth tests (WO14): every shipped feature named, no stale words.

Documentation-only order: these tests pin the README claims against the
shipped code. The tour count ties the README's "ten taps" to the actual
tour beats in web/app.js so the two cannot drift apart.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def tour_section():
    src = open(os.path.join(ROOT, "web", "app.js"), encoding="utf-8").read()
    start = src.index("===== guided tour (WO12)")
    end = src.index("===== end guided tour =====")
    return src[start:end]


class ReadmeTruthTest(unittest.TestCase):
    def test_spine_section_names_tour(self):
        text = readme()
        spine, _, _ = text.partition("## The Bay side")
        for phrase in ("guided tour", "Take the tour", "ten taps",
                       "no hunting", "no keys", "recording path",
                       "first-run path"):
            self.assertIn(phrase, spine, phrase)

    def test_tour_tap_count_matches_code(self):
        import re

        beats = re.findall(r'\{ id: "(\w+)"', tour_section())
        self.assertEqual(len(beats), 10)
        self.assertIn("ten taps", readme())

    def test_layout_names_tour_entries(self):
        text = readme()
        layout = text.partition("## Layout")[2].partition("<!--")[0]
        self.assertIn("Guided tour", layout)
        self.assertIn("both home", layout)

    def test_forced_demo_compare_named(self):
        self.assertIn("forced-demo Compare", readme())
        self.assertIn('runCompare({ demo: true })', tour_section())

    def test_live_evaluation_table_named(self):
        text = readme()
        self.assertIn("<!-- EVAL-SCALE:START -->", text)
        self.assertIn("Live evaluation at scale", text)
        self.assertIn("Agreement:", text)

    def test_zero_key_cold_start_named(self):
        run = readme().partition("## Run it")[2].partition("## The flow")[0]
        for phrase in ("No keys, no signup", "python server.py",
                       "http://127.0.0.1:8765", "four tabs"):
            self.assertIn(phrase, run, phrase)

    def test_money_grade_count_and_reliability_named(self):
        section = readme().partition("## Valuation engine")[2].partition("## Hybrid")[0]
        for phrase in ("money grade", "sold count", "reliability notes",
                       "13.25%", "3 solds", "400 days", "3x or more"):
            self.assertIn(phrase, section, phrase)

    def test_guided_first_tasks_named(self):
        section = readme().partition("## Usability pass")[2].partition("## Valuation")[0]
        self.assertIn("guided first tasks", section)

    def test_no_stale_wording(self):
        text = readme()
        for stale in ("next work order", "deferred", "TODO"):
            self.assertNotIn(stale, text, stale)


if __name__ == "__main__":
    unittest.main()
