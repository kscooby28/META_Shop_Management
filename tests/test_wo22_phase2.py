"""WO22 Phase 2 pins: proven Meta legs go live when keys are present.

2.1 one switch (SHOP_DEMO=1 + per-leg live_enabled, proven defaults,
    voice/VIN stay off); 2.2 Spark-grounding harvest, no car swap, SAM
    out of the live path; 2.3 live listing drafts on yard + inventory
    paths; 2.4 Wonder live second opinion with ms; 2.5 inventory
    Compare; 2.6 studio gate (demo until a live image-edit call with
    real cutout bytes succeeds); 2.7 live chips + /api/health legs;
    2.8 live Bay plan through the same ranking + honest Moved: trail.

No test here touches the network: live legs are stubbed in-process and
every refusal test patches its gate shut.
"""

import os
import shutil
import unittest

import server
import spark_open
import studio
import voice
import wonder
from bay import build_case, load_bay_case, new_plan, record_result
from comps import get_adapter as get_comps_adapter
from demo_cache import StepCache
from meta_client import MetaAPIError, demo_forced, spark_grounding_harvest
from server import Handler
from verdict import evaluate, load_rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_root(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


class FakeHandler:
    _bay_session = Handler._bay_session
    _cutout_spec = Handler._cutout_spec
    _merged_inputs = Handler._merged_inputs
    _bay_plan_view = Handler._bay_plan_view
    _inventory_compare_inputs = Handler._inventory_compare_inputs

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


def yard_session_with_harvest(harvest_mode="spark-grounding"):
    cache = StepCache(ROOT)
    harvest = cache.load_demo("harvest")
    parts = harvest["parts"]
    comps = get_comps_adapter(ROOT).lookup([p["id"] for p in parts], True)
    rules = load_rules(os.path.join(ROOT, "rules.json"))
    sid = server.new_session_id()
    server.put_session(sid, {"harvest": harvest, "harvest_mode": harvest_mode,
                             "comps": comps,
                             "verdicts": evaluate(parts, rules, comps)})
    return sid


def set_shop_demo(value):
    real = os.environ.get("SHOP_DEMO")
    if value is None:
        os.environ.pop("SHOP_DEMO", None)
    else:
        os.environ["SHOP_DEMO"] = value
    return real


class OneSwitchTest(unittest.TestCase):
    """2.1: live when the leg's key is present and demo is not forced."""

    def test_proven_legs_default_on_unproven_stay_off(self):
        import bay

        self.assertTrue(wonder.WONDER_LIVE)
        self.assertTrue(studio.IMAGE_LIVE)
        self.assertFalse(voice.VOICE_LIVE)
        self.assertFalse(bay.VIN_LIVE)

    def test_proven_model_defaults(self):
        self.assertEqual(wonder.WONDER_MODEL_DEFAULT, "muse-wonder-1.0")
        self.assertEqual(wonder.WONDER_PATH_DEFAULT, "/chat/completions")
        self.assertEqual(studio.IMAGE_MODEL_DEFAULT, "muse-image-1.0")
        self.assertEqual(studio.IMAGE_PATH_DEFAULT, "/responses")
        self.assertEqual(wonder.live_model(), "muse-wonder-1.0")
        self.assertEqual(studio.live_model(), "muse-image-1.0")

    def test_shop_demo_forces_every_leg_off(self):
        import bay

        real = set_shop_demo("1")
        try:
            self.assertTrue(demo_forced())
            self.assertFalse(wonder.live_enabled())
            self.assertFalse(studio.live_enabled())
            self.assertFalse(voice.live_enabled())
            self.assertFalse(bay.vin_live_enabled())
            self.assertFalse(spark_open.live_enabled())
        finally:
            set_shop_demo(real)
        self.assertFalse(demo_forced())

    def test_flag_patch_forces_demo(self):
        real_w, wonder.WONDER_LIVE = wonder.WONDER_LIVE, False
        real_s, studio.IMAGE_LIVE = studio.IMAGE_LIVE, False
        real_o, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, False
        try:
            self.assertFalse(wonder.live_enabled())
            self.assertFalse(studio.live_enabled())
            self.assertFalse(spark_open.live_enabled())
        finally:
            wonder.WONDER_LIVE = real_w
            studio.IMAGE_LIVE = real_s
            spark_open.SPARK_OPEN_LIVE = real_o

    def test_no_key_forces_demo(self):
        real_w = wonder._key_present
        real_s = studio._key_present
        real_o = spark_open._key_present
        wonder._key_present = lambda: False
        studio._key_present = lambda: False
        spark_open._key_present = lambda: False
        try:
            self.assertFalse(wonder.live_enabled())
            self.assertFalse(studio.live_enabled())
            self.assertFalse(spark_open.live_enabled())
        finally:
            wonder._key_present = real_w
            studio._key_present = real_s
            spark_open._key_present = real_o

    def test_voice_needs_confirmed_model_id(self):
        real_flag, voice.VOICE_LIVE = voice.VOICE_LIVE, True
        real_key = voice._key_present
        voice._key_present = lambda: True
        try:
            # Flag on and key present, but no confirmed model id in the
            # environment: still off until the owner confirms one.
            if not voice.live_model():
                self.assertFalse(voice.live_enabled())
        finally:
            voice.VOICE_LIVE = real_flag
            voice._key_present = real_key

    def test_env_example_documents_switch(self):
        text = read_root(".env.example")
        self.assertIn("SHOP_DEMO=1", text)
        self.assertIn("MUSE_WONDER_MODEL=muse-wonder-1.0", text)
        self.assertIn("MUSE_IMAGE_MODEL=muse-image-1.0", text)
        self.assertIn("muse-voice-transcribe-1.0", text)
        self.assertNotIn("key rotation", text)


class SparkGroundingHarvestTest(unittest.TestCase):
    """2.2: harvest from Spark's own boxes; SAM out of the live path."""

    def test_grounding_keeps_intake_car_and_boxes(self):
        intake = {
            "car": {"year": "1999", "make": "Testmake", "model": "Testmodel"},
            "parts": [
                {"id": "x1", "label": "widget", "category": "trim",
                 "intact": "yes", "intact_note": "shiny",
                 "count": 2, "box": [10, 20, 30, 40],
                 "source_tag": "photo-7"},
            ],
        }
        harvest = spark_grounding_harvest(intake)
        self.assertEqual(harvest["car"]["make"], "Testmake")
        (part,) = harvest["parts"]
        self.assertEqual(part["id"], "x1")
        (sighting,) = part["sightings"]
        self.assertEqual(sighting["box"], [10, 20, 30, 40])
        self.assertEqual(sighting["source"], "spark-live")
        self.assertEqual(sighting["source_tag"], "photo-7")

    def test_harvest_never_swaps_cars(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        intake = {
            "car": {"year": "1999", "make": "Testmake", "model": "Testmodel"},
            "parts": [{"id": "x1", "label": "widget", "box": [1, 2, 3, 4],
                       "source_tag": "photo-0"}],
        }
        server.put_session(sid, {"intake": intake, "intake_mode": "live"})
        try:
            Handler._api_harvest(fake, {"sessionId": sid})
        finally:
            shutil.rmtree(os.path.join(ROOT, "demo_cache", "live", sid),
                          ignore_errors=True)
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "spark-grounding")
        # The harvest describes the identified car, never the demo car.
        self.assertEqual(body["harvest"]["car"]["make"], "Testmake")
        self.assertNotIn("demo sample", body["harvest"]["car"]["make"])
        self.assertTrue(body["model"])
        self.assertIsInstance(body["ms"], int)

    def test_demo_harvest_unchanged(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(
            sid, {"intake": StepCache(ROOT).load_demo("intake"),
                  "intake_mode": "demo-cache"})
        Handler._api_harvest(fake, {"sessionId": sid, "demo": True})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "demo-cache")
        self.assertEqual(body["model"], "")

    def test_sam_out_of_live_path_but_kept_as_attempt(self):
        import meta_client

        harvest_src = read_root("server.py")
        handler = harvest_src[harvest_src.index("def _api_harvest"):
                              harvest_src.index("def _api_comps")]
        self.assertNotIn("segment_parts", handler)
        self.assertIn("spark_grounding_harvest", handler)
        self.assertTrue(callable(meta_client.segment_parts))

    def test_comps_treat_grounding_as_live(self):
        fake = FakeHandler()
        sid = yard_session_with_harvest("spark-grounding")
        Handler._api_comps(fake, {"sessionId": sid})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "live-adapter")
        self.assertIn("no reliable price", body["notice"])


