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


if __name__ == "__main__":
    unittest.main()
