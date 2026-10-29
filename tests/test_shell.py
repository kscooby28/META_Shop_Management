"""App shell tests (WO17): doors, camera inputs, Copilot header, lines, theme.

Presentation, navigation, and photo input only. The flows, grades, and
gates underneath are pinned by the existing suites, which must stay
green untouched.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def view_block(html, view_id):
    start = html.index('id="%s"' % view_id)
    ends = [html.index('id="view-', start + 1) for _ in range(1)
            if 'id="view-' in html[start + 1:]]
    mains = html.index("</main>", start)
    end = min(ends + [mains])
    return html[start:end]


VIEWS = ("view-home", "view-yard", "view-bay", "view-inventory", "view-compare")


class DoorsTest(unittest.TestCase):
    def test_three_doors(self):
        html = read("web/index.html")
        for door, words in (("door-bay", ("Bay", "Fix it")),
                            ("door-yard", ("Yard", "Strip it")),
                            ("door-driveway", ("Driveway", "Your own car"))):
            self.assertIn('id="%s"' % door, html)
            for word in words:
                self.assertIn(word, html)

    def test_doors_route_to_views(self):
        app = read("web/app.js")
        for door, view in (("door-bay", "bay"), ("door-yard", "yard"),
                           ("door-driveway", "inventory")):
            self.assertIn('"%s"' % door, app)
            self.assertIn('showView("%s")' % view, app)

    def test_compare_lives_under_yard(self):
        html = read("web/index.html")
        self.assertIn('id="btnCompareOpen"', view_block(html, "view-yard"))
        self.assertIn("Yard results", view_block(html, "view-compare"))

    def test_back_out_of_every_screen(self):
        html = read("web/index.html")
        for view, back in (("view-yard", "backYard"), ("view-bay", "backBay"),
                           ("view-inventory", "backInv"),
                           ("view-compare", "backCompare")):
            self.assertIn('id="%s"' % back, view_block(html, view), view)

    def test_settings_is_a_gear_not_a_tab(self):
        html = read("web/index.html")
        self.assertIn('id="navGear"', html)
        self.assertIn("⚙", html)
        self.assertNotIn("tabYard", html)
        self.assertNotIn("tabBay", html)
        self.assertNotIn("tabInventory", html)
        self.assertNotIn("tabCompare", html)

    def test_every_view_has_its_screen_line(self):
        html = read("web/index.html")
        for view in VIEWS:
            block = view_block(html, view)
            self.assertIn("screen-line", block, view)
            line = block.split("screen-line", 1)[1].split("</p>", 1)[0]
            self.assertGreater(len(re.sub(r"<[^>]+>", "", line).strip()), 20, view)

    def test_settings_has_its_screen_line(self):
        self.assertIn("screen-line", read("web/app.js"))


class CameraTest(unittest.TestCase):
    PAIRS = (("fileCamera", "fileInput", "btnPhoto"),
             ("bayVinCamera", "bayVin", "btnBayVinPhoto"),
             ("invCarPhotoCamera", "invCarPhoto", "btnInvCarPhotoCam"),
             ("invCarVinCamera", "invCarVin", "btnInvCarVinCam"),
             ("invPartPhotoCamera", "invPartPhoto", "btnInvPartPhotoCam"))

    def test_camera_input_beside_upload_fallback(self):
        html = read("web/index.html")
        for cam, fallback, btn in self.PAIRS:
            cam_tag = re.search(r'<input[^>]*id="%s"[^>]*>' % cam, html)
            self.assertIsNotNone(cam_tag, cam)
            self.assertIn('capture="environment"', cam_tag.group(0), cam)
            self.assertIn('id="%s"' % fallback, html)
            self.assertIn('id="%s"' % btn, html)

    def test_camera_buttons_say_photo(self):
        html = read("web/index.html")
        for _, _, btn in self.PAIRS:
            tag = re.search(r'<button[^>]*id="%s"[^>]*>([^<]*)</button>' % btn, html)
            self.assertIsNotNone(tag, btn)
            self.assertIn("photo", tag.group(1).lower(), btn)

    def test_every_camera_wired_to_its_fallback(self):
        app = read("web/app.js")
        for cam, fallback, btn in self.PAIRS:
            self.assertIn('twinCamera("%s", "%s", "%s")' % (cam, fallback, btn), app)


class CopilotHeaderTest(unittest.TestCase):
    def test_header_explains_itself(self):
        panel = read("web/index.html").partition('<aside id="panel"')[2]
        for phrase in ("Ask me about this car or part",
                       "I answer from the case file", "never guess"):
            self.assertIn(phrase, panel, phrase)

    def test_chips_demonstrate(self):
        panel = read("web/index.html").partition('<aside id="panel"')[2]
        chips = re.findall(r"data-chip=", panel)
        self.assertGreaterEqual(len(chips), 3)


class ThemeTest(unittest.TestCase):
    def test_tokens_defined(self):
        css = read("web/styles.css")
        root = css.partition(":root")[2].partition("}")[0]
        for token in ("--bg", "--surface", "--paper", "--ink", "--muted",
                      "--line", "--accent", "--accent-ink", "--grade-a",
                      "--grade-b", "--grade-c"):
            self.assertIn(token, root, token)
        self.assertIn("--accent: #e8a33d", root)

    def test_no_one_off_colors(self):
        css = read("web/styles.css")
        without_root = css.partition("}")[2]
        without_comments = re.sub(r"/\*.*?\*/", "", without_root, flags=re.S)
        ids = set(re.findall(r'id="([\w-]+)"', read("web/index.html")))
        hashes = re.findall(r"#([\w-]+)", without_comments)
        self.assertEqual(sorted(set(hashes) - ids), [])
        self.assertEqual(re.findall(r"rgba?\s*\(", without_comments), [])
        self.assertEqual(re.findall(r"hsla?\s*\(", without_comments), [])

    def test_dark_garage_body(self):
        css = read("web/styles.css")
        self.assertIn("background: var(--bg)", css)


class PrimaryTest(unittest.TestCase):
    def test_one_primary_per_screen(self):
        html = read("web/index.html")
        counts = {}
        for view in VIEWS:
            counts[view] = len(re.findall(r'class="primary[" ]',
                                          view_block(html, view)))
        self.assertEqual(counts["view-bay"], 1)
        self.assertEqual(counts["view-inventory"], 1)
        self.assertEqual(counts["view-compare"], 1)
        self.assertEqual(counts["view-home"], 0)

    def test_approve_keeps_its_gate_prominence(self):
        html = read("web/index.html")
        self.assertIn('id="btnApprove"', html)
        tag = re.search(r'<button[^>]*id="btnApprove"[^>]*>', html).group(0)
        self.assertIn("primary approve", tag)


if __name__ == "__main__":
    unittest.main()