class LiveListingDraftTest(unittest.TestCase):
    """2.3: live drafts on the yard and inventory paths."""

    def _stub_live_draft(self):
        real_key = server.api_key_present
        real_draft = server.build_live_draft
        server.api_key_present = lambda: True
        server.build_live_draft = lambda part, comp, verdict, car: {
            "title": "Live %s" % part.get("label", "part"),
            "description": "Stubbed live draft.",
            "condition": "Stubbed.",
            "source": "spark-live",
        }
        return real_key, real_draft

    def test_yard_live_draft(self):
        real_key, real_draft = self._stub_live_draft()
        try:
            fake = FakeHandler()
            sid = yard_session_with_harvest("spark-grounding")
            Handler._api_listing(fake, {"sessionId": sid, "partId": "p_diff"})
        finally:
            server.api_key_present = real_key
            server.build_live_draft = real_draft
            shutil.rmtree(os.path.join(ROOT, "demo_cache", "live", sid),
                          ignore_errors=True)
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "live")
        self.assertTrue(body["model"])
        self.assertIn("Live ", body["draft"]["title"])
        # Approve gate unchanged: post before approve is refused.
        Handler._api_listing_post(
            fake, {"sessionId": sid, "draftId": body["draftId"]})
        self.assertEqual(fake.sent[-1][0], 400)

    def test_inventory_live_draft(self):
        real_key, real_draft = self._stub_live_draft()
        try:
            fake = FakeHandler()
            Handler._api_listing(
                fake,
                {"invPart": {"id": "ip-x", "label": "knob",
                             "condition": "used", "value": 40,
                             "valueSource": "owner-entered"},
                 "invCar": {"year": "2001", "make": "BMW", "model": "325i"}})
        finally:
            server.api_key_present = real_key
            server.build_live_draft = real_draft
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "live")
        self.assertIn("Live knob", body["draft"]["title"])
        shutil.rmtree(os.path.join(ROOT, "demo_cache", "live", body["sessionId"]),
                      ignore_errors=True)

    def test_no_key_inventory_matches_old_demo_notice(self):
        real_key = server.api_key_present
        server.api_key_present = lambda: False
        try:
            fake = FakeHandler()
            Handler._api_listing(
                fake,
                {"invPart": {"id": "ip-x", "label": "knob"},
                 "invCar": {}})
        finally:
            server.api_key_present = real_key
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "demo-cache")
        self.assertEqual(
            body["notice"],
            "Demo case: showing the anonymized sample car, not your upload.")

    def test_demo_harvest_stays_demo(self):
        fake = FakeHandler()
        sid = yard_session_with_harvest("demo-cache")
        Handler._api_listing(fake, {"sessionId": sid, "partId": "p_diff"})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "demo-cache")
        self.assertEqual(body["model"], "")


