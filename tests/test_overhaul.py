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
        home = html[html.index('id="view-home"'):html.index('id="view-bay"')]
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
        self.assertIn('gallery: "assets/case-side.png"', app)
        self.assertIn(".emptybox img", css)

    def test_doors_use_committed_art(self):
        html = read_web("index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-bay"')]
        for door, asset, alt in (
                ("door-bay", "assets/door-shop.png", "Shop entrance"),
                ("door-garage", "assets/door-garage.png",
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
        for asset in ("assets/band-shop.png", "assets/band-garage.png"):
            self.assertIn(asset, bands)
            self.assertTrue(os.path.isfile(
                os.path.join(ROOT, "web", asset)), asset)

    def test_art_labels_stay_honest(self):
        html = read_web("index.html")
        self.assertIn("Illustrated street in daylight", html)
        app = read_web("app.js")
        for label in ("Illustrated shop interior",
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
        for back, dest in (("backBay", "Home"),
                            ("backInv", "Home"),
                            ("backCompare", "DIY Garage results")):
            tag = re.search(r'<button[^>]*id="%s"[^>]*>.*?</button>'
                            % back, html, re.S).group(0)
            self.assertIn("Back", tag, back)
            self.assertIn(dest, tag, back)
        css = read_web("styles.css")
        self.assertIn("min-height: 48px",
                      css_rule(css, ".backbar button.small {"))

    def test_bottom_bar_is_home_plus_side(self):
        html = read_web("index.html")
        nav = html[html.index('<nav id="bottomBar"'):
                   html.index("</nav>")]
        self.assertEqual(nav.count("<button"), 2)
        self.assertIn('id="bottomHome"', nav)
        self.assertIn("Home", nav)
        self.assertIn('id="sideChip"', nav)
        self.assertIn("Your side", nav)
        self.assertNotIn("bb-bay", nav)
        self.assertNotIn("bb-inv", nav)
        self.assertEqual(nav.count('aria-hidden="true"'), 2)
        self.assertNotIn("primary", nav)
        css = read_web("styles.css")
        self.assertIn("position: fixed", css_rule(css, ".bottombar {"))
        self.assertIn("min-height: 48px",
                      css_rule(css, ".bottombar button {"))
        self.assertNotIn("var(--accent",
                         css_rule(css, ".bottombar button.active {"))

    def test_side_chip_shows_identity(self):
        app = read_web("app.js")
        self.assertIn("function paintSideChip()", app)
        self.assertIn("function paintSideBadges()", app)
        self.assertIn("Your side: ", app)
        self.assertIn('"\\u2605 Your side"', app)
        self.assertIn('id = "profileCard";', app)
        self.assertNotIn("bb-bay", app)
        self.assertNotIn("bb-inv", app)

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
                "Two doors: run the repair bench, or look after your own cars and parts.",
                "Answer the tests and the plan ranks the cause and prices the job.",
                "Your cars and parts, organized and searchable.",
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
        self.assertEqual(len(beats), 8)


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
        self.assertNotIn("Settings", gear)
        home = re.search(r'<button[^>]*id="navHome"[^>]*>(.*?)</button>',
                         header, re.S).group(1)
        self.assertIn("\u2302", home)
        self.assertIn("Home", home)
        self.assertIn('<img class="navthumb"', home)
        self.assertNotIn("navSun", header)
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
        self.assertIn("PART_ART[v.part_id]", fn)
        self.assertIn("PART_LABEL_ART[glabel.toLowerCase()]", fn)
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

    def test_garage_keeps_one_primary(self):
        html = read_web("index.html")
        garage = html[html.index('id="view-inventory"'):html.index('id="view-compare"')]
        self.assertEqual(garage.count('class="primary'), 1)
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
        self.assertIn('<link rel="preload" href="assets/landing-2door.png"'
                      ' as="image">', html)

    def test_no_new_art_beyond_manifest(self):
        # The 7 Phase-1 manifest files plus the 2-door order's landing art
        # plus the 25 case-art set files (eval_caseart_results.json),
        # plus the audio/ dir holding the 8 tour narration mp3s
        # (eval_voice_results.json). eval JSONs stay byte-identical history.
        assets = sorted(os.listdir(os.path.join(ROOT, "web", "assets")))
        with open(os.path.join(ROOT, "eval_voice_results.json"),
                  encoding="utf-8") as fh:
            voice = sorted("tour-%s.mp3" % f["beat"]
                           for f in json.load(fh)["files"])
        self.assertEqual(sorted(os.listdir(os.path.join(ROOT, "web", "assets",
                                                         "audio"))), voice)
        self.assertEqual(assets, ["audio", "band-garage.png", "band-shop.png",
                                 "band-yard.png", "bay-engine.png",
                                 "case-bench.png", "case-front.png",
                                 "case-rear.png", "case-side.png",
                                 "door-garage.png", "door-shop.png",
                                 "door-yard.png", "empty-garage.png",
                                 "empty-shelf.png", "head-compare.png",
                                 "head-grade.png", "head-notes.png",
                                 "head-parts.png", "head-plan.png",
                                 "head-trail.png", "head-wrench.png",
                                 "landing-2door.png", "landing.png",
                                 "part-bumper.png", "part-coil.png",
                                 "part-diff.png", "part-ecu.png",
                                 "part-handle.png", "part-headlight.png",
                                 "part-m3bumper.png", "part-mirror.png",
                                 "part-taillight.png", "part-trunklid.png",
                                 "part-wheel.png"])

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


class CaseArtTest(unittest.TestCase):
    """Case-art set: generated photos wired into identifiers only.

    Measurement views (harvest viewer, strip, listing cutout preview)
    keep the real frames so boxes never lie; everything else that
    showed a sample drawing now shows the matching case-art photo.
    """

    def test_manifest_matches_committed_files(self):
        with open(os.path.join(ROOT, "eval_caseart_results.json"),
                  encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["model"], "muse-image-1.0")
        self.assertEqual(manifest["path"], "/responses")
        self.assertEqual(manifest["image_count"], 25)
        self.assertEqual(len(manifest["images"]), 25)
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

    def test_display_maps_resolve_to_files(self):
        app = read_web("app.js")
        for block, end in (("const EMPTY_ART", "const PART_ART"),
                           ("const PART_ART", "const PART_LABEL_ART"),
                           ("const PART_LABEL_ART",
                            "function partPhotoImg")):
            chunk = app[app.index(block):app.index(end)]
            self.assertNotIn("demo/frame", chunk, block)
            for asset in re.findall(r'"(assets/[^"]+)"', chunk):
                self.assertTrue(os.path.isfile(
                    os.path.join(ROOT, "web", asset)), asset)

    def test_yard_part_ids_all_have_art(self):
        app = read_web("app.js")
        chunk = app[app.index("const PART_ART"):
                    app.index("const PART_LABEL_ART")]
        with open(os.path.join(ROOT, "demo_cache", "harvest.demo.json"),
                  encoding="utf-8") as fh:
            parts = json.load(fh)["parts"]
        self.assertTrue(parts)
        for part in parts:
            self.assertIn(part["id"] + ":", chunk, part["id"])

    def test_seed_labels_all_have_art(self):
        app = read_web("app.js")
        chunk = app[app.index("const PART_LABEL_ART"):
                    app.index("function partPhotoImg")]
        with open(os.path.join(ROOT, "demo_cache", "inv_seed.demo.json"),
                  encoding="utf-8") as fh:
            seed = json.load(fh)
        labels = {p["label"].lower() for p in seed["parts"]}
        labels.update(n["part"].lower() for n in seed["knowledge"])
        self.assertTrue(labels)
        for label in labels:
            self.assertIn('"%s"' % label, chunk, label)

    def test_measurement_views_keep_real_frames(self):
        app = read_web("app.js")
        viewer = app[app.index("function renderViewer"):
                     app.index("function renderPartList")]
        self.assertIn("frameSrc(n)", viewer)
        strip = app[app.index("function renderStrip"):
                    app.index("function renderViewer")]
        self.assertIn("frameSrc(n)", strip)
        draft = app[app.index("async function runDraft"):
                    app.index("async function runApprove")]
        self.assertIn("frameSrc(cut.frame)", draft)

    def test_demo_tile_uses_case_art(self):
        html = read_web("index.html")
        btn = re.search(r'<button[^>]*id="btnDemo"[^>]*>(.*?)</button>',
                        html, re.S).group(0)
        self.assertIn('src="assets/case-front.png"', btn)
        self.assertIn("Labeled demo frames", btn)

    def test_studio_live_image_wins(self):
        app = read_web("app.js")
        fn = app[app.index("function renderStudio"):
                 app.index("async function runDraft")]
        self.assertIn('studio.kind !== "image"', fn)
        self.assertIn("Source: demo case art.", fn)
        self.assertIn("renderStudio(res.studio, res.mode, pid);", app)
        self.assertIn(
            "renderStudio(res.studio, res.mode, part.id, part.label);", app)


class PageTest(unittest.TestCase):
    """Paged views: graphical index + one page at a time, flows untouched."""

    def test_pages_cover_every_section(self):
        html = read_web("index.html")
        app = read_web("app.js")
        chunk = app[app.index("const VIEW_PAGES"):
                    app.index("function pageForSection")]
        bay = html[html.index('id="view-bay"'):
                   html.index('id="view-inventory"')]
        inv = html[html.index('id="view-inventory"'):
                   html.index('id="view-compare"')]
        covered = set(re.findall(r'secs: \[([^\]]+)\]', chunk))
        self.assertEqual(len(covered), 14)
        for block in (bay, inv):
            for sec in re.findall(r'<section id="([\w\-]+)"', block):
                self.assertIn('"%s"' % sec, chunk, sec)
        for asset in re.findall(r'art: "(assets/[^"]+)"', chunk):
            self.assertTrue(os.path.isfile(
                os.path.join(ROOT, "web", asset)), asset)

    def test_pager_keeps_one_primary(self):
        app = read_web("app.js")
        fn = app[app.index("function renderPager"):
                 app.index("function activatePage")]
        self.assertIn('querySelector(".primary")', fn)
        self.assertIn("hasPrimary", fn)
        self.assertIn('next.className = hasPrimary ? "small" : "primary";',
                      fn)

    def test_scrolls_route_through_pages(self):
        app = read_web("app.js")
        self.assertNotIn('").scrollIntoView(', app)
        soon = app[app.index("function scrollSoon"):
                   app.index("function showView")]
        self.assertIn("revealSection(ps.id)", soon)
        view = app[app.index("function showView"):
                   app.index("const VIEW_PAGES")]
        self.assertIn("activatePage(which, 0)", view)
        self.assertIn("function goSection(idOrEl)", app)
        self.assertIn("function revealSection(secId)", app)

    def test_index_cards_are_graphical(self):
        app = read_web("app.js")
        idx = app[app.index("function refreshIndex"):
                  app.index("function buildIndex")]
        self.assertIn('"gtile idxcard"', idx)
        self.assertIn('"timg"', idx)
        self.assertIn("pageStatus(view, i + 1)", idx)
        self.assertIn("img.src = p.art;", idx)

    def test_pager_honors_reduced_motion(self):
        app = read_web("app.js")
        act = app[app.index("function activatePage"):
                  app.index("function revealSection")]
        self.assertIn("calmMotion()", act)
        go = app[app.index("function goSection"):
                 app.index("/* Camera-first intake (WO17)")]
        self.assertIn("calmMotion()", go)


class GraphicalButtonsTest(unittest.TestCase):
    """Every button is graphical: icon or image plus word, never bare text."""

    PLAIN_OK = {"btnHomePhoto"}  # pinned pure-text hero photo button

    def test_every_static_button_is_graphical(self):
        html = read_web("index.html")
        found = 0
        for match in re.finditer(r"<button\b([^>]*)>(.*?)</button>",
                                 html, re.S):
            tag, body = match.group(0), match.group(2)
            mid = re.search(r'id="([\w-]+)"', tag)
            bid = mid.group(1) if mid else "<noid>"
            if bid in self.PLAIN_OK:
                continue
            found += 1
            self.assertTrue("<span" in body or "<img" in body, bid)
        self.assertGreater(found, 30)

    def test_js_buttons_are_graphical(self):
        app = read_web("app.js")
        self.assertEqual(app.count('tour.className = "primary gtile";'), 2)
        self.assertEqual(app.count("tword\">Take the tour<"), 2)
        self.assertEqual(app.count("ticon\" aria-hidden=\"true\">◉<"), 2)
        self.assertIn("<span aria-hidden=\"true\">✓</span> Save", app)
        self.assertIn("<span aria-hidden=\"true\">✓</span> Confirm into form",
                      app)

    def test_tour_progress_buttons_stay_pinned(self):
        app = read_web("app.js")
        bar = app[app.index("function tourBar"):
                  app.index("function placeTourBar")]
        self.assertIn('next.className = "small";', bar)
        self.assertNotIn("movieBar", bar)


class MovieTest(unittest.TestCase):
    """The tour plays itself: autoplay + voice, beats and gates untouched."""

    BEATS = ("chooser", "register", "knowledge", "money", "trust",
             "rerank", "decline", "compare")

    def movie_chunk(self):
        app = read_web("app.js")
        return app[app.index("const TOUR_SCRIPT"):
                   app.index("async function init()")]

    def test_script_covers_all_beats(self):
        chunk = self.movie_chunk()
        for beat in self.BEATS:
            self.assertIn(beat + ": { hold:", chunk, beat)
        for say in re.findall(r'say: "([^"]+)"', chunk):
            self.assertGreater(len(say), 20)
        for banned in ("/api/listing/approve", "/api/listing/post", "N63"):
            self.assertNotIn(banned, chunk, banned)

    def test_hooks_wired(self):
        app = read_web("app.js")
        start = app[app.index("function startTour"):
                    app.index("function exitTour")]
        self.assertIn("tourAutoplayStart();", start)
        stop = app[app.index("function exitTour"):
                   app.index("async function tourNext")]
        self.assertIn("tourAutoplayStop();", stop)
        place = app[app.index("function placeTourBar"):
                    app.index("function endTourPreview")]
        self.assertIn("tourAutoplayBeat(index);", place)

    def test_audio_voice_guarded_and_muted(self):
        chunk = self.movie_chunk()
        self.assertNotIn("speechSynthesis", chunk)
        self.assertNotIn("SpeechSynthesisUtterance", chunk)
        self.assertNotIn("tourSpeak(", chunk)
        for marker in ("new Audio()", "tourAudio.play()",
                       "tourAudio.pause()", "tourAudio.muted",
                       "tourAudio.onended", '"tour.muted"',
                       "Mute voice", "Unmute voice"):
            self.assertIn(marker, chunk, marker)

    def test_audio_files_present(self):
        with open(os.path.join(ROOT, "eval_voice_results.json"),
                  encoding="utf-8") as fh:
            man = json.load(fh)
        self.assertEqual(man["voice"], "en_US-lessac-medium")
        self.assertEqual(man["format"], "mp3")
        self.assertEqual(len(man["files"]), 8)
        self.assertEqual([f["beat"] for f in man["files"]], list(self.BEATS))
        for f in man["files"]:
            p = os.path.join(ROOT, f["file"])
            self.assertTrue(os.path.exists(p), f["file"])
            self.assertGreater(os.path.getsize(p), 10000, f["file"])
            self.assertGreater(f["duration_s"], 0, f["file"])

    def test_beat_audio_map(self):
        chunk = self.movie_chunk()
        for beat in self.BEATS:
            self.assertIn(beat + ': "assets/audio/tour-' + beat + '.mp3"',
                          chunk, beat)
        for src in re.findall(r'assets/audio/(tour-\w+\.mp3)', chunk):
            self.assertTrue(os.path.exists(os.path.join(ROOT, "web", "assets",
                                                         "audio", src)), src)

    def test_pause_pauses_audio_and_holds(self):
        chunk = self.movie_chunk()
        stop = chunk[chunk.index("function tourStopTimer"):
                     chunk.index("function tourAdvance")]
        self.assertIn("tourAudio.pause()", stop)
        bar = chunk[chunk.index("function renderMovieBar"):
                    chunk.index("function tourAutoplayStart")]
        self.assertIn("tourPlaying = !tourPlaying", bar)
        self.assertIn("tourStopTimer();", bar)

    def test_advance_on_audio_ended(self):
        chunk = self.movie_chunk()
        play = chunk[chunk.index("function tourPlayAudio"):
                     chunk.index("function renderMovieBar")]
        self.assertIn("tourAudio.onended", play)
        self.assertIn("setTimeout(() => tourAdvance(token), 1200)", play)

    def test_movie_bar_is_separate(self):
        chunk = self.movie_chunk()
        self.assertIn('id = "movieBar";', chunk)
        self.assertIn("btnMoviePlay", chunk)
        self.assertIn("btnMovieMute", chunk)
        self.assertIn("Pause movie", chunk)
        self.assertIn("Play movie", chunk)

    def test_tour_section_pins_intact(self):
        app = read_web("app.js")
        section = app[app.index("===== guided tour (WO12)"):
                      app.index("===== end guided tour =====")]
        ids = re.findall(r'\{ id: "(\w+)"', section)
        self.assertEqual(tuple(ids), self.BEATS)
        self.assertEqual(section.count('title: "'), 8)
        self.assertEqual(section.count('line: "'), 8)


class CraftTest(unittest.TestCase):
    """Visual craft pass: focus, notice mark, payoff strip, door status."""

    def test_focus_ring_ink_not_amber(self):
        css = read_web("styles.css")
        self.assertIn(":focus-visible", css)
        ring = css[css.index(":focus-visible"):
                   css.index(":focus-visible") + 200]
        self.assertIn("2px solid var(--ink)", ring)
        self.assertNotIn("accent", ring)

    def test_notice_mark(self):
        css = read_web("styles.css")
        self.assertIn('.notice::before { content: "!";', css)

    def test_payoff_strip_reads_state(self):
        app = read_web("app.js")
        fn = app[app.index("function pagePayoff"):
                 app.index("function renderPager")]
        for read in ("bay.plan.results", "bay.parts.length",
                     "invState.cars.length", "invState.parts.length",
                     "state.report.verdicts"):
            self.assertIn(read, fn, read)
        pager = app[app.index("function renderPager"):
                    app.index("function activatePage")]
        self.assertIn("pagePayoff(view, idx)", pager)

    def test_door_status(self):
        app = read_web("app.js")
        for fn in ("paintDoorStatus(doorId, text)",
                   "bayCaseStatus()", "garageStatus()"):
            self.assertIn("function " + fn, app, fn)
        badges = app[app.index("function paintSideBadges"):
                     app.index("/* Camera-first intake (WO17)")]
        self.assertIn('paintDoorStatus("door-bay", bayCaseStatus());',
                      badges)
        self.assertIn('paintDoorStatus("door-garage", garageStatus());',
                      badges)
        self.assertIn(".doorstat", read_web("styles.css"))


class DiyGarageLabelTest(unittest.TestCase):
    """Finalize Phase B: the enthusiast side is named DIY Garage
    everywhere a side label appears. Old standalone labels are gone;
    lowercase place-words (my/your/the garage), art alt text, internal
    mode values, and comments intentionally stay."""

    def test_side_label_is_diy_garage(self):
        html = read_web("index.html")
        app = read_web("app.js")
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for text, name in ((html, "index.html"), (app, "app.js"),
                           (readme, "README.md")):
            self.assertIn("DIY Garage", text, name)
        old = ("Garage — Your cars", "Garage · ← Home", "Garage results",
               '"Garage home"', '"Garage index', '"Enthusiast:',
               "(enthusiast)", "I'm an enthusiast", "the Garage gets",
               "under the Garage", "in the Garage view", "(Bay/Garage)",
               "or enthusiast.", "enthusiast (Garage)", "as Garage steps")
        for text, name in ((html, "index.html"), (app, "app.js"),
                           (readme, "README.md")):
            masked = text.replace("DIY Garage", "DIY_GARAGE")
            for s in old:
                self.assertNotIn(s, masked, "%s in %s" % (s, name))

    def test_mode_values_stay_logic(self):
        app = read_web("app.js")
        self.assertIn('p.mode === "shop" ? "enthusiast" : "shop"', app)
        self.assertIn('Profile.saveProfile(localStorage, $("setupEmail").value, mode)',
                      app)


if __name__ == "__main__":
    unittest.main()
