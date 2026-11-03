"""Round-3 pins: garage flow rebuilt photo-first, demo-frame ghosts gone,
landing hover life. Offline; look and feel stay a smoke proof."""

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


class HoverLifeTest(unittest.TestCase):
    """Landing breathes (drift + push); images stir; calm cuts everything."""

    def test_scene_keyframes_exist(self):
        css = read_web("styles.css")
        self.assertIn("@keyframes scenedrift", css)
        self.assertIn("@keyframes scenepushbay", css)
        self.assertIn("@keyframes scenepushgarage", css)
        self.assertNotIn("scenecar", css)
        self.assertNotIn("scenewalk", css)

    def test_zones_stay_empty(self):
        html = read_web("index.html")
        for zid in ("door-bay", "door-garage"):
            body = re.search(r'<button[^>]*id="%s"[^>]*>(.*?)</button>' % zid,
                             html, re.S).group(1)
            self.assertEqual(body.strip(), "", zid)

    def test_layers_share_drift_registration(self):
        css = read_web("styles.css")
        self.assertIn(".backdrop, .entrances, #sceneFx { animation: scenedrift",
                      css)
        self.assertIn(".scene:has(#door-bay:hover) .backdrop", css)
        self.assertIn(".scene:has(#door-garage:hover) .backdrop", css)

    def test_images_stir_on_hover(self):
        css = read_web("styles.css")
        self.assertIn(".gtile:hover img.timg { transform: scale(1.06); }", css)
        self.assertIn(".strip figure:hover img { transform: scale(1.07); }",
                      css)
        self.assertIn(".thumbs figure:hover img { transform: scale(1.07); }",
                      css)

    def test_calm_cuts_hover_life(self):
        calm = calm_block(read_web("styles.css"))
        self.assertIn(".backdrop, .entrances, #sceneFx { animation: none;",
                      calm)
        self.assertIn(".gtile:hover img.timg", calm)
        self.assertIn(".scene:has(#door-bay:hover) .backdrop", calm)


class SceneMotionTest(unittest.TestCase):
    """Canvas pull-in: keyed photo cutout, event-driven, calm-gated."""

    def test_canvas_layered_between_photo_and_zones(self):
        html = read_web("index.html")
        scene = html[html.index('id="homeScene"'):
                     html.index('id="view-bay"')]
        self.assertLess(scene.index('class="backdrop"'),
                        scene.index('id="sceneFx"'))
        self.assertLess(scene.index('id="sceneFx"'),
                        scene.index('class="tilegrid entrances"'))
        self.assertIn("pointer-events: none;", read_web("styles.css"))

    def test_key_and_drive_engine(self):
        app = read_web("app.js")
        mod = app[app.index("const SceneFx"):app.index("/* Camera-first")]
        for marker in ("move-car-shop.png", "move-car-alt.png",
                       "getImageData", "Uint8Array", "requestAnimationFrame",
                       "UX.Motion.driveMs", "calmMotion()",
                       "document.hidden", "visit", "replay"):
            self.assertIn(marker, mod, marker)

    def test_wiring_is_event_driven(self):
        app = read_web("app.js")
        self.assertIn("SceneFx.visit(which)", app)
        self.assertIn("(pointer: fine)", app)
        self.assertIn("SceneFx.replay()", app)
        self.assertIn("visibilitychange", app)
        self.assertIn("SceneFx.onCalmChange()", app)

    def test_drive_timing_is_ambient(self):
        ux = read_web("ux.js")
        self.assertIn("driveMs: 2800", ux)

    def test_motion_manifest_matches_assets(self):
        import json
        with open(os.path.join(ROOT, "eval_motion_results.json"),
                  encoding="utf-8") as fh:
            man = json.load(fh)
        self.assertEqual(man["image_count"], 2)
        self.assertEqual(man["failures"], {})
        for name in ("move-car-shop", "move-car-alt"):
            info = man["images"][name]
            self.assertTrue(os.path.isfile(
                os.path.join(ROOT, info["file"])), name)
            self.assertGreater(info["bytes"], 100000)


if __name__ == "__main__":
    unittest.main()
