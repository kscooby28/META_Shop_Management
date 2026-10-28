"""Muse Image studio tests (WO7 phase 1): demo composites, fallback, flag off."""

import json
import os
import unittest

import server
import studio
from demo_cache import StepCache
from meta_client import MetaAPIError
from server import Handler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def harvest_part(part_id):
    parts = StepCache(ROOT).load_demo("harvest")["parts"]
    return next(p for p in parts if p["id"] == part_id)


class StudioDemoTest(unittest.TestCase):
    def test_live_flag_off(self):
        self.assertFalse(studio.IMAGE_LIVE)

    def test_live_refuses_without_network(self):
        with self.assertRaises(MetaAPIError) as ctx:
            studio.request_studio_render("data:image/png;base64,xx", "diff")
        self.assertIn("key rotation", str(ctx.exception))

    def test_live_refuses_without_cutout_even_if_flagged(self):
        real, studio.IMAGE_LIVE = studio.IMAGE_LIVE, True
        try:
            with self.assertRaises(MetaAPIError) as ctx:
                studio.request_studio_render("", "diff")
            self.assertEqual(ctx.exception.kind, "bad_response")
        finally:
            studio.IMAGE_LIVE = real

    def test_composite_is_deterministic(self):
        with open(os.path.join(ROOT, "web", "demo", "frame4.svg"), encoding="utf-8") as fh:
            frame = fh.read()
        first = studio.composite_svg(frame, [300, 360, 700, 570], "differential")
        second = studio.composite_svg(frame, [300, 360, 700, 570], "differential")
        self.assertEqual(first, second)
        self.assertIn('viewBox="300 360 400 210"', first)
        self.assertIn("differential", first)
        self.assertNotIn("<script", first.lower())

    def test_cache_hit_is_source_tagged(self):
        part = harvest_part("p_diff")
        cut = Handler._cutout_spec(None, part)
        found = studio.demo_lookup("p_diff", cut, ROOT, part["label"])
        self.assertEqual(found["kind"], "svg")
        self.assertIn("demo-cache", found["source"])
        self.assertIn("Studio photo", found["note"])

    def test_cache_miss_builds_from_demo_frame(self):
        part = harvest_part("p_diff")
        cut = Handler._cutout_spec(None, part)
        found = studio.demo_lookup("p_not_cached", cut, ROOT, part["label"])
        self.assertIsNotNone(found)
        self.assertIn("built", found["source"])

    def test_no_box_means_fallback(self):
        self.assertIsNone(studio.demo_lookup("p_x", {"box": None}, ROOT))
        self.assertIsNone(studio.demo_lookup("p_x", {}, ROOT))

    def test_samples_cover_every_demo_part(self):
        with open(os.path.join(ROOT, "demo_cache", "studio.demo.json"), encoding="utf-8") as fh:
            samples = json.load(fh)["samples"]
        ids = [p["id"] for p in StepCache(ROOT).load_demo("harvest")["parts"]]
        self.assertEqual(sorted(samples), sorted(ids))


class FakeHandler:
    _bay_session = Handler._bay_session
    _cutout_spec = Handler._cutout_spec

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


class StudioListingTest(unittest.TestCase):
    def _session_with_harvest(self):
        sid = server.new_session_id()
        server.put_session(sid, {"harvest": StepCache(ROOT).load_demo("harvest")})
        return sid

    def test_yard_draft_carries_studio(self):
        fake = FakeHandler()
        sid = self._session_with_harvest()
        Handler._api_listing(fake, {"sessionId": sid, "partId": "p_diff"})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "demo-cache")
        self.assertTrue(body["studio"]["body"].startswith("<svg"))
        self.assertIn("demo-cache", body["studio"]["source"])
        self.assertTrue(body["cutout"]["box"])  # fallback still present

    def test_inventory_draft_falls_back_cleanly(self):
        fake = FakeHandler()
        Handler._api_listing(
            fake,
            {
                "demo": True,
                "invPart": {"id": "ip-x", "label": "knob", "value": None,
                            "valueSource": ""},
                "invCar": {},
            },
        )
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertIsNone(body["studio"])


if __name__ == "__main__":
    unittest.main()
