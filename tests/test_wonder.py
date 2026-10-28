"""Wonder router tests (WO7 phase 3): triggers, routing, Standard-only."""

import os
import unittest

import server
import wonder
from bay import build_case, load_bay_case, new_plan
from comps import get_adapter as get_comps_adapter
from demo_cache import StepCache
from meta_client import MetaAPIError
from server import Handler
from verdict import evaluate, load_rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yard_verdicts():
    cache = StepCache(ROOT)
    parts = cache.load_demo("harvest")["parts"]
    comps = get_comps_adapter(ROOT).lookup([p["id"] for p in parts], True)
    rules = load_rules(os.path.join(ROOT, "rules.json"))
    return evaluate(parts, rules, comps)["verdicts"]


def case1_plan():
    intake = load_bay_case("intake", "case1", ROOT)
    vehicle = intake["vehicle"]
    case = build_case(
        "b-w",
        vehicle,
        {"symptom": intake["symptom"], "codes": intake["codes"],
         "observations": intake["observations"], "area": intake["area"],
         "service_requested": intake["service_requested"],
         "engine": vehicle.get("engine", "")},
    )
    return new_plan(case, load_bay_case("plan", "case1", ROOT)["tests"])


def clean_verdict():
    return {"verdict": "A",
            "inputs": {"price_known": True, "demand_source": "shop",
                       "intact": "yes", "frames_seen": 3}}


class WonderUnitTest(unittest.TestCase):
    def test_live_flag_off(self):
        self.assertFalse(wonder.WONDER_LIVE)

    def test_standard_only(self):
        self.assertEqual(wonder.WONDER_VARIANT, "standard")
        real, wonder.WONDER_VARIANT = wonder.WONDER_VARIANT, "full"
        try:
            with self.assertRaises(MetaAPIError) as ctx:
                wonder.request_opinion({"kind": "yard"})
            self.assertIn("Standard", str(ctx.exception))
        finally:
            wonder.WONDER_VARIANT = real

    def test_live_refuses_without_network(self):
        with self.assertRaises(MetaAPIError) as ctx:
            wonder.request_opinion({"kind": "yard"})
        self.assertIn("key rotation", str(ctx.exception))

    def test_yard_triggers(self):
        self.assertEqual(wonder.assess_yard(clean_verdict())["triggers"], [])
        borderline = dict(clean_verdict(), verdict="B")
        self.assertIn("borderline grade (B)",
                      wonder.assess_yard(borderline)["triggers"])
        blind = {"verdict": "C",
                 "inputs": {"price_known": False, "demand_source": "",
                            "intact": "unknown", "frames_seen": 1}}
        triggers = wonder.assess_yard(blind)["triggers"]
        self.assertIn("no reliable price", triggers)
        self.assertIn("demand unsourced", triggers)
        self.assertIn("condition unclear in photo", triggers)

    def test_bay_triggers(self):
        fresh = {"tests": [{"id": "t1", "title": "look"}], "results": {},
                 "suspected": [], "eliminated": []}
        self.assertIn("no results recorded yet",
                      wonder.assess_bay(fresh)["triggers"])
        split = dict(fresh, results={"t1": "pass"},
                     suspected=["a", "b"], eliminated=["c"])
        self.assertIn("suspects split 2 ways",
                      wonder.assess_bay(split)["triggers"])

    def test_demo_opinions(self):
        hit = wonder.demo_opinion("yard", "p_headlight", ROOT)
        self.assertIn("headlight", hit["title"].lower())
        self.assertIn("demo-cache", hit["source"])
        default = wonder.demo_opinion("yard", "p_unknown", ROOT)
        self.assertEqual(default["title"], "Second opinion")

    def test_router_passes_straight_cases(self):
        result = wonder.escalate("yard", clean_verdict(), "p_x", ROOT)
        self.assertFalse(result["escalated"])
        self.assertIsNone(result["opinion"])

    def test_router_escalates_hard_cases_demo(self):
        borderline = dict(clean_verdict(), verdict="B")
        result = wonder.escalate("yard", borderline, "p_x", ROOT)
        self.assertTrue(result["escalated"])
        self.assertEqual(result["mode"], "demo-cache")
        self.assertIn("demo-cache", result["opinion"]["source"])

    def test_hard_flag_forces_escalation(self):
        result = wonder.escalate("yard", clean_verdict(), "p_x", ROOT, hard=True)
        self.assertTrue(result["escalated"])
        self.assertIn("flagged hard by the shop",
                      result["assessment"]["triggers"])

    def test_real_headlight_escalates(self):
        verdict = next(v for v in yard_verdicts() if v["part_id"] == "p_headlight")
        result = wonder.escalate("yard", verdict, "p_headlight", ROOT)
        self.assertTrue(result["escalated"])
        self.assertIn("headlight", result["opinion"]["title"].lower())


class FakeHandler:
    _bay_session = Handler._bay_session

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


class WonderEndpointTest(unittest.TestCase):
    def test_yard_second_opinion(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(sid, {"verdicts": {"verdicts": yard_verdicts()}})
        Handler._api_wonder(
            fake, {"sessionId": sid, "kind": "yard", "ref": "p_headlight"})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertTrue(body["escalated"])
        self.assertIn("borderline grade (B)", body["triggers"])
        self.assertIn("key rotation", body["notice"])

    def test_bay_second_opinion_uses_demo_case_ref(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(
            sid, {"bay": {"plan": case1_plan(), "demo_case": "case1"}})
        Handler._api_wonder(fake, {"sessionId": sid, "kind": "bay"})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertTrue(body["escalated"])
        self.assertIn("silent module", body["opinion"]["title"].lower())

    def test_missing_evidence_is_400(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(sid, {})
        Handler._api_wonder(
            fake, {"sessionId": sid, "kind": "yard", "ref": "p_diff"})
        self.assertEqual(fake.sent[-1][0], 400)
        Handler._api_wonder(fake, {"sessionId": sid, "kind": "bay"})
        self.assertEqual(fake.sent[-1][0], 400)
        Handler._api_wonder(fake, {"sessionId": sid, "kind": "nope"})
        self.assertEqual(fake.sent[-1][0], 400)


if __name__ == "__main__":
    unittest.main()
