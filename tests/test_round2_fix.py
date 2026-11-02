"""Round-2 pins: photo AI takeover, shop honesty, why-B answers,
video links, sheet scaling. Offline; live behavior stays a smoke proof."""

import io
import json
import os
import re
import unittest
from unittest import mock

import server
from server import Handler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_web(name):
    with open(os.path.join(ROOT, "web", name), encoding="utf-8") as fh:
        return fh.read()


class FakeSelf:
    def __init__(self):
        self.sent = None
        self.status = 200

    def _send_json(self, payload, status=200):
        self.sent = payload
        self.status = status

    def _bay_plan_view(self, plan):
        return Handler._bay_plan_view(None, plan)

    def _bay_session(self, payload):
        return Handler._bay_session(None, payload)


def demo_verdict_session():
    from verdict import evaluate, load_rules

    def load(name):
        with open(os.path.join(ROOT, "demo_cache", name),
                  encoding="utf-8") as fh:
            return json.load(fh)

    harvest = load("harvest.demo.json")
    comps = load("comps.demo.json")
    rules = load_rules(os.path.join(ROOT, "rules.json"))
    return {"harvest": harvest, "comps": comps,
            "verdicts": evaluate(harvest["parts"], rules, comps)}


class WhyBAnswerTest(unittest.TestCase):
    def test_names_part_rule_and_margin(self):
        why = Handler._local_chat_answer(
            None, demo_verdict_session(), "Why is this part a B?")
        for phrase in ("headlight", "1 frame", "needs 2",
                       "condition intact", "price $75"):
            self.assertIn(phrase, why, phrase)
        self.assertNotIn("frame(s)", why)
        self.assertNotIn("75.0", why)

    def test_miss_returns_no_lecture(self):
        out = Handler._local_chat_answer(
            None, demo_verdict_session(), "Why did the job stall?")
        self.assertNotIn("is B (", out)

    def test_low_only_price_no_crash(self):
        session = {"verdicts": {"verdicts": [{
            "label": "driver mirror", "verdict": "B",
            "verdict_means": "worth pulling",
            "rule_name": "r_worth_it_seen",
            "rule_explain": "seen enough to trust",
            "inputs": {"intact": "yes", "frames_seen": 1,
                       "demand": "high", "price_low": 45.0,
                       "price_high": None, "price_known": True}}]}}
        why = Handler._local_chat_answer(
            None, session, "Why is this part a B?")
        self.assertIn("price $45", why)

    def test_no_session_non_b_names_grades(self):
        ctx = {"yard": {"verdicts": [{"label": "x", "grade": "A"}]}}
        out = Handler._local_chat_answer(
            None, None, "Why is this part a B?", ctx)
        self.assertIn("No B parts on screen", out)

    def test_named_non_b_says_so(self):
        out = Handler._local_chat_answer(
            None, demo_verdict_session(), "Why is the mirror a B?")
        self.assertIn("is A, not B", out)

    def test_summary_plain_inputs(self):
        text = Handler._case_summary(None, demo_verdict_session())
        self.assertIn("condition intact", text)
        self.assertIn("price $75", text)
        self.assertNotIn("75.0", text)
        self.assertNotIn("intact=", text)


class ManualFallbackTest(unittest.TestCase):
    def test_inv_identify_manual(self):
        from meta_client import MetaAPIError

        fake = FakeSelf()
        with mock.patch("server.identify_car",
                        side_effect=MetaAPIError("down",
                                                kind="unreachable")):
            Handler._api_inv_identify(
                fake, {"photo": {"name": "p.jpg", "dataUrl": "x"}})
        self.assertTrue(fake.sent["ok"])
        self.assertEqual(fake.sent["mode"], "manual")
        self.assertEqual(fake.sent["car"]["year"], "unknown")
        self.assertIn("unreachable", fake.sent["notice"])
        self.assertIn("by hand", fake.sent["notice"])

    def test_inv_identify_missing_key_named(self):
        from meta_client import MetaAPIError

        fake = FakeSelf()
        with mock.patch(
                "server.identify_car",
                side_effect=MetaAPIError("no API key in local .env",
                                         kind="auth")):
            Handler._api_inv_identify(
                fake, {"photo": {"name": "p.jpg", "dataUrl": "x"}})
        self.assertIn("No API key found", fake.sent["notice"])

    def test_bay_plan_manual_names_kind(self):
        from meta_client import MetaAPIError

        server.put_session("t-manual", {"bay": {
            "case": {"case_id": "c1", "declined": False},
            "plan": None, "modes": {}}})
        fake = FakeSelf()
        with mock.patch("server.draft_plan",
                        side_effect=MetaAPIError("down",
                                                kind="unreachable")):
            Handler._api_bay_plan(fake, {"sessionId": "t-manual"})
        self.assertEqual(fake.sent["mode"], "manual")
        self.assertIn("unreachable", fake.sent["notice"])
        self.assertIn("by hand", fake.sent["notice"])
        self.assertEqual(fake.sent["plan"]["tests"], [])

    def test_bay_plan_live_stub(self):
        fake = FakeSelf()
        server.put_session("t-live", {"bay": {
            "case": {"case_id": "c2", "declined": False},
            "plan": None, "modes": {}}})
        with mock.patch("server.draft_plan",
                        return_value=[{"title": "Coil swap"}]):
            Handler._api_bay_plan(fake, {"sessionId": "t-live"})
        self.assertEqual(fake.sent["mode"], "live")
        self.assertEqual(fake.sent["notice"], "")
        self.assertEqual(len(fake.sent["plan"]["tests"]), 1)

    def test_bay_plan_demo_never_calls_live(self):
        fake = FakeSelf()
        server.put_session("t-demo", {"bay": {
            "case": {"case_id": "c3", "declined": False},
            "plan": None, "demo_case": "case1", "modes": {}}})
        with mock.patch("server.draft_plan",
                        side_effect=AssertionError("live called")):
            Handler._api_bay_plan(fake, {"sessionId": "t-demo"})
        self.assertEqual(fake.sent["mode"], "demo-cache")

    def test_bay_intake_manual_mode(self):
        fake = FakeSelf()
        Handler._api_bay_intake(fake, {"manual": {
            "vehicle": {"year": "2006", "make": "BMW",
                        "model": "325i"},
            "symptom": "rough idle", "codes": []}})
        self.assertEqual(fake.sent["mode"], "manual-entry")
        self.assertIn("Manual entry", fake.sent["notice"])


