"""Submission-fix pins: judges-panel corrections, frozen against drift.

Each test pins one correction from the pre-freeze critique pass:
honest words, working header/landing, MIME types, the --host flag,
the permissive tour voice, and the video plan. Static pins run
offline; live behavior stays an owner/braubus smoke proof.
"""

import json
import os
import re
import unittest

import server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_web(name):
    with open(os.path.join(ROOT, "web", name), encoding="utf-8") as fh:
        return fh.read()


def read_root(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def tour_says():
    app = read_web("app.js")
    return dict(re.findall(r'(\w+): \{ hold: \d+, say: "([^"]+)" \},',
                           app))


class AssetHonestyTest(unittest.TestCase):
    def test_asset_refs_exist(self):
        refs = set(re.findall(r'assets/[A-Za-z0-9_.\-/]+',
                              read_web("index.html")))
        refs |= set(re.findall(r'"(assets/[A-Za-z0-9_.\-/]+)"',
                               read_web("app.js")))
        self.assertTrue(refs)
        for ref in sorted(refs):
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT, "web", ref)), ref)

    def test_no_real_sold_in_web_or_voice(self):
        for name in ("app.js", "index.html", "ux.js", "profile.js",
                     "inventory.js", "gallery.js", "credentials.js",
                     "styles.css"):
            self.assertNotIn("real sold", read_web(name), name)
        man = read_root("eval_voice_results.json")
        self.assertNotIn("real sold", man)
        self.assertIn("sample sold ranges", read_web("app.js"))

    def test_captions_match_narration(self):
        app = read_web("app.js")
        beats = re.findall(
            r'\{ id: "(\w+)", view: [^,]+, section: [^,]+,'
            r' title: "[^"]+",\s+line: "([^"]+)" \},', app)
        self.assertEqual(len(beats), 8)
        says = tour_says()
        for beat_id, line in beats:
            self.assertEqual(line, says[beat_id], beat_id)


class CompareHonestyTest(unittest.TestCase):
    def test_no_model_name_on_rules_math(self):
        app = read_web("app.js")
        self.assertNotIn("Muse Spark 1.3", app)
        self.assertIn("Money grade (rules engine)", app)


class BackendCopyTest(unittest.TestCase):
    BANNED = ("Gulf Coast", "Gulf-Coast", "Ocean Springs",
              "Mississippi", "braubus")

    def test_no_region_or_internal_names_in_backend(self):
        for name in ("meta_client.py", "server.py"):
            text = read_root(name)
            for banned in self.BANNED:
                self.assertNotIn(banned, text, "%s in %s"
                                 % (banned, name))

    def test_chat_side_words_are_current(self):
        text = read_root("server.py")
        for old in ("Yard results on screen", "Driveway on screen",
                    "From the Yard results", "From your Driveway",
                    "Driveway shows", "Driveway is empty",
                    "Driveway prices on screen"):
            self.assertNotIn(old, text, old)
        for new in ("Results on screen", "DIY Garage on screen",
                    "From your DIY Garage"):
            self.assertIn(new, text, new)

    def test_rotation_copy_is_current(self):
        text = read_root("server.py")
        self.assertNotIn("until the key rotation", text)
        self.assertNotIn("rotation is confirmed", text)
        self.assertIn("in this demo build", text)


class ServerConfigTest(unittest.TestCase):
    def test_content_types_cover_media(self):
        types = server.CONTENT_TYPES
        self.assertEqual(types[".mp3"], "audio/mpeg")
        self.assertEqual(types[".png"], "image/png")
        self.assertEqual(types[".jpg"], "image/jpeg")
        self.assertEqual(types[".jpeg"], "image/jpeg")

    def test_host_flag_parsed(self):
        text = read_root("server.py")
        main = text[text.index('if __name__ == "__main__":'):]
        self.assertIn("--host=", main)
        self.assertIn('re.match(r"--host=', main)
        self.assertIn('host = "127.0.0.1"', main)


class LandingHeaderTest(unittest.TestCase):
    def test_side_chip_unhides_settings(self):
        app = read_web("app.js")
        at = app.index('$("sideChip").addEventListener')
        handler = app[at:at + 400]
        self.assertIn('$("settings").hidden = false', handler)
        self.assertLess(
            handler.index('$("settings").hidden = false'),
            handler.index('$("settings").open = true'))

    def test_setup_hint_wired(self):
        html = read_web("index.html")
        self.assertIn('id="setupHint"', html)
        app = read_web("app.js")
        self.assertIn("function setupHint(msg)", app)
        self.assertIn("setupHint(err.message)", app)

    def test_pill_hidden_when_empty(self):
        app = read_web("app.js")
        fn = app[app.index("function setPill("):
                 app.index("function setPill(") + 700]
        self.assertIn("pill.hidden = true", fn)
        self.assertNotIn('"not started"', fn)

    def test_zone_focus_outline_ink(self):
        css = read_web("styles.css")
        at = css.index(".door.zone:focus-visible")
        rule = css[at:at + 200]
        self.assertIn("3px solid var(--ink)", rule)
        self.assertNotIn("var(--accent", rule)


class VoiceManifestTest(unittest.TestCase):
    def test_manifest_matches_says(self):
        with open(os.path.join(ROOT, "eval_voice_results.json"),
                  encoding="utf-8") as fh:
            man = json.load(fh)
        self.assertEqual(man["voice"], "en_US-libritts-high")
        self.assertIn("CC BY 4.0", man["voice_license"])
        says = tour_says()
        self.assertEqual([f["beat"] for f in man["files"]],
                         list(says.keys()))
        for f in man["files"]:
            self.assertEqual(f["line"], says[f["beat"]], f["beat"])


class ReadmeFixesTest(unittest.TestCase):
    def test_audio_provenance_named(self):
        text = read_root("README.md")
        for phrase in ("Piper", "en_US-libritts-high", "CC BY 4.0",
                       "build time", "tour-*.mp3"):
            self.assertIn(phrase, text, phrase)

    def test_sam_step_qualified(self):
        text = read_root("README.md")
        self.assertIn("stands in for SAM", text)
        self.assertNotIn("SAM 3.1 masks each grounded part", text)

    def test_hybrid_rotation_current(self):
        text = read_root("README.md")
        hybrid = text[text.index("## Hybrid architecture"):
                      text.index("## Credentials")]
        self.assertNotIn("rotation is confirmed", hybrid)
        self.assertIn("demo build", hybrid)
        self.assertIn("22/30", hybrid)

    def test_run_it_names_phone_and_verify(self):
        text = read_root("README.md")
        run = text[text.index("## Run it"):text.index("## The flow")]
        for phrase in ("python3", "--host=0.0.0.0",
                       "python -m unittest",
                       "python scripts/smoke_demo.py", "Node.js"):
            self.assertIn(phrase, run, phrase)


class VideoPlanTest(unittest.TestCase):
    def test_plan_exists_with_checklist(self):
        with open(os.path.join(ROOT, "docs", "video-plan.md"),
                  encoding="utf-8") as fh:
            plan = fh.read()
        for phrase in ("tour.muted", "outro", "180",
                       "Take the tour", "Approve", "dry run",
                       "Force offline", "snap"):
            self.assertIn(phrase, plan, phrase)


class CssTokenTest(unittest.TestCase):
    def test_no_size_token_as_color(self):
        css = read_web("styles.css")
        self.assertNotIn("color: var(--text-", css)


if __name__ == "__main__":
    unittest.main()