class WonderLiveTest(unittest.TestCase):
    """2.4: Wonder live on hard calls, timed, never overwriting."""

    def test_live_opinion_carries_ms_and_model(self):
        real_gate = wonder.live_enabled
        real_request = wonder.request_opinion
        wonder.live_enabled = lambda: True
        wonder.request_opinion = lambda evidence: {
            "title": "Stubbed live opinion", "body": "Check it by hand.",
            "agrees": "partial", "watch": "rephoto",
            "source": "wonder-live", "ms": 4321,
            "model": "muse-wonder-1.0",
        }
        try:
            result = wonder.escalate(
                "yard",
                {"verdict": "B", "inputs": {"price_known": False}},
                "p_x", ROOT)
        finally:
            wonder.live_enabled = real_gate
            wonder.request_opinion = real_request
        self.assertTrue(result["escalated"])
        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["ms"], 4321)
        self.assertEqual(result["model"], "muse-wonder-1.0")
        # Beside the primary call: triggers assessed, verdict untouched.
        self.assertTrue(result["assessment"]["triggers"])
        self.assertEqual(result["opinion"]["source"], "wonder-live")

    def test_force_demo_wins_over_live(self):
        real_gate = wonder.live_enabled
        wonder.live_enabled = lambda: True
        try:
            result = wonder.escalate(
                "yard",
                {"verdict": "B", "inputs": {"price_known": False}},
                "p_x", ROOT, force_demo=True)
        finally:
            wonder.live_enabled = real_gate
        self.assertEqual(result["mode"], "demo-cache")
        self.assertIsNone(result["ms"])

    def test_wonder_endpoint_passes_ms_through(self):
        real_gate = wonder.live_enabled
        real_request = wonder.request_opinion
        wonder.live_enabled = lambda: True
        wonder.request_opinion = lambda evidence: {
            "title": "Stubbed", "body": "b", "agrees": True, "watch": "",
            "source": "wonder-live", "ms": 777, "model": "muse-wonder-1.0",
        }
        try:
            fake = FakeHandler()
            sid = yard_session_with_harvest("demo-cache")
            Handler._api_wonder(
                fake, {"sessionId": sid, "kind": "yard", "ref": "p_headlight"})
        finally:
            wonder.live_enabled = real_gate
            wonder.request_opinion = real_request
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "live")
        self.assertEqual(body["ms"], 777)
        self.assertEqual(body["model"], "muse-wonder-1.0")
        self.assertEqual(body["notice"], "")


