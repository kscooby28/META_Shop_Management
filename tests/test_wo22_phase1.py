"""WO22 Phase 1 pins: tour runs fresh, narration matches, captions stay.

Static pins for the submission-hardening behaviors: the fixed caption
strip, the fresh-profile demo preload, the per-beat true targets, the
verbatim recorded-live spare row, the listing overflow guards, and the
per-view mode pill. Offline; pixels stay a smoke proof.
"""

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_web(name):
    with open(os.path.join(ROOT, "web", name), encoding="utf-8") as fh:
        return fh.read()


def tour_section():
    src = read_web("app.js")
    start = src.index("===== guided tour (WO12)")
    end = src.index("===== end guided tour =====")
    return src[start:end]


def fn_body(src, name, end):
    return src[src.index("function " + name):src.index(end)]


class CaptionStripTest(unittest.TestCase):
    def test_strip_is_fixed_above_bottom_bar(self):
        css = read_web("styles.css")
        bar = css[css.index("#tourBar {"):css.index("#tourBar .tourline")]
        for marker in ("position: fixed;", "left: 0.5rem;",
                       "right: 0.5rem;", "z-index: 120;",
                       "env(safe-area-inset-bottom"):
            self.assertIn(marker, bar, marker)

    def test_beat_line_clamps_to_two(self):
        css = read_web("styles.css")
        start = css.index("#tourBar .tourline {")
        line = css[start:css.index("}", start)]
        self.assertIn("-webkit-line-clamp: 2;", line)
        self.assertIn("overflow: hidden;", line)

    def test_bar_docks_to_body_not_flow(self):
        place = fn_body(read_web("app.js"), "placeTourBar",
                        "function endTourPreview")
        self.assertIn("document.body.appendChild(bar);", place)
        self.assertNotIn("insertBefore", place)
        self.assertIn("tourAutoplayBeat(index);", place)

    def test_reveal_keeps_target_above_strip(self):
        app = read_web("app.js")
        reveal = fn_body(app, "tourReveal", "/* ===== tour autoplay")
        self.assertIn("revealSection(ps.id)", reveal)
        self.assertIn("getElementById(\"tourBar\")", reveal)
        self.assertIn("window.scrollTo({", reveal)
        self.assertNotIn("scrollIntoView", reveal)


class FreshTourTest(unittest.TestCase):
    def test_money_beat_preloads_demo_frames(self):
        beat = fn_body(tour_section(), "showTourBeat",
                       "const TOUR_RECORDED_SPARE")
        self.assertIn("if (!state.images.length) {", beat)
        self.assertIn("state.demo = true;", beat)
        self.assertIn("state.images = DEMO_FRAMES.map(", beat)
        self.assertIn("renderThumbs();", beat)

    def test_beat_errors_still_place_caption(self):
        beat = fn_body(tour_section(), "showTourBeat",
                       "const TOUR_RECORDED_SPARE")
        self.assertIn("} catch (err) {", beat)
        self.assertIn("notice(esc(err.message));", beat)
        tail = beat[beat.index("} catch (err) {"):]
        self.assertIn("placeTourBar(beat, tourState.beat);", tail)

    def test_targets_show_what_narration_says(self):
        beat = fn_body(tour_section(), "showTourBeat",
                       "const TOUR_RECORDED_SPARE")
        for marker in ('sel.value = "car-m3";',
                       "renderInvKnow();",
                       '"#verdicts .verdict"',
                       '$("bayCaseCard")',
                       '"#listingCard .approve-row"',
                       '"tourRecordedLive"'):
            self.assertIn(marker, beat, marker)


class RecordedSpareTest(unittest.TestCase):
    def test_reason_quoted_verbatim(self):
        with open(os.path.join(ROOT, "eval_scale_results.json"),
                  encoding="utf-8") as fh:
            recorded = json.load(fh)
        rows = [c for c in recorded["cases"]
                if c["case"] == "inventory-demo"][0]["parts"]
        verbatim = [p["open_reason"] for p in rows
                    if p["part_id"] == "ip-coil"][0]
        app = read_web("app.js")
        self.assertIn(verbatim, app)
        self.assertIn('"B"', app[app.index("const TOUR_RECORDED_SPARE"):
                                app.index("function tourShowRecordedSpare")])

    def test_card_labeled_recorded_live_not_demo(self):
        app = read_web("app.js")
        card = fn_body(app, "tourShowRecordedSpare",
                       "/* ===== end guided tour =====")
        self.assertIn("Recorded live run", card)
        self.assertIn("Muse Spark Open on Baseten", card)
        self.assertIn("TOUR_RECORDED_SPARE.when", card)
        self.assertIn("not a demo sample", card)
        self.assertNotIn("demoBadge", card)
        self.assertNotIn("DEMO", card)
        const = app[app.index("const TOUR_RECORDED_SPARE"):
                    app.index("function tourShowRecordedSpare")]
        self.assertIn('when: "2026-10-28"', const)

    def test_narration_still_names_the_catch(self):
        self.assertIn("roadside spare", tour_section())


class ListingOverflowTest(unittest.TestCase):
    def test_studio_photo_capped(self):
        css = read_web("styles.css")
        start = css.index("#studioBox img {")
        rule = css[start:css.index("}", start)]
        self.assertIn("max-height: 40vh;", rule)
        self.assertIn("max-width: 100%;", css)

    def test_gate_children_cannot_force_width(self):
        css = read_web("styles.css")
        for marker in ("#listingCard > * { min-width: 0;",
                       ".tilegrid > * { min-width: 0; }",
                       "#sec-listing img { max-width: 100%;"):
            self.assertIn(marker, css, marker)

    def test_verdict_art_is_a_banner(self):
        css = read_web("styles.css")
        start = css.index(".verdict > img.timg {")
        rule = css[start:css.index("}", start)]
        for marker in ("width: 100%;", "max-height: 18rem;",
                       "object-fit: cover;"):
            self.assertIn(marker, rule, marker)


class PerViewPillTest(unittest.TestCase):
    def test_views_own_their_legs(self):
        app = read_web("app.js")
        const = app[app.index("const VIEW_MODES"):
                    app.index("function setPill")]
        for marker in ('home: [],',
                       'bay: ["bayIntake", "bayPlan"],',
                       'inventory: ["intake", "harvest", "comps", "listing"],',
                       'compare: ["compare"],'):
            self.assertIn(marker, const, marker)

    def test_view_switch_repaints_pill(self):
        app = read_web("app.js")
        view = fn_body(app, "showView", "const VIEW_PAGES")
        self.assertIn("setPill();", view)

    def test_compare_run_records_its_mode(self):
        app = read_web("app.js")
        fn = fn_body(app, "runCompare", "function refreshListingParts")
        self.assertIn("state.modes.compare = res.modeOpen", fn)


if __name__ == "__main__":
    unittest.main()
