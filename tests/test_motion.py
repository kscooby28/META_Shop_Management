"""Motion, confirm, sunlight tests (WO18): the app moves like a phone app.

Presentation, navigation, and photo input only. Direction means
something, every camera shot confirms, sunlight mode keeps type bold
and surfaces solid. The flows, grades, and gates underneath are pinned
by the existing suites, which must stay green untouched.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def root_tokens():
    return read("web/styles.css").partition(":root")[2].partition("}")[0]


def wo18_section():
    src = read("web/app.js")
    start = src.index("motion + confirm + sunlight (WO18)")
    end = src.index("function initBay()", start)
    return src[start:end]


def sunlight_block():
    css = read("web/styles.css")
    start = css.index("body.sunlight {")
    end = css.index("@media (min-width: 900px)", start)
    return css[start:end]


def keyframe_bodies():
    css = re.sub(r"/\*.*?\*/", "", read("web/styles.css"), flags=re.S)
    bodies = []
    for match in re.finditer(r"@keyframes\s+[\w-]+\s*\{", css):
        depth = 1
        i = match.end()
        while depth and i < len(css):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        bodies.append(css[match.end():i - 1])
    return bodies


class MotionTokensTest(unittest.TestCase):
    def test_ease_is_material_standard(self):
        self.assertIn("--ease: cubic-bezier(0.4, 0, 0.2, 1)", root_tokens())

    def test_timing_tokens(self):
        root = root_tokens()
        for token, value in (("--t-tap", "150ms"), ("--t-door", "150ms"),
                             ("--t-page", "300ms"), ("--t-sheet", "300ms"),
                             ("--t-flip", "300ms"), ("--t-reveal", "200ms")):
            self.assertIn("%s: %s" % (token, value), root, token)

    def test_no_functional_duration_over_1000ms(self):
        css = re.sub(r"/\*.*?\*/", "", read("web/styles.css"), flags=re.S)
        for number, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|s)(?![a-z])", css):
            ms = float(number) * (1 if unit == "ms" else 1000)
            self.assertLessEqual(ms, 1000, "%s%s runs too long" % (number, unit))

    def test_keyframes_animate_transform_and_opacity_only(self):
        bodies = keyframe_bodies()
        self.assertTrue(bodies)
        for body in bodies:
            props = re.findall(r"([a-z-]+)\s*:", body)
            self.assertEqual(sorted(set(props) - {"transform", "opacity"}), [])

    def test_no_transition_all(self):
        for line in read("web/styles.css").splitlines():
            if "transition:" in line:
                self.assertNotIn("all", line.split("transition:")[1].split(";")[0])

    def test_press_feedback_on_press(self):
        css = read("web/styles.css")
        match = re.search(r"button:active\s*\{\s*transform:\s*scale\(([\d.]+)\)", css)
        self.assertIsNotNone(match)
        self.assertGreaterEqual(float(match.group(1)), 0.95)
        self.assertLessEqual(float(match.group(1)), 0.98)
        self.assertIn("transform var(--t-tap) var(--ease)", css)

    def test_reduced_motion_honored(self):
        css = read("web/styles.css")
        calm = css.partition("@media (prefers-reduced-motion: reduce)")[2]
        calm = calm.partition("@media (prefers-reduced-motion: no-preference)")[0]
        for cls in ("page-in-right", "page-in-left", "door-fade", "sheet-up",
                    "flip-glide", "hero-clone"):
            self.assertIn(cls, calm, cls)
        self.assertIn(".reveal { transition: none; opacity: 1; }", calm)
        self.assertIn(".moved-flash { animation: none; }", calm)
        self.assertIn("button:active { transform: none; }", calm)


class DirectionTest(unittest.TestCase):
    def test_showview_plays_transitions(self):
        app = read("web/app.js")
        self.assertIn("UX.transitionFor(from, which)", app)
        self.assertIn("playViewTransition(document.querySelector(\".work\")", app)
        self.assertIn("currentView = which;", app)

    def test_transition_classes_exist(self):
        css = read("web/styles.css")
        self.assertIn(".page-in-right { animation: slidein-right var(--t-page) var(--ease); }", css)
        self.assertIn(".page-in-left { animation: slidein-left var(--t-page) var(--ease); }", css)
        self.assertIn(".door-fade { animation: doorfade var(--t-door) var(--ease); }", css)
        self.assertIn(".sheet-up { animation: sheetup var(--t-sheet) var(--ease); }", css)

    def test_sheet_rises_from_bottom(self):
        css = read("web/styles.css")
        sheet = css[css.index("@keyframes sheetup"):css.index("@keyframes sheetup") + 200]
        self.assertIn("translateY(48px)", sheet)

    def test_never_blocks_input(self):
        self.assertNotIn("pointer-events", wo18_section())


class FlipTest(unittest.TestCase):
    def test_fail_state_renders_before_flip(self):
        app = read("web/app.js")
        record = app[app.index("async function bayRecord"):app.index("async function bayEditPlan")]
        self.assertLess(record.index("renderBayPlan();"), record.index("playFlip("))
        self.assertIn('playFlip($("bayPlan"), before, testId', record)

    def test_cards_carry_stable_ids(self):
        self.assertIn('card.setAttribute("data-test", t.id);', read("web/app.js"))

    def test_only_moved_rows_glide(self):
        section = wo18_section()
        self.assertIn("if (moved && !calm) {", section)
        self.assertIn('card.classList.add("flip-glide");', section)
        self.assertIn('if (id === focusId || moved) card.classList.add("moved-flash");', section)

    def test_moved_row_gets_evidence_line(self):
        section = wo18_section()
        self.assertIn('p.className = "moved-note";', section)
        self.assertIn("flipNote(last)", read("web/app.js"))

    def test_reduced_motion_is_highlight_only(self):
        section = wo18_section()
        self.assertIn("if (calm) return;", section)

    def test_rerank_is_interruptible(self):
        section = wo18_section()
        self.assertIn("const run = ++flipRun;", section)
        self.assertGreaterEqual(section.count("if (run !== flipRun) return;"), 2)

    def test_flip_timing_uses_window(self):
        self.assertIn("UX.Motion.flipMs + 60", wo18_section())


class LadderTest(unittest.TestCase):
    def test_quiet_then_skeleton_then_stages(self):
        section = wo18_section()
        self.assertIn("setTimeout(() => overlay.showSkel(), M.quietMs)", section)
        self.assertIn("setTimeout(() => overlay.showSteps(), M.skeletonMs)", section)
        self.assertIn("list.hidden = true; // ladder: quiet first, steps only past 2s", section)

    def test_skeleton_shaped_like_result_card(self):
        section = wo18_section()
        skel = section[section.index("showSkel()"):section.index("showSteps()")]
        self.assertEqual(skel.count("skel-bar"), 4)

    def test_no_bare_spinner(self):
        for name in ("app.js", "ux.js", "profile.js", "inventory.js",
                     "gallery.js", "credentials.js", "styles.css", "index.html"):
            self.assertNotIn("spinner", read("web/" + name).lower(), name)

    def test_staged_text_not_percentages(self):
        section = wo18_section()
        self.assertNotIn("percent", section)
        self.assertIn('li.textContent = steps[i] + " — done";', section)

    def test_cancel_retry_always_visible_while_working(self):
        html = read("web/index.html")
        self.assertIn('id="btnConfirmCancel"', html)
        self.assertIn('id="btnConfirmRetry"', html)
        section = wo18_section()
        self.assertIn('$("confirmWorkActions").hidden = false;', section)
        self.assertIn("workCancelled = true;", section)
        self.assertIn("if (workRerun) workRerun();", section)

    def test_clear_done_state(self):
        section = wo18_section()
        self.assertIn("Done — the result is below.", section)
        self.assertIn('close.textContent = "Close";', section)

    def test_all_camera_flows_wrapped(self):
        app = read("web/app.js")
        self.assertGreaterEqual(app.count('withStages("'), 6)  # run-all, identify, bay vin, car photo, car vin, part


class ConfirmFlowTest(unittest.TestCase):
    SHOTS = ("yard", "hero", "bayvin", "carphoto", "carvin", "part")

    def test_guide_before_capture(self):
        app = read("web/app.js")
        self.assertIn("paintShotGuide(btnId, SHOT_FOR_CAM[camId]", app)
        self.assertIn('p.className = "camguide";', wo18_section())
        html = read("web/index.html")
        hero = html[html.index('id="view-home"'):html.index('id="view-yard"')]
        self.assertIn("camguide", hero)

    def test_preview_after_capture(self):
        app = read("web/app.js")
        twin = app[app.index("function twinCamera"):app.index("function wireCameras")]
        self.assertIn("openConfirm(camId, files);", twin)
        self.assertNotIn("dispatchEvent", twin)
        section = wo18_section()
        self.assertIn('$("confirmPhoto").src = latest.url || "";', section)
        self.assertIn("box.hidden = false;", section)

    def test_retake_left_use_right_primary(self):
        html = read("web/index.html")
        actions = html[html.index('id="confirmActions"'):html.index('id="confirmWorkActions"')]
        self.assertLess(actions.index("btnConfirmRetake"), actions.index("btnConfirmUse"))
        tag = re.search(r'<button[^>]*id="btnConfirmUse"[^>]*>', actions).group(0)
        self.assertIn("primary", tag)
        self.assertIn("Retake", actions)
        self.assertIn("Use photo", actions)

    def test_add_angle_strip_for_walkaround_only(self):
        section = wo18_section()
        self.assertIn('if (UX.guideFor(st.shot).mode !== "whole") { strip.hidden = true; return; }',
                      section)
        self.assertIn('add.textContent = "Add another angle";', section)

    def test_use_moves_into_unchanged_upload_path(self):
        section = wo18_section()
        self.assertIn("target.files = dt.files;", section)
        self.assertIn('target.dispatchEvent(new Event("change", { bubbles: true }));', section)
        for cam, target in (("fileCamera", "fileInput"),
                            ("homeHeroCamera", "fileInput"),
                            ("bayVinCamera", "bayVin"),
                            ("invCarPhotoCamera", "invCarPhoto"),
                            ("invCarVinCamera", "invCarVin"),
                            ("invPartPhotoCamera", "invPartPhoto")):
            self.assertIn("%s: \"%s\"" % (cam, target), section)

    def test_photo_stays_on_screen_through_analysis(self):
        section = wo18_section()
        self.assertIn('if (photoSrc) $("confirmPhoto").src = photoSrc;', section)
        self.assertIn("it stays here until the result lands", section)

    def test_reveal_order_answer_first(self):
        section = wo18_section()
        self.assertIn('$("carCard"), $("totals"), $("verdicts"), $("listingCard")', section)
        self.assertIn("i * M.revealStepMs", section)
        self.assertIn("}, M.maxMs);", section)

    def test_edit_before_publish_gate_untouched(self):
        section = wo18_section()
        for banned in ("/api/listing/approve", "/api/listing/post",
                       "runApprove", "runPost", "saveRules", "/api/rules"):
            self.assertNotIn(banned, section, banned)
        self.assertNotIn(".value =", section)

    def test_failure_saves_draft_with_photo(self):
        section = wo18_section()
        self.assertIn("saveShotDraft(flow, photo, err);", section)
        self.assertIn('UX.saveDraft(localStorage, "shot-" + flow, draft);', section)
        self.assertIn("photo: small ? photoSrc : null,", section)

    def test_specific_failure_lines(self):
        ux = read("web/ux.js")
        for phrase in ("Move closer and hold steady",
                       "Step back so the whole thing fits",
                       "Angle away from the sun",
                       "No car or part found in that shot",
                       "nothing here is a guess"):
            self.assertIn(phrase, ux, phrase)

    def test_low_confidence_never_guesses(self):
        section = wo18_section()
        self.assertIn('keep.textContent = "Keep as unknown";', section)
        self.assertIn('if (kind === "low") {', section)

    def test_every_shot_has_guide_and_mode(self):
        ux = read("web/ux.js")
        for shot in self.SHOTS:
            self.assertIn("%s: { mode:" % shot, ux, shot)


class CaptureModesTest(unittest.TestCase):
    def test_two_modes_labeled_in_plain_words(self):
        ux = read("web/ux.js")
        self.assertIn('whole: "Whole car"', ux)
        self.assertIn('part: "Single part"', ux)

    def test_mode_label_wherever_camera_opens(self):
        section = wo18_section()
        self.assertEqual(section.count('tag.className = "mode-tag";'), 2)  # guides + preview
        html = read("web/index.html")
        self.assertIn('<span class="mode-tag">Whole car</span>', html)


class SunlightTest(unittest.TestCase):
    def test_toggle_in_settings_and_header(self):
        html = read("web/index.html")
        tag = re.search(r'<button[^>]*id="navSun"[^>]*>', html).group(0)
        self.assertIn('aria-label="Sunlight mode"', tag)
        app = read("web/app.js")
        self.assertIn("Sunlight mode — bold type, solid surfaces for glare", app)
        self.assertIn('sunBox.id = "sunToggle";', app)
        self.assertIn('$("navSun").addEventListener("click"', wo18_section())

    def test_browser_local_only(self):
        ux = read("web/ux.js")
        self.assertIn('const SUN_KEY = "copilot.sunlight";', ux)
        section = wo18_section()
        self.assertNotIn("fetch(", section)
        self.assertNotIn("/api/", section)

    def test_weight_and_contrast_up(self):
        block = sunlight_block()
        self.assertIn("font-weight: 600;", block)
        self.assertIn("--ink: var(--sun-ink);", block)
        self.assertIn("--muted: var(--sun-muted);", block)

    def test_translucency_and_blur_gone(self):
        block = sunlight_block()
        for token in ("--tint-a: var(--sun-paper);", "--tint-b: var(--sun-paper);",
                      "--tint-c: var(--sun-paper);", "--scrim: var(--sun-solid);",
                      "--shadow: var(--sun-solid);"):
            self.assertIn(token, block, token)
        self.assertNotIn("rgba", block)
        self.assertNotIn("blur", block)
        for sel in ("button:disabled", ".testcard.eliminated", ".overlay g.dim"):
            rule = block[block.index(sel):block.index(sel) + 120]
            self.assertIn("opacity: 1;", rule, sel)

    def test_type_floors(self):
        block = sunlight_block()
        ui, meta = block.split("body.sunlight .thumbs figcaption", 1)
        self.assertIn("font-size: 16px; font-weight: 700;", ui)
        self.assertIn("font-size: 12px; font-weight: 700;", meta)
        for cls in (".hint", ".status", ".verdict table", ".msg", "#chips button"):
            self.assertIn(cls, ui, cls)
        for cls in (".strip figcaption", ".demobadge", ".msg .mode", ".part-list .tag"):
            self.assertIn(cls, meta, cls)

    def test_no_thin_weights(self):
        for weight in re.findall(r"font-weight:\s*(\d+)", sunlight_block()):
            self.assertGreaterEqual(int(weight), 600)


class HeroTest(unittest.TestCase):
    def test_hero_take_photo_on_home(self):
        html = read("web/index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-yard"')]
        self.assertIn('id="homeHeroCamera"', home)
        tag = re.search(r'<button[^>]*id="btnHomePhoto"[^>]*>([^<]*)</button>', home)
        self.assertIsNotNone(tag)
        self.assertIn("Take a photo", tag.group(1))
        self.assertIn('class="photo herophoto"', home)
        self.assertLess(home.index("screen-line"), home.index("btnHomePhoto"))

    def test_hero_hands_into_yard_intake(self):
        app = read("web/app.js")
        self.assertIn('twinCamera("homeHeroCamera", "fileInput", "btnHomePhoto")', app)
        section = wo18_section()
        hero = section[section.index('if (st.shot === "hero")'):section.index("if (AUTO_SHOT")]
        self.assertIn('showView("yard");', hero)
        self.assertIn("heroExpand(rect, url);", hero)

    def test_captured_photo_expands_into_screen(self):
        section = wo18_section()
        expand = section[section.index("function heroExpand"):section.index("function yardPhoto")]
        self.assertIn('img.className = "hero-clone";', expand)
        self.assertIn("translate(", expand)
        self.assertIn("scale(", expand)
        self.assertIn('img.style.opacity = "0";', expand)
        self.assertIn("UX.Motion.pageMs + 80", expand)
        self.assertIn("calmMotion()) return;", expand)


class Order17GuardsTest(unittest.TestCase):
    def test_home_still_has_no_primary(self):
        html = read("web/index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-yard"')]
        self.assertEqual(len(re.findall(r'class="primary[" ]', home)), 0)

    def test_approve_gate_prominence_kept(self):
        tag = re.search(r'<button[^>]*id="btnApprove"[^>]*>', read("web/index.html")).group(0)
        self.assertIn("primary approve", tag)


if __name__ == "__main__":
    unittest.main()