class ImageTimeoutTest(unittest.TestCase):
    def test_budgets(self):
        import meta_client

        self.assertEqual(meta_client.IMAGE_TIMEOUT_SECONDS, 60)
        self.assertEqual(meta_client.TIMEOUT_SECONDS, 12)

    def test_identify_uses_image_budget(self):
        import meta_client
        from meta_client import MetaAPIError

        seen = {}

        class Resp:
            status = 200

            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content":
                        '{"car": {}, "parts": []}'}}]}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=None):
            seen["timeout"] = timeout
            return Resp()

        with mock.patch("meta_client._api_key", return_value="k"), \
                mock.patch("urllib.request.urlopen", fake_urlopen):
            meta_client.identify_car([{"name": "p.jpg",
                                       "dataUrl": "data:,x"}])
        self.assertEqual(seen["timeout"], 60)

    def test_image_legs_carry_budget_text_legs_do_not(self):
        with open(os.path.join(ROOT, "meta_client.py"),
                  encoding="utf-8") as fh:
            src = fh.read()

        def body(name):
            start = src.index("def %s(" % name)
            nxt = src.find("\ndef ", start + 1)
            return src[start:nxt if nxt > 0 else len(src)]

        for name in ("identify_car", "read_vin_photo",
                     "describe_part", "segment_parts"):
            self.assertIn("IMAGE_TIMEOUT_SECONDS", body(name),
                          name)
        self.assertNotIn("IMAGE_TIMEOUT_SECONDS",
                         body("draft_plan"))


class PhotoResultHangTest(unittest.TestCase):
    def test_result_always_lands(self):
        app = read_web("app.js")
        fn = app[app.index("async function identifyInvCarPhotoResult"):
                 app.index("function renderNetworkFeed")]
        self.assertIn("try {", fn)
        self.assertIn("catch (err) {", fn)
        self.assertIn("finishPhotoResult(photo, car || {});", fn)
        self.assertLess(fn.index("catch (err) {"),
                        fn.index("finishPhotoResult(photo, car || {});"))
        self.assertIn("demo: state.forceDemo",
                      app[app.index("async function identifyInvCarPhoto("):
                          app.index("async function identifyInvCarPhotoStaged")])


class ModePillTest(unittest.TestCase):
    def test_hidden_until_modes_exist(self):
        with open(os.path.join(ROOT, "web", "index.html"),
                  encoding="utf-8") as fh:
            html = fh.read()
        tag = re.search(r'<span[^>]*id="modePill"[^>]*>',
                        html).group(0)
        self.assertIn("hidden", tag)
        self.assertNotIn("not started", html)
        fn = read_web("app.js")
        fn = fn[fn.index("function setPill("):fn.index("function setPill(") + 700]
        self.assertIn('"manual-entry"', fn)


class VideoLinksTest(unittest.TestCase):
    def test_helpers_and_placements(self):
        app = read_web("app.js")
        self.assertIn("function ytLink(query, label)", app)
        self.assertIn("function ytSection(title, links)", app)
        self.assertIn("youtube.com/results?search_query=", app)
        self.assertIn('target="_blank" rel="noopener"', app)
        self.assertIn("not our picks", app)
        plan = app[app.index("function renderBayPlan"):
                   app.index("function renderBayTrail")]
        self.assertIn('"Fix-it videos"', plan)
        verdicts = app[app.index("function renderVerdicts"):
                       app.index("async function runVerdicts")]
        self.assertIn('"Pull-it videos"', verdicts)
        css = read_web("styles.css")
        self.assertIn(".ytlink", css)
        self.assertIn("min-height: 48px", css)


class SheetScaleTest(unittest.TestCase):
    def test_sheet_holds_together(self):
        css = read_web("styles.css")
        self.assertIn("min-height: 0", css)
        self.assertIn("#chatForm input { flex: 1; min-width: 0; }", css)
        self.assertNotIn("translateX(100%)", css)


class ChatSystemTest(unittest.TestCase):
    def test_two_door_voice(self):
        from meta_client import CHAT_SYSTEM

        self.assertIn("two-door", CHAT_SYSTEM)
        self.assertIn("Never guess", CHAT_SYSTEM)


if __name__ == "__main__":
    unittest.main()
