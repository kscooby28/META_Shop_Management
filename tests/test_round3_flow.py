"""Round-3 pins: garage flow rebuilt photo-first, demo-frame ghosts gone,
landing still under labeled doors. Offline; look and feel stay a smoke proof."""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_web(name):
    with open(os.path.join(ROOT, "web", name), encoding="utf-8") as fh:
        return fh.read()


def calm_block(css):
    start = css.index("@media (prefers-reduced-motion: reduce)")
    end = css.index("@media (prefers-reduced-motion: no-preference)", start)
    return css[start:end]


class GhostTest(unittest.TestCase):
    """Real photos survive the demo fallback; sample frames never haunt them."""

    def test_harvest_fallback_keeps_photos(self):
        app = read_web("app.js")
        fn = app[app.index("async function runHarvest"):
                 app.index("async function runVerdicts")]
        self.assertIn("Gallery.isDemoFrame(i.name)", fn)
        self.assertIn("your photos kept", fn)
        self.assertNotIn("state.images = DEMO_FRAMES.map((d) => ({ name: d.name, src: d.src }));\n    renderThumbs();\n    renderCar",
                         fn)

    def test_strip_only_shows_loaded_photos(self):
        app = read_web("app.js")
        fn = app[app.index("function frameOrder"):
                 app.index("function overlayColor")]
        self.assertIn("have.has(s.frame)", fn)

    def test_part_list_needs_a_loaded_photo(self):
        app = read_web("app.js")
        fn = app[app.index("function renderPartList"):
                 app.index("function highlightPart")]
        self.assertIn("state.images.some((i) => i.name === thumb.frame)", fn)

    def test_viewer_names_demo_boxes_honestly(self):
        app = read_web("app.js")
        fn = app[app.index("function renderViewer"):
                 app.index("function renderFrames")]
        self.assertIn("Sample boxes belong to the demo car", fn)


class PagesTest(unittest.TestCase):
    """Garage index: photo-first, one parts-and-values page, plain words."""

    def test_seven_garage_pages(self):
        app = read_web("app.js")
        chunk = app[app.index("const VIEW_PAGES"):
                    app.index("function pageForSection")]
        self.assertEqual(len(re.findall(r'\{ n: "G\d"', chunk)), 7)
        self.assertNotIn('"G8"', chunk)
        self.assertNotIn('"G9"', chunk)

    def test_parts_and_values_merged(self):
        app = read_web("app.js")
        chunk = app[app.index("const VIEW_PAGES"):
                    app.index("function pageForSection")]
        self.assertIn('title: "Parts & values"', chunk)
        self.assertIn('secs: ["sec-iparts", "sec-itotals", "sec-verdicts", "sec-totals"]',
                      chunk)
        self.assertNotIn("Money & compare", chunk)

    def test_photos_before_values_in_dom(self):
        html = read_web("index.html")
        self.assertLess(html.index('id="sec-intake"'),
                        html.index('id="sec-iparts"'))
        self.assertLess(html.index('id="sec-harvest"'),
                        html.index('id="sec-verdicts"'))

    def test_step_numbers_follow_dom_order(self):
        html = read_web("index.html")
        inv = html[html.index('id="view-inventory"'):
                   html.index('id="view-compare"')]
        steps = re.findall(r'<section id="([\w\-]+)">\s*<h2><span class="step">(\d+)</span>',
                           inv)
        self.assertEqual([n for _, n in steps],
                         [str(i) for i in range(1, len(steps) + 1)])
        self.assertEqual(
            [s for s, _ in steps],
            ["sec-icars", "sec-iknow", "sec-intake", "sec-harvest",
             "sec-iparts", "sec-itotals", "sec-verdicts", "sec-totals",
             "sec-listing", "sec-rules"])

    def test_index_cards_say_step_n(self):
        app = read_web("app.js")
        fn = app[app.index("function refreshIndex"):
                 app.index("function buildIndex")]
        self.assertIn('"Step " + (i + 1) + " · " + p.title', fn)
        self.assertNotIn('p.n + " · " + p.title', fn)

    def test_statuses_are_plain_words(self):
        app = read_web("app.js")
        fn = app[app.index("function pageStatus"):
                 app.index("function refreshIndex")]
        self.assertNotIn('"Ready"', fn)
        self.assertNotIn('"Not started"', fn)
        self.assertIn('"Done"', fn)
        self.assertIn('"To do"', fn)


