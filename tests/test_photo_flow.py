"""DIY photo-flow tests (Corey order): photo to analyzing to autofill to
four demo panels to tour entry, all under DIY Garage.

Static pins against web/app.js plus the canonical demo seed
demo_cache/photo_result.demo.json. The live identify path stays intact
and unproven here; demo mode is the verified path.
"""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_app():
    with open(os.path.join(ROOT, "web", "app.js"), encoding="utf-8") as fh:
        return fh.read()


def load_photo_seed():
    with open(os.path.join(ROOT, "demo_cache", "photo_result.demo.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def load_inv_seed():
    with open(os.path.join(ROOT, "demo_cache", "inv_seed.demo.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


class PhotoResultScreenTest(unittest.TestCase):
    def test_screen_builds_under_diy_register(self):
        app = read_app()
        fn = app[app.index("function buildPhotoResultScreen"):app.index("function showPhotoAnalyzing")]
        self.assertIn('document.querySelector("#sec-icars details")', fn)
        for marker in ('box.id = "invPhotoResult"', 'img.id = "invPhotoImg"',
                       'work.id = "invPhotoAnalyzing"', 'bar.id = "invPhotoBar"',
                       'steps.id = "invPhotoSteps"', 'fields.id = "invPhotoFields"',
                       '"photoPanelEstimated"', '"photoPanelNearby"',
                       '"photoPanelNetwork"', '"photoPanelShops"',
                       '"Photo result"', '"Analyzing…"'):
            self.assertIn(marker, fn, marker)

    def test_analyzing_is_visible_progress(self):
        app = read_app()
        fn = app[app.index("function showPhotoAnalyzing"):app.index("function finishPhotoResult")]
        for marker in ("buildPhotoResultScreen()", '"Analyzing…"',
                       "invPhotoBar", "invPhotoSteps", '"Reading photo…"',
                       '"Identifying…"', '"Matching parts…"',
                       'bar.style.width = Math.round((tick / items.length) * 100) + "%";',
                       "scrollSoon(box)"):
            self.assertIn(marker, fn, marker)

    def test_result_screen_uses_defined_classes_only(self):
        app = read_app()
        fn = app[app.index("function buildPhotoResultScreen"):app.index("function showPhotoAnalyzing")]
        for marker in ('hint.className = "hint"', 'prog.className = "progress"',
                       'honest.className = "hint"'):
            self.assertIn(marker, fn, marker)


class PhotoChainTest(unittest.TestCase):
    def test_flow_order_is_photo_analyzing_autofill_panels(self):
        app = read_app()
        fn = app[app.index("async function identifyInvCarPhotoResult"):app.index("function renderNetworkFeed")]
        first = fn.index("showPhotoAnalyzing(photo)")
        last = fn.index("finishPhotoResult(photo")
        self.assertIn("invIdentifyFn()", fn[first:last])
        self.assertIn("downscale(file)", fn)

    def test_entries_use_the_result_flow(self):
        app = read_app()
        self.assertIn("guard(identifyInvCarPhotoResult,", app)
        self.assertIn("await identifyInvCarPhotoResult();", app)
        self.assertIn("invIdentifyFn = identifyInvCarPhoto;", app)

    def test_finish_renders_panels_then_tour_entry(self):
        app = read_app()
        fn = app[app.index("function finishPhotoResult"):app.index("function renderPhotoPanels")]
        self.assertLess(fn.index("renderPhotoPanels()"), fn.index("ensurePhotoTourEntry()"))
        for marker in ('$("invPhotoBar").style.width = "100%"',
                       '"Analyzing done"', 'Auto-filled from photo'):
            self.assertIn(marker, fn, marker)


class PhotoAutofillTest(unittest.TestCase):
    def test_only_known_fields_fill_never_guessed(self):
        app = read_app()
        fn = app[app.index("async function identifyInvCarPhoto("):app.index("async function identifyInvCarPhotoStaged")]
        self.assertEqual(fn.count('!== "unknown"'), 4)
        self.assertIn("return car;", fn)
        self.assertIn('api("/api/inv/identify", { photo, demo: invSeeded })', fn)

    def test_unknowns_rendered_not_invented(self):
        app = read_app()
        fn = app[app.index("function finishPhotoResult"):app.index("function renderPhotoPanels")]
        self.assertIn('? "unknown" : v', fn)
        for field in ("c.year", "c.make", "c.model", "c.trim"):
            self.assertIn(field, fn, field)


class PhotoPanelsTest(unittest.TestCase):
    def test_all_four_panels_render_from_demo_seed(self):
        app = read_app()
        fn = app[app.index("function renderPhotoPanels"):app.index("function ensurePhotoTourEntry")]
        for marker in ("photoPanelEstimated", "photoPanelNearby",
                       "photoPanelNetwork", "photoPanelShops",
                       "PHOTO_RESULT_DEMO", "demoBadge()",
                       'price unknown', '"Estimated parts for this car"',
                       '"Local parts near you"',
                       '"Other cars in the network like yours"',
                       '"Shops willing to work on it"'):
            self.assertIn(marker, fn, marker)

    def test_seed_is_demo_marked_and_mirrored(self):
        seed = load_photo_seed()
        for key in ("estimatedParts", "nearbyParts", "networkCars", "willingShops"):
            self.assertIn(key, seed)
            self.assertTrue(seed[key], key)
        self.assertIn("DEMO", seed["source"])
        app = read_app()
        self.assertIn("const PHOTO_RESULT_DEMO = {", app)
        for label in ("driver headlight", "Demo Auto Parts — Northside (DEMO)",
                      "2004 BMW 325i parts car (DEMO)",
                      "Demo Shop — Northside (DEMO)"):
            self.assertIn(label, json.dumps(seed, ensure_ascii=False), label)
            self.assertIn(label, app, label)

    def test_prices_match_seed_comps_or_unknown(self):
        seed = load_photo_seed()
        board = load_inv_seed()["partComps"]
        seen = 0
        for part in seed["estimatedParts"] + seed["nearbyParts"]:
            if part["price"] is None:
                self.assertEqual(part["source"], "")
            else:
                self.assertIn(part["label"], board, part["label"])
                self.assertEqual(part["price"], board[part["label"]]["value"])
                seen += 1
        self.assertGreater(seen, 0)

    def test_no_real_names_addresses_or_contacts(self):
        blob = json.dumps(load_photo_seed())
        self.assertNotIn("@", blob)
        self.assertNotIn("http", blob)
        self.assertIsNone(re.search(r"\d{3}[-. ]\d{3}[-. ]\d{4}", blob))
        seed = load_photo_seed()
        for part in seed["nearbyParts"]:
            self.assertIn("(DEMO)", part["where"])
            self.assertIn("(DEMO)", part["distance"])
        for shop in seed["willingShops"]:
            self.assertIn("(DEMO)", shop["name"])
            self.assertIn("(DEMO)", shop["note"])
        for car in seed["networkCars"]:
            self.assertIn("(DEMO)", car["label"])

    def test_network_honesty_line_present(self):
        app = read_app()
        fn = app[app.index("function renderPhotoPanels"):app.index("function ensurePhotoTourEntry")]
        self.assertIn("nothing is posted anywhere", fn)
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        feed = html[html.index('id="networkFeed"'):html.index('id="sec-rules"')]
        self.assertIn("nothing is posted anywhere", feed)


class PhotoTourEntryTest(unittest.TestCase):
    def test_result_screen_offers_the_tour(self):
        app = read_app()
        fn = app[app.index("function ensurePhotoTourEntry"):app.index("function renderNetworkFeed")]
        self.assertIn('tour.id = "btnPhotoTour";', fn)
        self.assertIn('tour.className = "primary gtile";', fn)
        self.assertIn("Take the tour", fn)
        self.assertIn('tour.addEventListener("click", () => startTour());', fn)
        self.assertEqual(fn.count("startTour()"), 1)

    def test_tour_never_auto_starts(self):
        app = read_app()
        for start, end in (("function showPhotoAnalyzing", "function finishPhotoResult"),
                           ("function finishPhotoResult", "function renderPhotoPanels"),
                           ("function renderPhotoPanels", "function ensurePhotoTourEntry"),
                           ("async function identifyInvCarPhotoResult", "function renderNetworkFeed")):
            fn = app[app.index(start):app.index(end)]
            self.assertNotIn("startTour()", fn, start)


if __name__ == "__main__":
    unittest.main()
