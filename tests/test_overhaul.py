"""WO21 overhaul tests, phase by phase. Phase 1: real imagery.

The scene-illustration art set is rendered live, committed under
web/assets/, and wired into landing, doors, and setting bands. These
tests pin the manifest against the committed files, the doodle scenes
gone, the evidence frames untouched, and the honesty labels on the
new art. Later phases append their own classes below.
"""

import hashlib
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import test_eval_meta

LIVE_CALL_MARKERS = test_eval_meta.LiveCallSitesTest.MARKERS

RULES_PINNED = "1861d550c7680f5c0199906fda321f6c66108df2ee7d948639c683ed2b521a86"


def read_web(name):
    with open(os.path.join(ROOT, "web", name), encoding="utf-8") as fh:
        return fh.read()


def load_manifest():
    with open(os.path.join(ROOT, "eval_art_results.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


class OverhaulArtTest(unittest.TestCase):
    def test_manifest_matches_committed_files(self):
        manifest = load_manifest()
        self.assertEqual(manifest["model"], "muse-image-1.0")
        self.assertEqual(manifest["path"], "/responses")
        self.assertEqual(manifest["image_count"], 7)
        self.assertEqual(len(manifest["images"]), 7)
        total = 0
        for name, info in manifest["images"].items():
            for key in ("prompt", "file", "format", "bytes", "dims"):
                self.assertIn(key, info, name)
                self.assertTrue(info[key], name)
            path = os.path.join(ROOT, info["file"])
            self.assertTrue(os.path.isfile(path), info["file"])
            with open(path, "rb") as fh:
                raw = fh.read()
            self.assertEqual(len(raw), info["bytes"], name)
            self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n", name)
            total += info["bytes"]
        self.assertEqual(manifest["total_bytes"], total)
        self.assertEqual(manifest["live_calls_sent"],
                         sum(manifest["attempts"].values()))
        self.assertEqual(manifest["cost_estimate_usd"],
                         round(manifest["live_calls_sent"] * 0.01, 2))

    def test_scene_svgs_gone_evidence_stays(self):
        html = read_web("index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-yard"')]
        scene = home[home.index('<div class="scene"'):
                     home.index('id="btnHomePhoto"')]
        self.assertNotIn("<svg", scene)
        self.assertNotIn("sceneart", html)
        app = read_web("app.js")
        bands = app[app.index("var SETTING_BANDS"):
                    app.index("function renderSettingBand")]
        self.assertNotIn("<svg", bands)
        self.assertNotIn("sceneart", bands)
        css = read_web("styles.css")
        self.assertNotIn(".sceneart", css)
        for frame in ("frame1.svg", "frame2.svg", "frame3.svg",
                      "frame4.svg"):
            path = os.path.join(ROOT, "web", "demo", frame)
            self.assertTrue(os.path.isfile(path), frame)
        self.assertIn('gallery: "demo/frame1.svg"', app)
        self.assertIn(".emptybox img", css)

    def test_doors_use_committed_art(self):
        html = read_web("index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-yard"')]
        for door, asset, alt in (
                ("door-bay", "assets/door-shop.png", "Shop entrance"),
                ("door-yard", "assets/door-yard.png", "Yard gate"),
                ("door-driveway", "assets/door-garage.png",
                 "Home garage door")):
            self.assertIn('id="%s"' % door, home)
            self.assertIn('src="%s"' % asset, home)
            self.assertIn('alt="%s"' % alt, home)
            self.assertTrue(os.path.isfile(
                os.path.join(ROOT, "web", asset)), asset)

    def test_bands_use_committed_art(self):
        app = read_web("app.js")
        bands = app[app.index("var SETTING_BANDS"):
                    app.index("function renderSettingBand")]
        for asset in ("assets/band-shop.png", "assets/band-yard.png",
                      "assets/band-garage.png"):
            self.assertIn(asset, bands)
            self.assertTrue(os.path.isfile(
                os.path.join(ROOT, "web", asset)), asset)

    def test_art_labels_stay_honest(self):
        html = read_web("index.html")
        self.assertIn("Illustrated shop street", html)
        app = read_web("app.js")
        for label in ("Illustrated shop interior", "Illustrated yard lot",
                      "Illustrated home garage"):
            self.assertIn(label, app)

    def test_gen_script_has_no_other_live_path(self):
        with open(os.path.join(ROOT, "scripts", "gen_art.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        for marker in LIVE_CALL_MARKERS:
            self.assertNotIn(marker, src, marker)
        self.assertEqual(src.count("urlopen("), 0)

    def test_rules_json_byte_identical(self):
        with open(os.path.join(ROOT, "rules.json"), "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(),
                             RULES_PINNED)


def css_rule(css, selector):
    start = css.index(selector)
    open_brace = css.index("{", start)
    return css[open_brace + 1:css.index("}", open_brace)]


def yard_context():
    return {"view": "yard",
            "yard": {"verdicts": [
                {"label": "driver mirror", "grade": "B",
                 "reason": "thin comps", "price": 120}],
                "totals": {"A": {"plain_words": "Pull nothing."},
                           "B": {"plain_words": "Pull one part."}}}}


def inventory_context():
    return {"view": "inventory",
            "inventory": {
                "cars": ["1995 BMW M3"],
                "parts": [{"label": "spare ignition coil",
                           "car": "1995 BMW M3", "price": 200}],
                "notes": ["1995 BMW M3: No EWS on this unit, and it is "
                          "coveted amongst E30 owners."]}}


def bay_session():
    import bay
    case = {"case_id": "bay-1", "symptom": "creep",
            "codes": ["P0300"], "vehicle": {"category": "sedan"}}
    plan = bay.new_plan(case, [{"id": "t1", "title": "Coil swap"}])
    return {"bay": {"case": case, "plan": plan}}


class OverhaulCopilotTest(unittest.TestCase):
    def test_copilot_renders_as_button_plus_sheet(self):
        with open(os.path.join(ROOT, "web", "index.html"),
                  encoding="utf-8") as fh:
            html = fh.read()
        tag = html[html.index('id="copilotFab"') - 30:
                   html.index('id="copilotFab"') + 120]
        self.assertNotIn("primary", tag)
        self.assertIn("Copilot", tag)
        self.assertIn('id="panel"', html)
        self.assertIn("never guess", html)
        chips = html[html.index('id="chips"'):html.index('id="chatForm"')]
        self.assertEqual(chips.count('class="gtile"'), 3)
        css = read_web("styles.css")
        self.assertIn("display: none", css_rule(css, ".panel {"))
        self.assertIn("position: fixed", css_rule(css, ".panel {"))
        sheet = css_rule(css, ".panel.open {")
        self.assertIn("display: flex", sheet)
        self.assertIn("sheetup var(--t-sheet) var(--ease)", sheet)
        fab = css_rule(css, "#copilotFab {")
        self.assertIn("min-height: 48px", fab)

    def test_sheet_honors_reduced_motion(self):
        css = read_web("styles.css")
        calm = css[css.index("prefers-reduced-motion: reduce"):
                   css.index("prefers-reduced-motion: no-preference")]
        self.assertIn(".panel.open { animation: none; }", calm)

    def test_yard_question_grounded_offline(self):
        from server import Handler
        answer = Handler._local_chat_answer(
            None, None, "Why is the mirror a B?", yard_context())
        self.assertIn("driver mirror", answer)
        self.assertIn("B", answer)
        self.assertNotIn("lacking reliable data", answer)

    def test_m3_note_grounded_offline(self):
        from server import Handler
        answer = Handler._local_chat_answer(
            None, None, "Tell me about the M3 engine computer note",
            inventory_context())
        self.assertIn("EWS", answer)
        self.assertIn("E30", answer)

    def test_bay_question_grounded_offline(self):
        from server import Handler
        handler = Handler.__new__(Handler)
        answer = handler._local_chat_answer(
            bay_session(), "Rank the tests")
        self.assertIn("Next up", answer)
        self.assertIn("Coil swap", answer)

    def test_missing_data_names_filler(self):
        from server import Handler
        empty = Handler._local_chat_answer(
            None, None, "How much is the coil?", {})
        self.assertIn("load the demo inventory", empty)
        self.assertNotIn("lacking reliable data", empty)
        flow = Handler._local_chat_answer(None, None, "Why is it a B?", {})
        self.assertIn("run the flow", flow)
        self.assertNotIn("lacking reliable data", flow)

    def test_case_summary_merges_context(self):
        from server import Handler
        summary = Handler._case_summary(None, None, yard_context())
        self.assertIn("Open tab: yard", summary)
        self.assertIn("Yard results on screen", summary)
        self.assertIn("driver mirror is B", summary)


class OverhaulNavTest(unittest.TestCase):
    def test_back_bar_on_every_drilled_in_screen(self):
        html = read_web("index.html")
        for back, dest in (("backYard", "Home"),
                            ("backBay", "Home"),
                            ("backInv", "Home"),
                            ("backCompare", "Yard results")):
            tag = re.search(r'<button[^>]*id="%s"[^>]*>.*?</button>'
                            % back, html, re.S).group(0)
            self.assertIn("Back", tag, back)
            self.assertIn(dest, tag, back)
        css = read_web("styles.css")
        self.assertIn("min-height: 48px",
                      css_rule(css, ".backbar button.small {"))

    def test_bottom_bar_exactly_three_doors(self):
        html = read_web("index.html")
        nav = html[html.index('<nav id="bottomBar"'):
                   html.index("</nav>")]
        self.assertEqual(nav.count("<button"), 3)
        for bid, word in (("bb-bay", "Bay"), ("bb-yard", "Yard"),
                          ("bb-inv", "Driveway")):
            self.assertIn('id="%s"' % bid, nav, bid)
            self.assertIn(word, nav, bid)
        self.assertEqual(nav.count('aria-hidden="true"'), 3)
        self.assertNotIn("primary", nav)
        css = read_web("styles.css")
        self.assertIn("position: fixed", css_rule(css, ".bottombar {"))
        self.assertIn("min-height: 48px",
                      css_rule(css, ".bottombar button {"))
        self.assertNotIn("var(--accent",
                         css_rule(css, ".bottombar button.active {"))

    def test_bottom_bar_routes_like_doors(self):
        app = read_web("app.js")
        for bid, view in (("bb-bay", "bay"), ("bb-yard", "yard"),
                          ("bb-inv", "inventory")):
            self.assertIn('"%s"' % bid, app, bid)
            self.assertIn('showView("%s")' % view, app, view)
        self.assertIn('$("bb-bay").classList.toggle("active"', app)

    def test_settings_behind_gear_profile_inside(self):
        html = read_web("index.html")
        tag = re.search(r'<details[^>]*id="settings"[^>]*>',
                        html).group(0)
        self.assertIn("hidden", tag)
        header = html[html.index("<header"):html.index("</header>")]
        self.assertIn('id="navGear"', header)
        self.assertEqual(header.count("\u2699"), 1)
        self.assertNotIn(">Settings", header)
        self.assertNotIn("profile", header.lower())
        app = read_web("app.js")
        self.assertIn("panel.hidden = false", app)
        self.assertIn('$("settings").hidden = true', app)
        fn = app[app.index("function renderSettings()"):]
        fn = fn[:fn.index("\n}\n")]
        self.assertIn('const box = $("settingsBody");', fn)
        self.assertIn('"Profile"', fn)

    def test_purpose_line_on_every_screen(self):
        html = read_web("index.html")
        for purpose in (
                "Photo in, pull-it-or-leave-it verdict and money out.",
                "Answer the tests and the plan ranks the cause and prices the job.",
                "Your cars and parts, organized and searchable.",
                "Three doors: fix a car, strip a parts car, or look after your own.",
                "Two engines grade the same case side by side."):
            self.assertIn(purpose, html, purpose)
        app = read_web("app.js")
        self.assertIn("Your profile, credentials, and demo switches.",
                      app)

    def test_tour_keeps_no_back(self):
        app = read_web("app.js")
        bar = app[app.index("function tourBar"):
                  app.index("function placeTourBar")]
        self.assertNotIn('"Back"', bar)
        self.assertIn('"Next"', bar)
        self.assertIn('"Exit tour"', bar)
        beats = re.findall(r'\{ id: "(\w+)"',
                           app[app.index("const TOUR_BEATS"):
                               app.index("let tourState")])
        self.assertEqual(len(beats), 10)


if __name__ == "__main__":
    unittest.main()
