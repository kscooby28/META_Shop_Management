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


def load_seed():
    with open(os.path.join(ROOT, "demo_cache", "inv_seed.demo.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


class OverhaulSeedTest(unittest.TestCase):
    def test_every_car_has_multiple_parts(self):
        seed = load_seed()
        by_car = {}
        for part in seed["parts"]:
            by_car.setdefault(part["carId"], []).append(part["id"])
        for car in seed["cars"]:
            got = by_car.get(car["id"], [])
            self.assertGreaterEqual(len(got), 2,
                                    "single-part car: %s" % car["label"])

    def test_seed_values_comps_or_unknown(self):
        seed = load_seed()
        board = seed["partComps"]
        for part in seed["parts"]:
            if part["value"] is None:
                self.assertEqual(part["valueSource"], "", part["id"])
            else:
                self.assertIn(part["label"], board, part["id"])
                self.assertEqual(part["value"],
                                 board[part["label"]]["value"], part["id"])

    def test_m3_knowledge_note_verbatim(self):
        seed = load_seed()
        notes = [n for n in seed["knowledge"] if n["part"] == "engine computer"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["reason"],
                         "No EWS on this unit, and it is coveted amongst E30 owners.")
        self.assertEqual(notes[0]["value"], 200)

    def test_filter_controls_exist_and_wire(self):
        html = read_web("index.html")
        self.assertIn('id="invFilterCar"', html)
        self.assertIn('id="invFilterPart"', html)
        app = read_web("app.js")
        self.assertIn('$("invFilterCar").addEventListener("change", renderInvParts)', app)
        self.assertIn('$("invFilterPart").addEventListener("input", renderInvParts)', app)
        fn = app[app.index("function renderInvParts"):
                 app.index("function renderInvTotals")]
        self.assertIn('invFilterCar', fn)
        self.assertIn('invFilterPart', fn)
        self.assertIn('No parts match this filter.', fn)

    def test_part_rows_title_plus_one_field(self):
        app = read_web("app.js")
        fn = app[app.index("function renderInvParts"):
                 app.index("function renderInvTotals")]
        row = fn[fn.index("insertAdjacentHTML"):fn.index("rowmore")]
        self.assertIn("<strong>", row)
        self.assertIn("value unknown", row)
        self.assertNotIn("relbadge", row)
        details = fn[fn.index("rowmore"):]
        self.assertIn("relbadge", details)

    def test_notes_render_text_only(self):
        app = read_web("app.js")
        fn = app[app.index("function renderInvKnow"):
                 app.index("function renderInvParts")]
        self.assertNotIn("<img", fn)

    def test_totals_name_unknowns(self):
        inv = read_web("inventory.js")
        self.assertIn("Unknown and left out: ", inv)


class OverhaulCopyTest(unittest.TestCase):
    BANNED = ("Gulf Coast", "Gulf-Coast", "Ocean Springs", "Mississippi",
              "Built for a Gulf Coast shop")

    def test_no_region_naming_in_web(self):
        web = os.path.join(ROOT, "web")
        for base, dirs, names in os.walk(web):
            dirs[:] = [d for d in dirs if d != "assets"]
            for name in names:
                if not name.endswith((".html", ".js", ".css")):
                    continue
                with open(os.path.join(base, name),
                          encoding="utf-8") as fh:
                    text = fh.read()
                for banned in self.BANNED:
                    self.assertNotIn(banned, text, name)

    def test_readme_region_line_fixed(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("Gulf Coast", text)
        self.assertIn("no region naming", text)

    def test_desktop_capture_labels_present(self):
        app = read_web("app.js")
        for label in ("Choose a photo", "Choose a VIN photo",
                      "Choose a clear photo of the whole car",
                      "On your phone this opens the camera; "
                      "here, choose a photo file",
                      "File picker here"):
            self.assertIn(label, app)
        for phone in ("Take a photo", "Take a VIN photo",
                      "Get the whole car in the frame.", "Camera first"):
            self.assertIn(phone, app)

    def test_desktop_gate_is_positive_media_test(self):
        app = read_web("app.js")
        self.assertIn("(hover: hover) and (pointer: fine)", app)
        self.assertIn("function desktopCapture()", app)
        self.assertIn("function labelCaptureForDevice()", app)
        self.assertLess(app.index("wireCameras();"),
                        app.index("labelCaptureForDevice();"))

    def test_camera_plumbing_untouched(self):
        html = read_web("index.html")
        self.assertEqual(html.count('capture="environment"'), 6)
        app = read_web("app.js")
        for cam in ("fileCamera", "homeHeroCamera", "bayVinCamera",
                    "invCarPhotoCamera", "invCarVinCamera",
                    "invPartPhotoCamera"):
            self.assertIn('twinCamera("%s"' % cam, app)
        self.assertIn("openConfirm(camId, files)", app)

    def test_painted_guides_branch_on_desktop(self):
        app = read_web("app.js")
        fn = app[app.index("function paintShotGuide"):
                 app.index("function renderConfirmStrip")]
        self.assertIn("DESKTOP_GUIDES[shot]", fn)
        self.assertIn("desktopCapture()", fn)


class OverhaulVerdictTest(unittest.TestCase):
    HOW = ("The verdict engine grades every part by its sold prices and "
           "demand \u2014 the rule it used is shown on each card.")

    def test_rule_reason_on_card_face(self):
        app = read_web("app.js")
        fn = app[app.index("function renderVerdicts"):
                 app.index("function renderTotals")]
        face = fn[:fn.index("<details")]
        self.assertIn("whyline", face)
        self.assertIn("v.rule_name", face)
        self.assertIn("v.rule_explain", face)
        self.assertIn("Rule:</strong>", face)

    def test_money_reason_on_card_face(self):
        app = read_web("app.js")
        fn = app[app.index("function renderVerdicts"):
                 app.index("function renderTotals")]
        face = fn[:fn.index("<details")]
        self.assertIn("moneyRow(v)", face)
        self.assertIn("Money:</strong>", face)
        self.assertIn("money grade unknown", face)
        self.assertIn('<span class="missing">money grade unknown</span>',
                      face)

    def test_details_evidence_unchanged(self):
        app = read_web("app.js")
        fn = app[app.index("function renderVerdicts"):
                 app.index("function renderTotals")]
        details = fn[fn.index("<details"):]
        self.assertIn("Evidence and inputs", details)
        self.assertIn('<div class="rule">', details)
        self.assertIn("v.verdict_means", details)
        self.assertIn("Money grade", details)

    def test_how_note_on_yard(self):
        html = read_web("index.html")
        sec = html[html.index('<section id="sec-verdicts">'):
                  html.index('<div id="verdicts">')]
        self.assertIn(self.HOW, sec)

    def test_whyline_tokens_only(self):
        css = read_web("styles.css")
        rule = css[css.index(".verdict .whyline"):
                   css.index("}", css.index(".verdict .whyline"))]
        self.assertIn("var(--text-body)", rule)
        self.assertNotIn("#", rule)
        self.assertNotIn("accent", rule)

    def test_rules_byte_identical(self):
        with open(os.path.join(ROOT, "rules.json"), "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(),
                             RULES_PINNED)


class OverhaulGraphicalFixesTest(unittest.TestCase):
    """WO20 graphical-build repairs: each fix below pins its guard."""

    def test_drawer_shadow_replaced_by_solid_border(self):
        css = read_web("styles.css")
        self.assertNotIn("-4px 0 16px", css)
        mobile = css[css.index("@media (max-width: 900px)"):
                     css.index("@media (prefers-reduced-motion: reduce)")]
        panel = mobile[mobile.index(".panel {"):mobile.index("#panelToggle")]
        self.assertNotIn("box-shadow", panel)
        self.assertIn("border-left: 2px solid var(--line);", panel)
        for value in re.findall(r"box-shadow:\s*([^;]+);",
                                re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
            self.assertEqual(value.strip(),
                             "inset 0 1px 0 var(--line)", value)

    def test_small_buttons_keep_shop_targets(self):
        css = read_web("styles.css")
        base = re.search(r"^button\.small \{([^}]*)\}", css,
                         re.M).group(1)
        self.assertIn("min-height: 44px", base)
        self.assertIn("min-height: 48px",
                      css_rule(css, ".backbar button.small {"))

    def test_motion_is_tokens_transform_opacity_only(self):
        plain = re.sub(r"/\*.*?\*/", "", read_web("styles.css"), flags=re.S)
        lits = set()
        for value in re.findall(r"(?:transition|animation):\s*([^;]+);",
                                plain):
            bare = re.sub(r"var\(--[\w-]+\)", "", value)
            words = set(re.findall(r"[a-z][\w-]*", bare))
            self.assertNotIn("ease", words, value)
            self.assertNotIn("background-color", words, value)
            self.assertNotIn("border-color", words, value)
            lits.update(re.findall(r"\d+\.?\d*m?s\b", value))
        self.assertEqual(lits, {"900ms"})
        for value in re.findall(r"transition:\s*([^;]+);", plain):
            for prop in re.findall(r"[a-z-]+(?=\s+var\(--t-)", value):
                self.assertIn(prop, ("transform", "opacity"), value)
        self.assertIn(".flash { animation: fadein var(--t-door) var(--ease); }",
                      plain)

    def test_reduced_motion_cuts_flash(self):
        css = read_web("styles.css")
        calm = css[css.index("prefers-reduced-motion: reduce"):
                   css.index("prefers-reduced-motion: no-preference")]
        self.assertIn(".flash { animation: none; }", calm)
        app = read_web("app.js")
        flash = app[app.index("function flash(el)"):
                    app.index("function stageIn")]
        self.assertIn("calmMotion()) return;", flash)

    def test_overlay_grades_come_from_tokens(self):
        app = read_web("app.js")
        self.assertIn("function overlayColor(grade)", app)
        self.assertIn('getPropertyValue("--grade-"', app)
        self.assertIn("const color = overlayColor(grade);", app)
        for hard in ("#9a6206", "#1e6b3a", "#a83a32"):
            self.assertNotIn(hard, app, hard)

    def test_inventory_car_filter_has_sheet_face(self):
        app = read_web("app.js")
        self.assertIn('sheetPicker($("invFilterCar"), "Filter by car")',
                      app)
        html = read_web("index.html")
        self.assertIn('id="invFilterCar"', html)
        fn = app[app.index("function renderInvParts"):
                 app.index("function renderInvTotals")]
        self.assertIn("syncPickers();", fn)

    def test_header_buttons_show_icon_plus_word(self):
        html = read_web("index.html")
        header = html[html.index("<header"):html.index("</header>")]
        gear = re.search(r'<button[^>]*id="navGear"[^>]*>(.*?)</button>',
                         header, re.S).group(1)
        self.assertIn("\u2699", gear)
        self.assertIn("Settings", gear)
        sun = re.search(r'<button[^>]*id="navSun"[^>]*>(.*?)</button>',
                        header, re.S).group(1)
        self.assertIn("\u2600", sun)
        self.assertIn("Sun", sun)
        app = read_web("app.js")
        self.assertIn("\u2191 Move up", app)
        self.assertIn("\u2193 Move down", app)

    def test_profile_cards_show_selected_state(self):
        app = read_web("app.js")
        self.assertIn("function paintSetupChoice(mode)", app)
        self.assertIn('shop.setAttribute("aria-pressed"', app)
        self.assertIn('fan.setAttribute("aria-pressed"', app)
        self.assertIn('paintSetupChoice("");', app)
        self.assertIn("paintSetupChoice(mode);", app)
        self.assertIn("paintSetupChoice((Profile.loadProfile(localStorage)"
                      " || {}).mode);", app)

    def test_hero_settles_without_zoom(self):
        app = read_web("app.js")
        expand = app[app.index("function heroExpand"):
                     app.index("function yardPhoto")]
        self.assertIn("scale(", expand)
        self.assertIn("Math.min(1.15, Math.max(1.05", expand)
        self.assertNotIn("Math.min(3", app)

    def test_empty_actions_are_tiles(self):
        app = read_web("app.js")
        empty = app[app.index("function emptyInto"):
                    app.index("function demoBadge")]
        self.assertIn('btn.className = "gtile";', empty)
        self.assertIn('class="ticon"', empty)
        self.assertIn('class="tword"', empty)
        self.assertIn("esc(e.action)", empty)
        trail = app[app.index("function renderBayTrail"):
                    app.index("function renderBayParts")]
        self.assertIn('btn.className = "gtile";', trail)
        self.assertIn("Review parts</span>", trail)

    def test_grade_cards_carry_part_photo(self):
        app = read_web("app.js")
        fn = app[app.index("function renderVerdicts"):
                 app.index("function renderTotals")]
        self.assertIn("Gallery.partThumb(ghpart)", fn)
        self.assertIn("frameSrc(gvthumb.frame)", fn)
        self.assertIn('class="timg"', fn)
        self.assertIn("gradeImg +", fn)

    def test_gate_composes_its_price(self):
        html = read_web("index.html")
        tag = re.search(r'<div[^>]*id="listingPrice"[^>]*>',
                        html).group(0)
        self.assertIn("big-money", tag)
        app = read_web("app.js")
        self.assertIn("function renderGatePrice(partId, from)", app)
        self.assertIn('renderGatePrice(pid, "yard");', app)
        self.assertIn('renderGatePrice(part.id, "inv");', app)
        self.assertIn("price unknown", app)
        self.assertIn('$("listingPrice").innerHTML = "";', app)

    def test_receipts_reveal_in_stages(self):
        app = read_web("app.js")
        self.assertIn("function stageIn(el)", app)
        self.assertIn("function stageReceipt(box, html)", app)
        self.assertIn('stageReceipt($("receipt"),', app)
        self.assertIn("data-on", app)
        fn = app[app.index("function renderInvKnow"):
                 app.index("function renderInvParts")]
        self.assertIn("stageIn(box.firstElementChild);", fn)

    def test_yard_keeps_one_primary(self):
        html = read_web("index.html")
        yard = html[html.index('id="view-yard"'):html.index('id="view-bay"')]
        self.assertEqual(yard.count('class="primary'), 1)
        run = re.search(r'<button[^>]*id="btnRunAll"[^>]*>',
                        html).group(0)
        self.assertNotIn("primary", run)
        gate = re.search(r'<button[^>]*id="btnApprove"[^>]*>',
                         html).group(0)
        self.assertIn("primary approve", gate)

    def test_tour_progression_not_primary(self):
        app = read_web("app.js")
        bar = app[app.index("function tourBar"):
                  app.index("function placeTourBar")]
        self.assertIn('next.className = "small";', bar)
        self.assertNotIn("primary", bar)
        self.assertIn('"Next"', bar)
        self.assertIn('"Finish"', bar)
        self.assertIn('"Exit tour"', bar)

    def test_landing_art_preloads(self):
        html = read_web("index.html")
        self.assertIn('<link rel="preload" href="assets/landing.png"'
                      ' as="image">', html)

    def test_no_new_art_beyond_manifest(self):
        assets = sorted(os.listdir(os.path.join(ROOT, "web", "assets")))
        self.assertEqual(assets, ["band-garage.png", "band-shop.png",
                                 "band-yard.png", "door-garage.png",
                                 "door-shop.png", "door-yard.png",
                                 "landing.png"])

    def test_grade_text_contrast_reproved(self):
        css = read_web("styles.css")
        root = css.partition(":root")[2].partition("}")[0]
        tok = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", root))

        def lum(hexcode):
            rgb = [int(hexcode[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928
                   else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def ratio(fore, back):
            return ((max(lum(fore), lum(back)) + 0.05)
                    / (min(lum(fore), lum(back)) + 0.05))

        for grade in ("grade-a", "grade-b", "grade-c"):
            self.assertGreaterEqual(ratio(tok[grade], tok["surface"]),
                                    4.5, grade)


if __name__ == "__main__":
    unittest.main()
