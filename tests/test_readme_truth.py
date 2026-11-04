"""README truth tests (WO14, WO22 P3): judge-first README, history in docs/.

The README speaks to a judge in sixty seconds; work-order history moved to
docs/build-log.md and measurements to docs/evals.md in WO22 P3. These tests
pin each claim where it now lives. The tour count still ties the README's
"eight taps" to the actual tour beats in web/app.js so the two cannot drift.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def build_log():
    with open(os.path.join(ROOT, "docs", "build-log.md"),
              encoding="utf-8") as fh:
        return fh.read()


def evals():
    with open(os.path.join(ROOT, "docs", "evals.md"),
              encoding="utf-8") as fh:
        return fh.read()


def tour_section():
    src = open(os.path.join(ROOT, "web", "app.js"), encoding="utf-8").read()
    start = src.index("===== guided tour (WO12)")
    end = src.index("===== end guided tour =====")
    return src[start:end]


class ReadmeTruthTest(unittest.TestCase):
    def test_pitch_names_theme_and_tour(self):
        text = readme()
        pitch, _, _ = text.partition("## Demo video")
        for phrase in ("I own a BMW performance shop",
                       "Build for Your World"):
            self.assertIn(phrase, pitch, phrase)
        for phrase in ("guided tour", "Take the tour", "eight taps"):
            self.assertIn(phrase, text, phrase)

    def test_tour_tap_count_matches_code(self):
        import re

        beats = re.findall(r'\{ id: "(\w+)"', tour_section())
        self.assertEqual(len(beats), 8)
        self.assertIn("eight taps", readme())

    def test_build_log_names_tour_entries(self):
        layout = build_log().partition("## Layout")[2]
        self.assertIn("Guided tour", layout)
        self.assertIn("both home", layout)

    def test_forced_demo_compare_named(self):
        self.assertIn("forced-demo Compare", readme())
        self.assertIn('runCompare({ demo: true })', tour_section())

    def test_live_evaluation_table_named(self):
        text = evals()
        self.assertIn("<!-- EVAL-SCALE:START -->", text)
        self.assertIn("Live evaluation at scale", text)
        self.assertIn("Agreement:", text)
        self.assertIn("docs/evals.md", readme())

    def test_zero_key_cold_start_named(self):
        run = readme().partition("## Quickstart")[2].partition("## Built")[0]
        for phrase in ("No keys, no signup", "python server.py",
                       "http://127.0.0.1:8765", "two doors"):
            self.assertIn(phrase, run, phrase)

    def test_money_grade_count_and_reliability_named(self):
        section = build_log().partition(
            "## Valuation engine")[2].partition("## Hybrid")[0]
        for phrase in ("money grade", "sold count", "reliability notes",
                       "13.25%", "3 solds", "400 days", "3x or more"):
            self.assertIn(phrase, section, phrase)

    def test_guided_first_tasks_named(self):
        section = build_log().partition(
            "## Usability pass")[2].partition("## Valuation")[0]
        self.assertIn("guided first tasks", section)

    def test_no_stale_wording(self):
        text = readme()
        for stale in ("next work order", "deferred", "TODO",
                      "rotation is confirmed", "Meta key rotation",
                      "until the key rotation"):
            self.assertNotIn(stale, text, stale)


if __name__ == "__main__":
    unittest.main()