class InventoryCompareTest(unittest.TestCase):
    """2.5: inventory second look beside the yard rows."""

    def _inv_payload(self):
        return [
            {"id": "ip-coil", "label": "spare ignition coil",
             "condition": "used, working when pulled", "note": "Kept as roadside spare",
             "value": 25, "valueSource": "demo-sample: inventory seed",
             "carLabel": "My driver"},
        ]

    def test_inventory_rows_without_yard_verdicts(self):
        real = spark_open.SPARK_OPEN_LIVE
        spark_open.SPARK_OPEN_LIVE = False
        try:
            fake = FakeHandler()
            sid = server.new_session_id()
            server.put_session(sid, {})
            Handler._api_compare(
                fake, {"sessionId": sid, "invItems": self._inv_payload()})
        finally:
            spark_open.SPARK_OPEN_LIVE = real
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"], [])
        (row,) = body["invRows"]
        self.assertEqual(row["label"], "spare ignition coil")
        self.assertIn(row["rule"], ("A", "B", "C"))
        self.assertEqual(body["invModeOpen"], "demo-cache")

    def test_inventory_live_second_look(self):
        seen = {}
        real = server.compare_grades

        def recording(evidence, part_ids, root):
            seen["evidence"] = evidence
            return {"grades": [{"part_id": "ip-coil", "grade": "C",
                                "reason": "Keep as spare."}],
                    "mode": "live", "source": "spark-open-live",
                    "notice": "", "ms": 19603,
                    "model": "meta-models/muse-spark-open-1026"}

        server.compare_grades = recording
        try:
            fake = FakeHandler()
            sid = yard_session_with_harvest("demo-cache")
            Handler._api_compare(
                fake, {"sessionId": sid, "invItems": self._inv_payload()})
        finally:
            server.compare_grades = real
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(len(body["rows"]), 7)
        (row,) = body["invRows"]
        self.assertEqual(row["gradeOpen"], "C")
        self.assertEqual(body["invMsOpen"], 19603)
        self.assertEqual(body["invModelOpen"], "meta-models/muse-spark-open-1026")
        # The owner's note rides the evidence, as in the recorded catch.
        (part,) = seen["evidence"]["parts"]
        self.assertIn("roadside spare", part["owner_note"])

    def test_inventory_rows_carry_money_grade(self):
        real = spark_open.SPARK_OPEN_LIVE
        spark_open.SPARK_OPEN_LIVE = False
        try:
            fake = FakeHandler()
            sid = server.new_session_id()
            server.put_session(sid, {})
            Handler._api_compare(
                fake, {"sessionId": sid, "invItems": self._inv_payload()})
        finally:
            spark_open.SPARK_OPEN_LIVE = real
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        (row,) = body["invRows"]
        # Owner value $25 prices the money side for real.
        self.assertIn(row["grade13"], ("A", "B", "C"))
        self.assertIn("Shop range nets", row["reason13"])
        self.assertEqual(body["invMode13"], "demo-cache")

    def test_inventory_money_falls_back_without_value(self):
        real = spark_open.SPARK_OPEN_LIVE
        spark_open.SPARK_OPEN_LIVE = False
        try:
            fake = FakeHandler()
            sid = server.new_session_id()
            server.put_session(sid, {})
            payload = [dict(self._inv_payload()[0])]
            payload[0].pop("value", None)
            payload[0].pop("valueSource", None)
            Handler._api_compare(fake, {"sessionId": sid, "invItems": payload})
        finally:
            spark_open.SPARK_OPEN_LIVE = real
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        (row,) = body["invRows"]
        self.assertEqual(row["grade13"], "?")
        self.assertIn("No owner value", row["reason13"])

    def test_compare_still_needs_something(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(sid, {})
        Handler._api_compare(fake, {"sessionId": sid})
        self.assertEqual(fake.sent[-1][0], 400)


class StudioGateTest(unittest.TestCase):
    """2.6: studio stays demo until a live image-edit call succeeds."""

    def test_no_cutout_bytes_no_live_studio(self):
        real_gate = studio.live_enabled
        real_key = server.api_key_present
        real_draft = server.build_live_draft
        studio.live_enabled = lambda: True
        server.api_key_present = lambda: True
        server.build_live_draft = lambda part, comp, verdict, car: {
            "title": "t", "description": "d", "condition": "c",
            "source": "spark-live",
        }
        try:
            fake = FakeHandler()
            sid = yard_session_with_harvest("spark-grounding")
            Handler._api_listing(fake, {"sessionId": sid, "partId": "p_diff"})
        finally:
            studio.live_enabled = real_gate
            server.api_key_present = real_key
            server.build_live_draft = real_draft
            shutil.rmtree(os.path.join(ROOT, "demo_cache", "live", sid),
                          ignore_errors=True)
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "live")
        self.assertIn("demo-cache", body["studio"]["source"])

    def test_art_renders_never_feed_listings(self):
        self.assertNotIn("request_art_render", read_root("server.py"))


