"""Video-spine journey tests (WO6): the demo beats in the order the video walks them.

Enthusiast half runs in Node against the real browser modules
(tests/spine_driver.js). Listing gate and shop half run here in-process
against the real server modules: draft blocks until Approve, then the Bay
case opens, a pass and a fail re-rank the plan with a visible trail,
a decline renders as a verdict, and recording every test closes the plan.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

import server
from server import Handler
from bay import build_case, labor_math, load_bay_case, new_plan, ranked_tests, record_result

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SpineDriverTest(unittest.TestCase):
    def test_enthusiast_beats_in_order(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for the spine journey driver")
        driver = os.path.join(ROOT, "tests", "spine_driver.js")
        proc = subprocess.run(
            [node, driver], cwd=ROOT, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, "spine driver failed:\n%s" % output)
        self.assertIn("ALL", output)
        self.assertNotIn("FAIL", output)
        # Beats land in video order: first-run, route, seed, register,
        # look-for, totals, reopen.
        marks = [
            "chooser appears on first run",
            "routes to inventory home",
            "M3 parts car is in the seed",
            "manual registration lands",
            "engine computer, $200, no EWS",
            "plain sourced money",
            "identity persists",
        ]
        positions = [output.index(m) for m in marks]
        self.assertEqual(positions, sorted(positions), "spine beats out of order")


class FakeHandler:
    """Captures _send_json; borrows the session helper (it ignores self)."""

    _bay_session = Handler._bay_session
    _cutout_spec = Handler._cutout_spec

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


class SpineListingGateTest(unittest.TestCase):
    def test_draft_blocks_until_approve_then_posts_mock(self):
        fake = FakeHandler()
        Handler._api_listing(
            fake,
            {
                "demo": True,
                "invPart": {
                    "id": "ip-ecu",
                    "label": "engine computer",
                    "condition": "used, pins clean",
                    "value": 200,
                    "valueSource": "demo-sample: owner note",
                },
                "invCar": {"year": "1995", "make": "BMW", "model": "M3"},
            },
        )
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        session_id, draft_id = body["sessionId"], body["draftId"]

        Handler._api_listing_post(
            fake, {"sessionId": session_id, "draftId": draft_id}
        )
        status, refused = fake.sent[-1]
        self.assertEqual(status, 400)
        self.assertIn("Approve", refused["error"])

        Handler._api_listing_approve(
            fake,
            {
                "sessionId": session_id,
                "draftId": draft_id,
                "title": "M3 engine computer",
                "description": "Used, pins clean.",
                "destinations": ["ebay"],
            },
        )
        status, approved = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertTrue(approved["ok"])

        # NOTE: tempfile lands inside the repo when TMPDIR points at the
        # workspace, so the scratch dir is removed in the finally below.
        scratch = tempfile.mkdtemp()
        real_root, server.ROOT = server.ROOT, scratch
        try:
            Handler._api_listing_post(
                fake, {"sessionId": session_id, "draftId": draft_id}
            )
        finally:
            server.ROOT = real_root
            shutil.rmtree(scratch, ignore_errors=True)
        status, posted = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(posted["draft"]["receipt"]["adapter"], "mock-outbox")
        self.assertIn("Nothing was sent", posted["draft"]["receipt"]["note"])


def case1():
    intake = load_bay_case("intake", "case1", ROOT)
    vehicle = intake["vehicle"]
    return build_case(
        "b-spine",
        vehicle,
        {
            "symptom": intake["symptom"],
            "codes": intake["codes"],
            "observations": intake["observations"],
            "area": intake["area"],
            "service_requested": intake["service_requested"],
            "engine": vehicle.get("engine", ""),
        },
    )


class SpineShopJourneyTest(unittest.TestCase):
    def test_bay_beats_in_order(self):
        # Open: symptom in, vehicle categorized, ranked plan with visible inputs.
        case = case1()
        self.assertFalse(case["declined"])
        self.assertIn("category", case["vehicle"])
        plan = new_plan(case, load_bay_case("plan", "case1", ROOT)["tests"])
        order = [t["id"] for t in ranked_tests(plan)]
        self.assertEqual(order, ["t1", "t2", "t4", "t3", "t5"])
        self.assertEqual(ranked_tests(plan)[0]["score_parts"]["symptom_match"], 3)

        # A pass rules a cause out and names what it did.
        record_result(plan, "t1", "pass", "12.1V steady")
        self.assertIn("no power to module", plan["eliminated"])
        self.assertIn("passed", plan["trail"][-1]["caused_by"])
        self.assertEqual(len(plan["trail"]), 1)

        # A fail suspects a cause and moves the ranking.
        record_result(plan, "t4", "fail", "no click by hand")
        self.assertIn("dead module", plan["suspected"])
        self.assertTrue(plan["trail"][-1]["moved"])
        self.assertEqual(len(plan["trail"]), 2)

        # Parts and labor stay sourced and plain.
        report = labor_math(plan, {})
        self.assertIn("$", report["plain_words"])
        self.assertIn("180", report["plain_words"])

        # Close: every test recorded, the plan is complete.
        for test in ranked_tests(plan):
            if test["id"] not in plan["results"]:
                record_result(plan, test["id"], "pass")
        self.assertEqual(len(plan["results"]), len(plan["tests"]))

    def test_decline_beat_renders_as_verdict(self):
        bad = build_case(
            "b-decline",
            {"year": 2012, "make": "BMW", "model": "550i", "trim": "", "engine": "N63"},
            {
                "symptom": "crank no start, nothing",
                "codes": [],
                "observations": [],
                "area": "electrical",
                "service_requested": "diagnose",
                "engine": "N63",
            },
        )
        self.assertTrue(bad["declined"])
        self.assertEqual(bad["decline"]["verdict"], "declined")
        self.assertTrue(bad["decline"]["title"])
        self.assertTrue(bad["decline"]["next_step"])


if __name__ == "__main__":
    unittest.main()
