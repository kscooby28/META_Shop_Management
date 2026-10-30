"""Graphical-choice tests (WO20): every choice graphical, system-wide.

Layer 1 pins the shared system: tile/card language, motion discipline
(existing keyframes only, no one-off durations), accent count frozen,
network baseline frozen. Later layers append their own classes below.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")


def read(name):
    with open(os.path.join(WEB, name), encoding="utf-8") as fh:
        return fh.read()


def css():
    return read("styles.css")


def css_no_comments():
    return re.sub(r"/\*.*?\*/", "", css(), flags=re.S)


def rule_body(selector):
    plain = css_no_comments()
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", plain)
    assert match, "missing rule " + selector
    return match.group(1)


def reduced_block():
    plain = css_no_comments()
    start = plain.index("@media (prefers-reduced-motion: reduce)")
    end = plain.index("@media (prefers-reduced-motion: no-preference)",
                      start)
    return plain[start:end]


KEYFRAMES = {"slidein-right", "slidein-left", "doorfade", "sheetup",
             "movedflash", "skelpulse", "fadein"}
# Literal durations already in the tree at WO19 (panel slide, button ease,
# strip ease, flash, skeleton pulse). Anything new must be a token.
LEGACY_DURATIONS = {"0.15s", "0.12s", "0.2s", "0.25s", "900ms"}


class SystemClassesTest(unittest.TestCase):
    def test_tile_language(self):
        tile = rule_body(".gtile")
        self.assertIn("min-height: 56px;", tile)
        self.assertIn("var(--radius-card)", tile)
        self.assertIn("inset 0 1px 0 var(--line)", tile)
        self.assertIn("var(--text-title)", rule_body(".gtile .tword"))
        self.assertIn("800", rule_body(".gtile .tword"))
        self.assertIn("var(--text-body)", rule_body(".gtile .tfield"))
        self.assertIn("var(--text-title)", rule_body(".gtile .ticon"))
        self.assertIn("var(--radius-small)", rule_body(".gtile img.timg"))
        self.assertIn("var(--ink)",
                      rule_body('.gtile[aria-pressed="true"]'))

    def test_card_language(self):
        card = rule_body(".gcard")
        self.assertIn("var(--radius-card)", card)
        self.assertIn("inset 0 1px 0 var(--line)", card)
        self.assertIn("var(--text-title)", rule_body(".gcard .ctitle"))

    def test_segments_and_sheets(self):
        self.assertIn("var(--ink)",
                      rule_body('.seg button[aria-pressed="true"]'))
        sheet = rule_body(".gsheet")
        self.assertIn("sheetup var(--t-sheet) var(--ease)", sheet)
        self.assertIn("var(--radius-card)", sheet)
        self.assertIn("display: none;", rule_body(".gsheet[hidden]"))
        self.assertIn("var(--text-title)", rule_body(".gsheet .gtitle"))

    def test_band_art_is_committed_raster(self):
        body = rule_body(".settingband img")
        self.assertIn("display: block", body)
        self.assertIn("object-fit: cover", body)
        self.assertIn("110px", body)


class SystemMotionTest(unittest.TestCase):
    def test_keyframes_set_unchanged(self):
        self.assertEqual(
            set(re.findall(r"@keyframes\s+([\w-]+)", css_no_comments())),
            KEYFRAMES)

    def test_no_one_off_durations_or_easings(self):
        for value in re.findall(r"(?:transition|animation):\s*([^;]+);",
                                css_no_comments()):
            for lit in re.findall(r"\d+\.?\d*m?s\b", value):
                self.assertIn(lit, LEGACY_DURATIONS, value)
            self.assertNotIn("cubic-bezier(", value)
            bare = re.sub(r"var\(--[\w-]+\)", "", value)
            words = set(re.findall(r"[a-z][\w-]*", bare))
            self.assertEqual(words - KEYFRAMES - {
                "transform", "opacity", "background-color",
                "border-color", "ease", "infinite", "alternate",
                "none", "ms", "s"}, set(), value)

    def test_reduced_motion_covers_new_motion(self):
        block = reduced_block()
        self.assertIn(".gsheet", block)


class AccentFrozenTest(unittest.TestCase):
    def test_amber_still_only_money_and_primary(self):
        plain = css_no_comments()
        self.assertEqual(plain.count("var(--accent)"), 5)
        self.assertEqual(plain.count("var(--accent-ink)"), 1)


class NetworkBaselineTest(unittest.TestCase):
    def test_no_new_network_paths(self):
        fetches = 0
        for name in os.listdir(WEB):
            if not name.endswith(".js"):
                continue
            fetches += read(name).count("fetch(")
        self.assertEqual(fetches, 6)
        for base, _, files in os.walk(WEB):
            for name in files:
                path = os.path.join(base, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        text = fh.read()
                except (UnicodeDecodeError, ValueError):
                    continue  # binary assets hold no URLs
                for url in re.findall(r"https?://[^\s\"'<>]+", text):
                    self.assertEqual(url, "http://www.w3.org/2000/svg",
                                     path)


class LandingTest(unittest.TestCase):
    def home(self):
        html = read("index.html")
        return html[html.index('id="view-home"'):html.index('id="view-yard"')]

    def test_entrances_tappable_never_primary(self):
        home = self.home()
        for door in ("door-bay", "door-yard", "door-driveway"):
            tag = re.search(r'<button[^>]*id="%s"[^>]*>' % door,
                            home).group(0)
            self.assertNotIn("primary", tag, door)
            self.assertIn("door entrance", tag, door)

    def test_home_zero_primaries(self):
        self.assertEqual(
            len(re.findall(r'class="primary[" ]', self.home())), 0)

    def test_door_press_beat(self):
        app = read("app.js")
        self.assertIn("function doorPress(btn)", app)
        self.assertIn("calmMotion()", app)
        at = app.index("function doorPress")
        press = app[at:at + 400]
        self.assertIn('"door-fade"', press)
        for door, view in (("door-bay", 'showView("bay")'),
                           ("door-yard", 'showView("yard")'),
                           ("door-driveway", 'showView("inventory")')):
            self.assertIn('"%s"' % door, app)
            self.assertIn(view, app)

    def test_generic_shop_signage_only(self):
        home = self.home()
        self.assertNotIn("Pixar", read("index.html"))
        self.assertIn('src="assets/door-shop.png"', home)
        for label in ("Bay — Fix it", "Yard — Strip it",
                      "Driveway — Your own car"):
            self.assertIn(label, home)

    def test_backdrop_is_illustration_not_inventory(self):
        home = self.home()
        scene = home[home.index('<div class="scene"'):
                     home.index('id="btnHomePhoto"')]
        self.assertIn("<img", scene)
        self.assertIn('src="assets/landing.png"', scene)
        self.assertNotIn("demo/frame", scene)


class SettingTest(unittest.TestCase):
    def test_setting_map(self):
        app = read("app.js")
        for view, setting in (("bay", "shop"), ("yard", "yard"),
                              ("inventory", "garage"), ("home", "home")):
            self.assertIn('%s: "%s"' % (view, setting), app)
        self.assertIn("compare: null", app)

    def test_swap_hooks(self):
        app = read("app.js")
        for call in ('applySetting("bay")', 'applySetting("yard")',
                     'applySetting("inventory")', 'applySetting("home")',
                     "applySetting(dest)"):
            self.assertIn(call, app, call)
        opener = app[app.index('btnCompareOpen"'):app.index(
            'btnCompareOpen"') + 200]
        self.assertNotIn("applySetting", opener)

    def test_case_survives_setting_change(self):
        # Chrome-only proof: the swap touches the body dataset and the
        # band art, never case state, sessions, or grades.
        app = read("app.js")
        block = app[app.index("var SETTING_FOR_VIEW"):
                    app.index("renderSettingBand(s);\n}")]
        self.assertIn("document.body.dataset.setting", block)
        self.assertIn("settingBand", block)
        for banned in ("state.", "state[", "sessionId", "fetch(",
                       "put_session", "evaluate", "amberMoney",
                       "renderVerdicts", "renderTotals", "approve("):
            self.assertNotIn(banned, block, banned)

    def test_neutral_panels(self):
        html = read("index.html")
        tag = re.search(r'<section[^>]*id="sec-compare"[^>]*>',
                        html).group(0)
        self.assertIn("neutralpanel", tag)
        app = read("app.js")
        self.assertIn('box.classList.add("neutralpanel")', app)
        self.assertEqual(
            app.count("Neutral panel over the current setting"), 2)

    def test_band_art_is_illustration(self):
        app = read("app.js")
        bands = app[app.index("var SETTING_BANDS"):
                    app.index("function renderSettingBand")]
        for label in ("Illustrated shop interior", "Illustrated yard lot",
                      "Illustrated home garage"):
            self.assertIn(label, bands, label)
        self.assertIn("<img", bands)
        self.assertNotIn("<svg", bands)
        self.assertNotIn("demo/frame", bands)


class StagingTest(unittest.TestCase):
    def test_working_view_helper(self):
        app = read("app.js")
        helper = app[app.index("function stageWorkview"):
                     app.index("function stageWorkview") + 600]
        self.assertIn("Working view — the job at hand", helper)
        self.assertNotIn(".src", helper)
        self.assertEqual(app.count("stageWorkview("), 4)

    def test_staged_css(self):
        self.assertIn("4px solid var(--line)", rule_body(".staged"))
        self.assertIn("var(--ink)",
                      rule_body('body[data-setting="shop"] .staged'))
        self.assertIn("var(--text-meta)", rule_body(".workview"))

    def test_no_location_claims(self):
        banned = ("in the shop", "in the garage", "now in the",
                  "located", "arrived at")
        for base, _, files in os.walk(WEB):
            for name in files:
                if not name.endswith((".html", ".js", ".css")):
                    continue
                path = os.path.join(base, name)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                for phrase in banned:
                    self.assertNotIn(phrase, text, path)


class ConfirmTilesTest(unittest.TestCase):
    def test_retake_tile_reshows_shot(self):
        html = read("index.html")
        btn = re.search(r'<button[^>]*id="btnConfirmRetake"[^>]*>(.*?)</button>',
                        html, re.S).group(0)
        self.assertIn("gtile", btn)
        self.assertIn('<img class="timg"', btn)
        self.assertIn("Shoot it again", btn)
        app = read("app.js")
        self.assertIn("#btnConfirmRetake img.timg", app)
        self.assertIn('retakeThumb.src = latest.url;', app)

    def test_use_tile_stays_the_one_primary(self):
        html = read("index.html")
        tag = re.search(r'<button[^>]*id="btnConfirmUse"[^>]*>',
                        html).group(0)
        self.assertIn("primary", tag)
        self.assertIn("gtile", tag)
        self.assertIn("Use photo", html)
        css = css_no_comments()
        self.assertIn("button.primary .ticon", css)

    def test_add_angle_tile(self):
        app = read("app.js")
        self.assertIn('add.className = "gtile";', app)
        self.assertIn('add.textContent = "Add another angle";', app)
        self.assertIn('plus.className = "ticon";', app)

    def test_confirm_gates_unmoved(self):
        app = read("app.js")
        for marker in ("target.files = dt.files;",
                       'target.dispatchEvent(new Event("change"',
                       "openConfirm(camId, files);",
                       'twinCamera("fileCamera", "fileInput", "btnPhoto")'):
            self.assertIn(marker, app, marker)


class SourceTilesTest(unittest.TestCase):
    PAIRS = (("btnPhoto", "fileInput"),
             ("btnBayVinPhoto", "bayVin"),
             ("btnInvCarPhotoCam", "invCarPhoto"),
             ("btnInvCarVinCam", "invCarVin"),
             ("btnInvPartPhotoCam", "invPartPhoto"))

    def test_camera_tiles(self):
        html = read("index.html")
        for btn, _ in self.PAIRS:
            tag = re.search(r'<button[^>]*id="%s"[^>]*>' % btn,
                            html).group(0)
            self.assertIn("gtile", tag, btn)
            self.assertIn("photo", tag, btn)

    def test_os_input_hidden_behind_tile(self):
        html = read("index.html")
        for _, fallback in self.PAIRS:
            tag = re.search(r'<input[^>]*id="%s"[^>]*>' % fallback,
                            html).group(0)
            self.assertIn("hidden", tag, fallback)
            label = re.search(r'<label[^>]*for="%s"[^>]*>' % fallback,
                              html).group(0)
            self.assertIn("gtile", label, fallback)

    def test_demo_tile_labeled(self):
        html = read("index.html")
        btn = re.search(r'<button[^>]*id="btnDemo"[^>]*>(.*?)</button>',
                        html, re.S).group(0)
        self.assertIn("gtile", btn)
        self.assertIn('src="demo/frame1.svg"', btn)
        self.assertIn("Labeled demo frames", btn)


class GradeCardsTest(unittest.TestCase):
    def test_grade_cards(self):
        app = read("app.js")
        self.assertIn("const gradeBtn = (g) =>", app)
        self.assertIn('class="gtile gradecard" data-override=', app)
        self.assertIn("grade-sm grade-' + g", app)
        self.assertIn("Rule grade", app)
        self.assertIn("clear override", app)
        self.assertIn("var(--radius-card)", rule_body(
            ".override-row .gradecard") + rule_body(".gtile"))

    def test_summary_header_collapsed_evidence(self):
        app = read("app.js")
        card = app[app.index("card.innerHTML ="):app.index(
            "card.querySelector('[data-f=")]
        for marker in ('class="vword"', 'class="vprice"',
                       'class="vpull"',
                       '<details class="rowmore">'
                       "<summary>Evidence and inputs</summary>"):
            self.assertIn(marker, card, marker)
        self.assertLess(card.index("<summary>"),
                        card.index("<table>"))

    def test_override_logic_unmoved(self):
        app = read("app.js")
        for marker in ('btn.getAttribute("data-override")',
                       "state.overrides[v.part_id] = grade",
                       "delete state.overrides[v.part_id]",
                       "await runVerdicts(true)"):
            self.assertIn(marker, app, marker)


class GateTest(unittest.TestCase):
    def test_listing_card_is_the_gate(self):
        html = read("index.html")
        tag = re.search(r'<div[^>]*id="listingCard"[^>]*>',
                        html).group(0)
        self.assertIn("gatecard", tag)
        gate = rule_body(".gatecard")
        self.assertIn("2px solid var(--ink)", gate)
        self.assertIn("var(--radius-card)", gate)

    def test_approve_gate_untouched(self):
        html = read("index.html")
        tag = re.search(r'<button[^>]*id="btnApprove"[^>]*>',
                        html).group(0)
        self.assertIn("primary approve", tag)
        app = read("app.js")
        for marker in ("mock outbox", "chaching", "btnPost",
                       "Discard draft"):
            self.assertIn(marker, app + html, marker)


class MotionChoiceTest(unittest.TestCase):
    def test_graphical_pass_fail(self):
        app = read("app.js")
        for res, glyph, word in (("pass", "✓", "Pass"),
                                ("fail", "✕", "Fail")):
            self.assertIn('class="gtile verdictbtn" data-res="%s"' % res,
                          app)
        self.assertIn('aria-hidden="true">✓</span>', app)
        self.assertIn('aria-hidden="true">✕</span>', app)
        self.assertIn('<span class="tword">Pass</span>', app)
        self.assertIn('<span class="tword">Fail</span>', app)
        for marker in ('querySelectorAll("[data-res]")',
                       'btn.getAttribute("data-res")',
                       'querySelectorAll("[data-move]")',
                       'querySelector("[data-edit]")'):
            self.assertIn(marker, app, marker)

    def test_verdict_button_colors(self):
        css = css_no_comments()
        self.assertIn("var(--grade-a)",
                      rule_body('.verdictbtn[data-res="pass"]'))
        self.assertIn("var(--grade-c)",
                      rule_body('.verdictbtn[data-res="fail"]'))
        for sel in ('.verdictbtn[data-res="pass"]',
                    '.verdictbtn[data-res="fail"]',
                    ".verdictbtn"):
            self.assertNotIn("var(--accent", rule_body(sel), sel)

    def test_status_first_header(self):
        app = read("app.js")
        self.assertIn('class="tmeta"', app)
        self.assertIn("shop time unknown", app)
        self.assertIn("<summary>Why it ranks here</summary>", app)

    def test_flip_evidence_on_moved_rows(self):
        app = read("app.js")
        flip = app[app.index("function playFlip"):
                   app.index("function playFlip") + 1400]
        self.assertIn('"Moved " + (now > was ? "down" : "up")', flip)
        self.assertIn("moved-note", flip)
        self.assertIn("flip-glide", flip)
        self.assertIn("if (calm) return;", flip)

    def test_engine_columns(self):
        app = read("app.js")
        for marker in ('pc.className = "pccard";',
                       'class="pchead"', 'class="engines"',
                       'class="enginecol"', 'class="enginelabel"',
                       "Muse Spark 1.3", "Muse Spark Open, open-weight via Baseten"):
            self.assertIn(marker, app, marker)
        css = css_no_comments()
        self.assertIn("@media (max-width: 700px)", css)
        self.assertIn("@media (min-width: 701px)", css)
        self.assertIn("1fr 1fr", rule_body(".engines"))


class PickersTest(unittest.TestCase):
    SELECTS = ("listingPart", "wonderPart", "bayArea", "invKnowCar",
               "invPartCar", "invPartRel")

    def test_carriers_stay_logic_reads_value(self):
        html = read("index.html")
        app = read("app.js")
        for sel in self.SELECTS:
            self.assertIn('id="%s"' % sel, html, sel)
            self.assertIn('$("' + sel + '").value', app, sel)
        self.assertIn('[data-f="demand"]', app)

    def test_faces(self):
        app = read("app.js")
        for marker in ("function segify(sel)", "function openOptSheet",
                       "function sheetPicker", "function syncPickers",
                       'seg.className = "seg"',
                       'sheet.className = "gsheet"',
                       'h.className = "gtitle"',
                       'opts.className = "gopts"',
                       'segify($("bayArea"))',
                       'segify($("invPartRel"))',
                       'sheetPicker($("listingPart"), "Pick a part")',
                       'sheetPicker($("wonderPart"), "Ask about a part")',
                       'sheetPicker($("invKnowCar"), "Car notes for")',
                       'sheetPicker($("invPartCar"), "Attach to car")',
                       "new Event(\"change\""):
            self.assertIn(marker, app, marker)
        self.assertEqual(app.count("sel.hidden = true;"), 2)

    def test_sheet_native_speed(self):
        app = read("app.js")
        sheet = app[app.index("function openOptSheet"):
                    app.index("function sheetPicker")]
        for banned in ("setTimeout", "fetch(", "await", "animate("):
            self.assertNotIn(banned, sheet, banned)


class SettingsCardsTest(unittest.TestCase):
    def test_cards(self):
        app = read("app.js")
        self.assertIn('card.className = "gcard homehead";', app)
        for title in ('"Profile"', '"Demo"', '"Display"'):
            self.assertIn(title, app)
        self.assertIn('wrap.className = "gcard";', app)

    def test_native_semantics_kept(self):
        app = read("app.js")
        self.assertIn('sunBox.id = "sunToggle";', app)
        self.assertIn("offBox.type = \"checkbox\";", app)
        self.assertIn("sunBox.type = \"checkbox\";", app)
        self.assertIn('sun.className = "gtile";', app)
        self.assertIn('off.className = "gtile";', app)


class WayfindingTest(unittest.TestCase):
    def test_backs_show_space_and_destination(self):
        html = read("index.html")
        for bid, text in (("backYard", "◧</span> Yard · ← Home"),
                          ("backBay", "⚒</span> Bay · ← Home"),
                          ("backInv", "⌂</span> Driveway · ← Home"),
                          ("backCompare", "⇄</span> Compare · ← Yard results")):
            body = re.search(r'<button[^>]*id="%s"[^>]*>(.*?)</button>' % bid,
                             html, re.S).group(1)
            self.assertIn(text, body, bid)

    def test_nav_home_wayfinding(self):
        html = read("index.html")
        tag = re.search(r'<button[^>]*id="navHome"[^>]*>(.*?)</button>',
                        html, re.S).group(0)
        self.assertIn("⌂", tag)
        self.assertIn("Home", tag)


class EmptiesTest(unittest.TestCase):
    def test_every_empty_has_art_action_and_copy(self):
        app = read("app.js")
        with open(os.path.join(ROOT, "web", "ux.js"),
                  encoding="utf-8") as fh:
            ux = fh.read()
        keys = set(re.findall(r'emptyInto\(\w+, "(\w+)"', app))
        self.assertGreaterEqual(len(keys), 10)
        art = app[app.index("const EMPTY_ART"):
                  app.index("function emptyInto")]
        for key in keys:
            self.assertIn(key + ":", ux, key)
            self.assertIn(key + ':', art, key)


class ChipsDeclineProfileTest(unittest.TestCase):
    def test_chips_are_cards(self):
        html = read("index.html")
        chips = html[html.index('id="chips"'):html.index('id="chatForm"')]
        self.assertEqual(chips.count('class="gtile"'), 3)
        self.assertEqual(chips.count("data-chip="), 3)
        for glyph in ("◉", "?", "✎"):
            self.assertIn(glyph, chips, glyph)

    def test_decline_mark_never_amber(self):
        app = read("app.js")
        self.assertIn('class="dmark"', app)
        mark = rule_body(".decline .dmark")
        self.assertIn("var(--grade-c)", mark)
        self.assertNotIn("var(--accent", mark)

    def test_profile_cards_one_primary(self):
        html = read("index.html")
        overlay = html[html.index('id="setupOverlay"'):
                       html.index('id="confirm"')]
        for bid in ("btnSetupShop", "btnSetupFan"):
            tag = re.search(r'<button[^>]*id="%s"[^>]*>' % bid,
                            overlay).group(0)
            self.assertIn("gtile", tag, bid)
        self.assertEqual(
            len(re.findall(r'class="primary[" ]', overlay)), 1)
        fan = re.search(r'<button[^>]*id="btnSetupFan"[^>]*>',
                        overlay).group(0)
        self.assertIn("primary", fan)


class FreeformExceptionTest(unittest.TestCase):
    def test_inputs_stay_honestly_minimal(self):
        html = read("index.html")
        year = re.search(r'<input[^>]*id="bayYear"[^>]*>', html).group(0)
        self.assertIn('type="text"', year)
        self.assertNotIn("gtile", year)
        app = read("app.js")
        self.assertIn('data-f="price_low" type="number"', app)


class JourneyTest(unittest.TestCase):
    def tour_slice(self):
        app = read("app.js")
        start = app.index("const TOUR_BEATS")
        end = app.index("function tourEnsureSeed")
        return app[start:end]

    def test_journey_line(self):
        app = read("app.js")
        bar = app[app.index("function tourBar"):
                  app.index("function placeTourBar")]
        for marker in ('journey.className = "jline";',
                       'd.className = "jdot";',
                       'd.classList.add("now");',
                       'd.classList.add("done");',
                       'dest.className = "jdest";',
                       "TOUR_BEATS.forEach((b, i) => {",
                       '"Next: " + TOUR_BEATS[index + 1].title'):
            self.assertIn(marker, bar, marker)
        self.assertNotIn('"Back"', bar)
        self.assertNotIn("spotlight", bar)
        self.assertNotIn("scrim", bar)

    def test_journey_css(self):
        self.assertIn("var(--radius-round)", rule_body(".jdot"))
        self.assertIn("var(--ink)", rule_body(".jdot.now"))
        self.assertIn("var(--muted)", rule_body(".jdot.done"))
        self.assertIn("var(--text-meta)", rule_body(".jdest"))
        for sel in (".jline", ".jdot", ".jdot.now", ".jdot.done",
                    ".jdest"):
            self.assertNotIn("var(--accent", rule_body(sel), sel)

    def test_ten_taps_end_to_end(self):
        # The state machine, statically: ten beats, one tap advances
        # exactly one beat, the eleventh tap cannot exist (exit at ten).
        app = read("app.js")
        beats = re.findall(r'\{ id: "(\w+)"',
                           app[app.index("const TOUR_BEATS"):
                               app.index("let tourState")])
        self.assertEqual(len(beats), 10)
        nxt = app[app.index("async function tourNext"):
                  app.index("async function tourEnsureSeed")]
        self.assertIn("tourState.beat + 1 >= TOUR_BEATS.length", nxt)
        self.assertIn("tourState.beat += 1;", nxt)
        writes = [m for m in re.finditer(r"tourState\.beat\s*(\+?=)",
                                         app)]
        self.assertEqual(len(writes), 1)
        self.assertIn("tourState = { beat: 0 };", app)
        self.assertEqual(app.count("addEventListener(\"click\", guard(tourNext"),
                        1)

    def test_tour_never_swaps_setting_or_touches_gates(self):
        tour = self.tour_slice()
        for banned in ("applySetting", "runApprove", "runPost",
                       "saveRules", "/api/rules", "$(\"btnApprove\")",
                       "$(\"btnPost\")"):
            self.assertNotIn(banned, tour, banned)
        app = read("app.js")
        self.assertIn("The tour starts past the doors", app)

    def test_forced_demo_untouched(self):
        app = read("app.js")
        self.assertIn("runCompare({ demo: true })", app)
        self.assertIn("nothing approved", app)


class PolishTest(unittest.TestCase):
    def lum(self, hexval):
        rgb = [int(hexval[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
               for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def test_b_hue_separated_from_amber(self):
        root = css_no_comments().partition("}")[0]
        grade_b = re.search(r"--grade-b:\s*(#[0-9a-f]+)", root).group(1)
        accent = re.search(r"--accent:\s*(#[0-9a-f]+)", root).group(1)
        self.assertEqual(grade_b, "#9aa05c")
        self.assertNotEqual(grade_b, accent)
        tint = re.search(r"--tint-b:\s*rgba\(([^)]+)\)", root).group(1)
        self.assertTrue(tint.startswith("154, 160, 92"), tint)

    def test_b_badge_contrast_reproved(self):
        ratio = (self.lum("#9aa05c") + 0.05) / (self.lum("#14110c") + 0.05)
        self.assertGreaterEqual(ratio, 4.5)

    def test_tabular_amber_money(self):
        self.assertIn(".money, .big-money, .totalcard .big "
                      "{ font-variant-numeric: tabular-nums; }",
                      css_no_comments())

    def test_totals_always_amber(self):
        app = read("app.js")
        self.assertIn("amberMoney(esc(sentence))", app)
        self.assertIn("amberMoney(esc(sentence.slice(0, cut)))", app)
        self.assertIn("amberMoney(esc(labor.plain_words))", app)


if __name__ == "__main__":
    unittest.main()
