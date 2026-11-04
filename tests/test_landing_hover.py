"""Landing hover highlight: hovering a door highlights that half.

Regression pins for the owner's landing direction: hover over the shop
half highlights shop, hover over the garage half highlights home/garage.
Highlight only: no zoom, scale, or motion on the doors.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_web(name):
    with open(os.path.join(ROOT, "web", name), encoding="utf-8") as fh:
        return fh.read()


def door_rules(css):
    out = []
    for match in re.finditer(r"([^{}]*\.door[^{}]*)\{([^{}]*)\}", css):
        out.append((match.group(1).strip(), match.group(2)))
    return out


class LandingDoorsTest(unittest.TestCase):
    def test_two_labeled_doors_over_photo(self):
        html = read_web("index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-bay"')]
        self.assertIn('id="door-bay"', home)
        self.assertIn('id="door-garage"', home)
        self.assertIn("Shop", home)
        self.assertIn("DIY Garage", home)

    def test_hover_highlights_hovered_half(self):
        css = read_web("styles.css")
        hover = [body for sel, body in door_rules(css)
                 if ":hover" in sel and ":not(" not in sel]
        self.assertTrue(hover)
        self.assertTrue(any("background:" in body and "transparent" not in body
                            for body in hover))

    def test_hover_dims_other_half(self):
        css = read_web("styles.css")
        self.assertIn(".entrances:hover .door.zone:not(:hover)", css)

    def test_doors_never_scale_or_move(self):
        css = read_web("styles.css")
        for sel, body in door_rules(css):
            self.assertNotIn("transform", body, sel)
            self.assertNotIn("scale(", body, sel)
            self.assertNotIn("transition", body, sel)

    def test_keyboard_focus_matches_hover(self):
        css = read_web("styles.css")
        focus = [body for sel, body in door_rules(css)
                 if "focus-visible" in sel]
        self.assertTrue(focus)
        self.assertTrue(any("background:" in body and "transparent" not in body
                            for body in focus))


if __name__ == "__main__":
    unittest.main()