class HalfMotionTest(unittest.TestCase):
    """Landing rests still under labeled doors; no hover zoom anywhere."""

    def test_no_landing_hover_motion(self):
        css = read_web("styles.css")
        for dead in ("halfpushshop", "halfpushgarage", "bclone",
                     "scenedrift", "scenepush", "scenecar", "scenewalk",
                     "sceneFx", "SceneFx", "--t-drive", "--t-walk",
                     "--t-drift", "move-car"):
            self.assertNotIn(dead, css, dead)
        html = read_web("index.html")
        self.assertNotIn("bclone", html)

    def test_backdrop_is_the_only_landing_image(self):
        html = read_web("index.html")
        scene = html[html.index('id="homeScene"'):
                     html.index('id="view-bay"')]
        self.assertEqual(scene.count("<img"), 1)
        self.assertIn('src="assets/landing-2door.jpg"', scene)

    def test_doors_are_labeled_buttons(self):
        html = read_web("index.html")
        for zid, words in (("door-bay", ("Shop", "fix it")),
                           ("door-garage", ("DIY Garage", "your cars"))):
            body = re.search(r'<button[^>]*id="%s"[^>]*>(.*?)</button>' % zid,
                             html, re.S).group(1)
            for word in words:
                self.assertIn(word, body, zid)
            self.assertIn("doorlabel", body, zid)

    def test_images_stir_on_hover(self):
        css = read_web("styles.css")
        self.assertIn(".gtile:hover img.timg { transform: scale(1.06); }", css)
        self.assertIn(".strip figure:hover img { transform: scale(1.07); }",
                      css)
        self.assertIn(".thumbs figure:hover img { transform: scale(1.07); }",
                      css)

    def test_calm_still_cuts_tile_motion(self):
        calm = calm_block(read_web("styles.css"))
        self.assertNotIn("bclone", calm)
        self.assertIn(".gtile:hover img.timg", calm)


class ShopRateTest(unittest.TestCase):
    """Shop rate lives on the shop side; DIY rules hold grades only."""

    def test_diy_page_names_grades_only(self):
        app = read_web("app.js")
        chunk = app[app.index("const VIEW_PAGES"):
                    app.index("function pageForSection")]
        self.assertIn('title: "Verdict rules"', chunk)
        self.assertNotIn("Rules & rate", chunk)
        self.assertNotIn("shop rate", chunk)

    def test_rules_form_has_no_rate(self):
        app = read_web("app.js")
        fn = app[app.index("function renderRules"):
                 app.index("async function saveRules")]
        self.assertNotIn("Shop rate", fn)
        self.assertNotIn("__rate", fn)
        save = app[app.index("async function saveRules"):
                   app.index("function fillBayRate")]
        self.assertIn("const rate = state.rules.labor_rate_per_hour;", save)

    def test_bay_labor_owns_the_rate(self):
        html = read_web("index.html")
        labor = html[html.index('id="sec-blabor"'):
                     html.index('id="sec-best"')]
        self.assertIn('id="bayRate"', labor)
        self.assertIn('id="btnBayRate"', labor)
        self.assertIn('id="bayRateHead"', html)
        app = read_web("app.js")
        for marker in ("function fillBayRate", "function saveShopRate",
                       "btnBayRate", "labor_rate_per_hour: rate"):
            self.assertIn(marker, app, marker)


if __name__ == "__main__":
    unittest.main()
