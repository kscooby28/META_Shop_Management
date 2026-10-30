"""Sex-appeal tests (WO19): modern website looks, same product underneath.

Presentation only. Every element the Step 0 audit named as still-plain
has a test proving it changed; every element named as already-modern
has a test proving it did not regress. Type sizes and corner radii live
in tokens like colors already do; amber means money and the primary
action and nothing else; sunlight mode stays fully solid; no new
motion, no new navigation, no invented data.
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


def root_tokens():
    return css().partition(":root")[2].partition("}")[0]


def sunlight_block():
    plain = css_no_comments()
    start = plain.index("body.sunlight {")
    end = plain.index("@media (min-width: 900px)", start)
    return plain[start:end]


def keyframe_names():
    return set(re.findall(r"@keyframes\s+([\w-]+)", css_no_comments()))


def rule_body(selector):
    plain = css_no_comments()
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", plain)
    assert match, "missing rule " + selector
    return match.group(1)


TEXT_TOKENS = {"--text-display", "--text-title", "--text-body", "--text-meta"}
RADIUS_TOKENS = {"--radius-small", "--radius-card", "--radius-pill",
                 "--radius-round"}
SUN_TOKENS = {"--sun-ui", "--sun-meta", "--sun-base"}


class TypeScaleTest(unittest.TestCase):
    def test_four_sizes_and_values(self):
        root = root_tokens()
        for token, value in (("--text-display", "2rem"),
                             ("--text-title", "1.25rem"),
                             ("--text-body", "1rem"),
                             ("--text-meta", "0.8rem")):
            self.assertIn("%s: %s;" % (token, value), root, token)

    def test_radii_tokens_and_values(self):
        root = root_tokens()
        for token, value in (("--radius-small", "8px"),
                             ("--radius-card", "12px"),
                             ("--radius-pill", "999px"),
                             ("--radius-round", "50%")):
            self.assertIn("%s: %s;" % (token, value), root, token)

    def test_every_font_size_is_a_token(self):
        for value in re.findall(r"font-size:\s*([^;]+);", css_no_comments()):
            refs = set(re.findall(r"--[\w-]+", value))
            self.assertTrue(refs, value)
            self.assertEqual(refs - TEXT_TOKENS - SUN_TOKENS, set(), value)

    def test_every_corner_is_a_token(self):
        for value in re.findall(r"border-radius:\s*([^;]+);",
                                css_no_comments()):
            refs = set(re.findall(r"--[\w-]+", value))
            self.assertTrue(refs, value)
            self.assertEqual(refs - RADIUS_TOKENS, set(), value)

    def test_four_sizes_maximum(self):
        used = set()
        for value in re.findall(r"font-size:\s*([^;]+);", css_no_comments()):
            used.update(re.findall(r"--[\w-]+", value))
        self.assertEqual(used - SUN_TOKENS, TEXT_TOKENS)

    def test_no_inline_font_size(self):
        for name in ("index.html", "app.js", "profile.js", "inventory.js",
                     "gallery.js", "ux.js", "credentials.js"):
            self.assertNotIn("font-size", read(name), name)


class AccentDisciplineTest(unittest.TestCase):
    DEAMBERED = ("button.photo", ".offlinebar", ".guide",
                 ".strip figure.sel img", ".progress > div", ".msg.user",
                 ".gatebadge", ".moved-flash", ".moved-note", ".mode-tag",
                 ".confirm-frame", ".navbtn.active", ".pill.demo",
                 ".door:hover", ".grade-B", ".totalcard.total-b")

    def test_amber_only_money_and_primary(self):
        plain = css_no_comments()
        self.assertEqual(plain.count("var(--accent)"), 5)
        self.assertEqual(plain.count("var(--accent-ink)"), 1)
        for selector in ("button.primary", ".totalcard .big", ".money",
                         ".big-money"):
            self.assertIn("var(--accent)", rule_body(selector), selector)

    def test_deambered_sites_stay_neutral(self):
        for selector in self.DEAMBERED:
            self.assertNotIn("var(--accent", rule_body(selector), selector)

    def test_success_and_decline_keep_own_colors(self):
        self.assertIn("var(--grade-a)", rule_body(".confirm-done"))
        self.assertIn("2px solid var(--ink)", rule_body(".decline"))
        self.assertIn("var(--grade-a)", rule_body(".testcard.doneok"))
        self.assertIn("var(--grade-c)", rule_body(".testcard.donefail"))


class ContrastTest(unittest.TestCase):
    @staticmethod
    def luminance(hexcode):
        code = hexcode.lstrip("#")
        rgb = [int(code[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
               for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    @classmethod
    def ratio(cls, fore, back):
        lighter = max(cls.luminance(fore), cls.luminance(back))
        darker = min(cls.luminance(fore), cls.luminance(back))
        return (lighter + 0.05) / (darker + 0.05)

    def tokens(self):
        return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})",
                               root_tokens()))

    def test_body_text_contrast(self):
        tok = self.tokens()
        for fore in ("ink", "muted"):
            for back in ("bg", "surface", "paper"):
                self.assertGreaterEqual(
                    self.ratio(tok[fore], tok[back]), 4.5,
                    "%s on %s" % (fore, back))

    def test_sunlight_and_primary_contrast(self):
        tok = self.tokens()
        for fore in ("sun-ink", "sun-muted"):
            for back in ("sun-bg", "sun-surface", "sun-paper"):
                self.assertGreaterEqual(
                    self.ratio(tok[fore], tok[back]), 4.5,
                    "%s on %s" % (fore, back))
        self.assertGreaterEqual(
            self.ratio(tok["accent-ink"], tok["accent"]), 4.5, "primary")


class SunlightSolidTest(unittest.TestCase):
    def test_no_translucency_blur_or_thin_type(self):
        block = sunlight_block()
        self.assertNotIn("rgba", block)
        self.assertNotIn("hsla", block)
        self.assertNotIn("blur", block)
        for value in re.findall(r"opacity:\s*([\d.]+)", block):
            self.assertEqual(float(value), 1.0)
        for weight in re.findall(r"font-weight:\s*(\d+)", block):
            self.assertGreaterEqual(int(weight), 600)


class HeroTest(unittest.TestCase):
    # WO20 supersedes the strip hero with the landing scene: the scene is
    # illustration (SVG, never a photo), the demo frames leave the home
    # view, and the entrances carry the doors below the scene.
    def test_home_landing_scene(self):
        html = read("index.html")
        home = html[html.index('id="view-home"'):html.index('id="view-yard"')]
        scene = home[home.index('<div class="scene"'):home.index('id="btnHomePhoto"')]
        self.assertNotIn("<svg", scene)
        self.assertIn("<img", scene)
        self.assertIn("Illustrated shop street", scene)
        self.assertNotIn("demo/frame", home)
        self.assertNotIn("http", scene)
        self.assertLess(home.index("screen-line"), home.index('<div class="scene"'))
        self.assertLess(home.index('<div class="scene"'),
                        home.index('class="tilegrid entrances"'))

    def test_scene_css_exists(self):
        self.assertIn("display: block", rule_body(".backdrop"))
        self.assertIn("var(--radius-card)", rule_body(".backdrop"))
        self.assertIn("6.5rem", rule_body(".doorart"))


class MoneyTest(unittest.TestCase):
    def test_price_tag_totals(self):
        big = rule_body(".totalcard .big")
        self.assertIn("var(--text-display)", big)
        self.assertIn("var(--accent)", big)
        self.assertIn("800", big)
        mine = rule_body(".big-money")
        self.assertIn("var(--text-display)", mine)
        self.assertIn("var(--accent)", mine)
        self.assertIn("var(--accent)", rule_body(".money"))

    def test_money_wrapped_after_escape(self):
        app = read("app.js")
        self.assertIn("function amberMoney(escText)", app)
        self.assertIn('<span class="money">', app)
        for call in ("amberMoney(esc(totals.A.plain_words))",
                     "amberMoney(esc(inp.money_grade",
                     "amberMoney(esc(money(inp.price_low)"):
            self.assertIn(call, app, call)

    def test_shop_rate_money_coded(self):
        self.assertIn('<span class="money">$180</span>', read("index.html"))

    def test_no_new_literal_money_amounts_in_js(self):
        # Audited baseline, all honest: "$0" is a computed zero-total
        # display, "$180" the real shop rate in a log line, "$200" tour
        # narrative. Any new literal would be an invented number.
        for name in ("profile.js", "inventory.js", "gallery.js", "ux.js",
                     "credentials.js"):
            self.assertEqual(
                re.findall(r"\$[0-9][\d,]*(?:\.\d+)?", read(name)), [], name)
        self.assertEqual(
            sorted(set(re.findall(r"\$[0-9][\d,]*(?:\.\d+)?",
                                  read("app.js")))),
            ["$0", "$180", "$200"])

    def test_unknown_stays_styled_unknown(self):
        self.assertIn("var(--grade-c)", rule_body(".missing"))
        app = read("app.js")
        for literal in ("no reliable price", "value unknown"):
            self.assertIn(literal, app, literal)


class DensityRowsTest(unittest.TestCase):
    def test_inventory_rows_disclose_details(self):
        app = read("app.js")
        self.assertIn('more.className = "rowmore";', app)
        self.assertIn("Condition and note", app)
        self.assertIn('<details class="rowmore"><summary>Sources</summary>', app)
        self.assertIn("flex-basis: 100%", rule_body(".rowmore"))

    def test_harvest_rows_are_not_paragraphs(self):
        app = read("app.js")
        self.assertNotIn("<span>count: ", app)
        self.assertIn("condition: ", app)  # the one contextual field stays
        self.assertIn(".part-list .thumb", css_no_comments())
        self.assertIn("96px", rule_body(".part-list .thumb"))


class StatusGlyphTest(unittest.TestCase):
    def test_status_is_icon_plus_word(self):
        app = read("app.js")
        for glyph in ("✓ PASS", "✕ FAIL", "○ PENDING"):
            self.assertIn(glyph, app, glyph)
        self.assertIn("RULED OUT", app)
        self.assertIn("line-through",
                      rule_body(".testcard.eliminated .tname"))


class PhotoIdentityTest(unittest.TestCase):
    def test_bay_case_leads_with_car_photo(self):
        app = read("app.js")
        self.assertIn('class="casephoto"', app)
        self.assertIn("bay.vinPhoto.data", app)
        self.assertIn("object-fit: cover", rule_body(".casephoto"))

    def test_part_thumbs_replace_inline_style(self):
        app = read("app.js")
        self.assertIn("grade grade-sm grade-", app)
        self.assertIn("var(--text-meta)", rule_body(".grade-sm"))


class CompareHeadTest(unittest.TestCase):
    def test_compare_head_has_hierarchy(self):
        self.assertIn('head.className = "compare-head";', read("app.js"))
        self.assertIn("var(--text-title)", rule_body(".compare-head"))


class SettingsCardTest(unittest.TestCase):
    def test_profile_controls_grouped_in_card(self):
        app = read("app.js")
        self.assertIn('card.className = "gcard homehead";', app)
        self.assertIn("demoCard.appendChild(walk);", app)
        self.assertIn("flex-basis: 100%",
                      rule_body("#settingsBody .homehead"))


class ChipsTest(unittest.TestCase):
    def test_chips_are_tappable_cards(self):
        chips = rule_body("#chips")
        self.assertIn("flex-direction: column", chips)
        button = rule_body("#chips button")
        self.assertIn("var(--text-body)", button)
        self.assertIn("width: 100%", button)
        self.assertIn("var(--radius-card)", button)


class EmptyStatesTest(unittest.TestCase):
    def test_photo_contexts_show_own_frames(self):
        app = read("app.js")
        self.assertIn("gallery: \"demo/frame1.svg\"", app)
        self.assertIn("parts: \"demo/frame2.svg\"", app)
        self.assertIn("verdicts: \"demo/frame3.svg\"", app)
        self.assertIn(".emptybox img", css_no_comments())

    def test_empty_card_is_designed(self):
        box = rule_body(".emptybox")
        self.assertIn("1px solid var(--line)", box)
        self.assertNotIn("dashed", box)
        self.assertIn("var(--text-title)", rule_body(".emptybox .etitle"))


class HairlineTest(unittest.TestCase):
    HAIRLINE = "box-shadow: inset 0 1px 0 var(--line);"

    def test_cards_carry_one_hairline(self):
        plain = css_no_comments()
        self.assertGreaterEqual(plain.count(self.HAIRLINE.strip(";")), 12)
        for selector in (".work section", ".door", ".verdict", ".testcard",
                         ".invcar", ".decline", ".totalcard"):
            self.assertIn("inset 0 1px 0 var(--line)",
                          rule_body(selector), selector)

    def test_no_new_drop_shadows(self):
        for value in re.findall(r"box-shadow:\s*([^;]+);", css_no_comments()):
            self.assertIn(value.strip(),
                          ("inset 0 1px 0 var(--line)",
                           "-4px 0 16px var(--shadow)"))


class NoNewMotionTest(unittest.TestCase):
    def test_keyframes_set_unchanged(self):
        self.assertEqual(keyframe_names(),
                         {"slidein-right", "slidein-left", "doorfade",
                          "sheetup", "movedflash", "skelpulse", "fadein"})

    def test_no_new_easings(self):
        plain = css_no_comments()
        outside = plain.partition("}")[2]
        self.assertNotIn("cubic-bezier(", outside)

    def test_no_linear_motion(self):
        for value in re.findall(r"(?:transition|animation):\s*([^;]+);",
                                css_no_comments()):
            self.assertNotIn("linear", value)


class LeftAloneTest(unittest.TestCase):
    """Audit findings marked already-modern: prove zero regression."""

    def test_doors_structure_kept(self):
        # WO20: doors are graphical entrances (art on top, labels below);
        # ids, routing, words, and the ink hover all stand.
        door = rule_body(".door")
        for_keep = ("display: flex;", "flex-direction: column;",
                    "min-height: 12rem;", "2px solid var(--line);",
                    "overflow: hidden;")
        for text in for_keep:
            self.assertIn(text, door, text)
        self.assertIn("border-color: var(--ink);",
                      rule_body(".door:hover"))
        self.assertIn("var(--text-title)", rule_body(".door-name"))
        self.assertIn("var(--text-body)", rule_body(".door-why"))

    def test_grade_pills_kept(self):
        self.assertIn(".grade-A { background: var(--grade-a); }",
                      css_no_comments())
        self.assertIn(".grade-B { background: var(--grade-b); }",
                      css_no_comments())
        self.assertIn(".grade-C { background: var(--grade-c); }",
                      css_no_comments())

    def test_gallery_viewer_kept(self):
        self.assertIn("aspect-ratio: 1 / 1;",
                      rule_body(".viewer .imgwrap"))
        for part in ("A", "B", "C"):
            self.assertIn(".overlay g.part-%s polygon" % part,
                          css_no_comments())

    def test_verdict_override_kept(self):
        self.assertIn("data-override", read("app.js"))
        self.assertIn(".override-row", css_no_comments())

    def test_confirm_frame_still_dashed(self):
        self.assertIn("2px dashed", rule_body(".confirm-frame"))

    def test_view_transitions_still_wired(self):
        self.assertIn("playViewTransition(document.querySelector",
                      read("app.js"))

    def test_tour_bar_kept(self):
        self.assertIn('bar.className = "homehead";', read("app.js"))

    def test_decline_and_setup_kept(self):
        self.assertIn("2px solid var(--ink)", rule_body(".decline"))
        self.assertIn("z-index: 100", rule_body("#setupOverlay"))

    def test_listing_and_labor_inputs_kept(self):
        self.assertIn('id="listingTitle"', read("index.html"))
        self.assertIn("bayLaborFromInputs", read("app.js"))

    def test_copilot_header_kept(self):
        self.assertIn("never guess", read("index.html"))

    def test_hero_not_reclassified(self):
        tag = re.search(r'<button[^>]*id="btnHomePhoto"[^>]*>',
                        read("index.html")).group(0)
        self.assertNotIn("primary", tag)
        self.assertIn("photo herophoto", tag)

    def test_sunlight_and_guides_still_wired(self):
        app = read("app.js")
        for marker in ('$("navSun")', '"sunToggle"', "paintShotGuide(btnId",
                       "UX.transitionFor(from, which)"):
            self.assertIn(marker, app, marker)


if __name__ == "__main__":
    unittest.main()