class LiveVisibilityTest(unittest.TestCase):
    """2.7: chips on every live step, legs on /api/health."""

    def test_health_legs_shape(self):
        legs = server._live_legs()
        self.assertEqual(len(legs), 6)
        by_leg = {entry["leg"]: entry for entry in legs}
        self.assertEqual(
            sorted(by_leg),
            ["image", "spark", "spark-open", "vin", "voice", "wonder"])
        for entry in legs:
            self.assertIn(entry["key"], ("META_API_KEY", "BASETEN_API_KEY"))
            self.assertIsInstance(entry["key_present"], bool)
            self.assertIsInstance(entry["live"], bool)
            self.assertTrue(entry["label"])
            # Model ids only; a key value could never hide here unnoticed:
            # every model string is empty or a known model id prefix.
            self.assertTrue(
                entry["model"] == ""
                or entry["model"].startswith("muse-")
                or entry["model"].startswith("meta-models/"))

    def test_demo_responses_carry_empty_model(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(
            sid, {"intake": StepCache(ROOT).load_demo("intake"),
                  "intake_mode": "demo-cache"})
        Handler._api_intake(
            fake, {"sessionId": sid, "images": [{"name": "demo-frame-1"}],
                   "demo": True})
        body = fake.sent[-1][1]
        self.assertEqual(body["mode"], "demo-cache")
        self.assertEqual(body["model"], "")
        self.assertIsInstance(body["ms"], int)

    def test_frontend_live_chips(self):
        app = read_root("web/app.js")
        for pin in ("function isLiveMode", "function liveChip(",
                    "function liveChipHTML(", "function liveSuffix(",
                    "spark-grounding", "LIVE - ", "Live models:",
                    "invItems", "invRows", "Your inventory, second look",
                    "spark.grounding"):
            self.assertIn(pin, app, pin)
        self.assertNotIn("sam.segment", app)
        css = read_root("web/styles.css")
        self.assertIn(".livechip", css)


class LiveBayPlanTest(unittest.TestCase):
    """2.8: live plans flow through ranking + honest trail."""

    def test_live_plan_uses_same_ranking(self):
        real = server.draft_plan
        server.draft_plan = lambda case: [
            {"id": "t1", "title": "live test one", "causes": ["c1"],
             "symptom_match": True},
            {"id": "t2", "title": "live test two", "causes": ["c2"]},
        ]
        try:
            fake = FakeHandler()
            server.put_session("t-p2-live", {"bay": {
                "case": {"case_id": "c9", "declined": False},
                "plan": None, "modes": {}}})
            Handler._api_bay_plan(fake, {"sessionId": "t-p2-live"})
        finally:
            server.draft_plan = real
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "live")
        self.assertTrue(body["model"])
        self.assertEqual(len(body["plan"]["tests"]), 2)
        # Same ranking inputs, same pass/fail path.
        self.assertIn("score_parts", body["plan"]["tests"][0])
        Handler._api_bay_result(
            fake, {"sessionId": "t-p2-live", "testId": "t1", "result": "pass"})
        plan = fake.sent[-1][1]["plan"]
        self.assertEqual(len(plan["trail"]), 1)
        shutil.rmtree(
            os.path.join(ROOT, "demo_cache", "live", "t-p2-live"),
            ignore_errors=True)

    def test_real_jump_format(self):
        intake = load_bay_case("intake", "case3", ROOT)
        vehicle = intake["vehicle"]
        case = build_case(
            "b-3", vehicle,
            {"symptom": intake["symptom"], "codes": intake["codes"],
             "observations": intake["observations"], "area": intake["area"],
             "service_requested": intake["service_requested"],
             "engine": vehicle.get("engine", "")},
        )
        plan = new_plan(case, load_bay_case("plan", "case3", ROOT)["tests"])
        record_result(plan, "t1", "fail", "deviation stayed on 4")
        self.assertEqual(plan["trail"][-1]["moved"],
                         ["t2 -> #1 (+5, ruled out: bad injector; "
                          "now suspected: cylinder-side fault)"])

    def test_recorded_test_never_lists_itself(self):
        intake = load_bay_case("intake", "case1", ROOT)
        vehicle = intake["vehicle"]
        case = build_case(
            "b-1", vehicle,
            {"symptom": intake["symptom"], "codes": intake["codes"],
             "observations": intake["observations"], "area": intake["area"],
             "service_requested": intake["service_requested"],
             "engine": vehicle.get("engine", "")},
        )
        plan = new_plan(case, load_bay_case("plan", "case1", ROOT)["tests"])
        record_result(plan, "t1", "pass", "12.1V steady")
        record_result(plan, "t4", "fail", "no click by hand")
        self.assertFalse([j for j in plan["trail"][0]["moved"]
                          if j.startswith("t1 ")])
        self.assertFalse([j for j in plan["trail"][1]["moved"]
                          if j.startswith("t4 ")])


if __name__ == "__main__":
    unittest.main()
