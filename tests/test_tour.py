"""Guided tour tests (WO12): beat order, exit, demo-only, side-effect-free.

The tour UI runs in the browser, so structure is proven statically
against the delimited tour section in web/app.js, and the action
sequence it drives is replayed in-process against the real handlers to
prove grades never change and nothing is approved or posted.
"""

import os
import re
import shutil
import unittest

import server
import spark_open
from comps import get_adapter as get_comps_adapter
from demo_cache import StepCache
from server import Handler
from verdict import evaluate, load_rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_APP = os.path.join(ROOT, "web", "app.js")

BEAT_ORDER = ["chooser", "register", "dme", "totals", "listing", "ranking",
              "decline", "close", "money", "compare"]


def tour_section():
    src = open(WEB_APP, encoding="utf-8").read()
    start = src.index("===== guided tour (WO12)")
    end = src.index("===== end guided tour =====")
    return src[start:end]


class TourStaticTest(unittest.TestCase):
    def test_beats_in_spine_order(self):
        ids = re.findall(r'\{ id: "(\w+)"', tour_section())
        self.assertEqual(ids, BEAT_ORDER)

    def test_every_beat_explained(self):
        section = tour_section()
        self.assertEqual(section.count('title: "'), 10)
        self.assertEqual(section.count('line: "'), 10)

    def test_exit_and_restart(self):
        section = tour_section()
        self.assertIn("Exit tour", section)
        self.assertIn("exitTour()", section)
        self.assertIn("beat: 0", section)

    def test_tour_never_approves_or_posts(self):
        section = tour_section()
        for banned in ("/api/listing/approve", "/api/listing/post",
                       "_api_listing_approve", "_api_listing_post",
                       "save_rules", "put_session"):
            self.assertNotIn(banned, section, banned)

    def test_tour_names_no_engine_code(self):
        # The decline beat uses the oil-change path so no engine code
        # ever appears on screen, on camera or off.
        self.assertNotIn("N63", tour_section())

    def test_compare_beat_forces_demo(self):
        self.assertIn("runCompare({ demo: true })", tour_section())

    def test_entry_on_both_homes(self):
        src = open(WEB_APP, encoding="utf-8").read()
        self.assertEqual(src.count("Take the tour"), 2)
        self.assertEqual(src.count("startTour()"), 3)  # 2 entries + def


class FakeHandler:
    _bay_session = Handler._bay_session
    _cutout_spec = Handler._cutout_spec
    _bay_plan_view = Handler._bay_plan_view

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


def live_files():
    root = os.path.join(ROOT, "demo_cache", "live")
    found = set()
    for base, _, files in os.walk(root):
        found.update(os.path.join(base, f) for f in files)
    return found


class TourSequenceTest(unittest.TestCase):
    """Replay the tour's action sequence: grades frozen, gate untouched."""

    def test_sequence_changes_no_grade_approves_nothing(self):
        cache = StepCache(ROOT)
        parts = cache.load_demo("harvest")["parts"]
        comps = get_comps_adapter(ROOT).lookup([p["id"] for p in parts], True)
        rules = load_rules(os.path.join(ROOT, "rules.json"))
        before = {v["part_id"]: v["verdict"]
                  for v in evaluate(parts, rules, comps)["verdicts"]}
        files_before = live_files()

        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(
            sid, {"harvest": cache.load_demo("harvest"),
                  "comps": comps,
                  "verdicts": evaluate(parts, rules, comps)})
        # Listing beat: draft only, never approve.
        Handler._api_listing(fake, {"sessionId": sid, "partId": "p_diff"})
        self.assertEqual(fake.sent[-1][0], 200)
        # Ranking beat: case1 opens, plan drafts.
        Handler._api_bay_intake(fake, {"sessionId": sid, "demoCase": "case1"})
        Handler._api_bay_plan(fake, {"sessionId": sid})
        plan_tests = [t["id"] for t in fake.sent[-1][1]["plan"]["tests"]]
        self.assertEqual(plan_tests, ["t1", "t2", "t4", "t3", "t5"])
        # Re-rank inside the ranking beat: pass + fail move the trail.
        Handler._api_bay_result(
            fake, {"sessionId": sid, "testId": "t1", "result": "pass"})
        Handler._api_bay_result(
            fake, {"sessionId": sid, "testId": "t4", "result": "fail"})
        self.assertEqual(len(fake.sent[-1][1]["plan"]["trail"]), 2)
        # Decline beat mirrors the tour: oil-change decline, no engine
        # code anywhere. (N63 policy is covered by test_spine + smoke.)
        Handler._api_bay_intake(
            fake,
            {"sessionId": sid,
             "manual": {
                 "vehicle": {"year": 2015, "make": "BMW", "model": "328i",
                             "engine": ""},
                 "area": "maintenance", "service_requested": "oil change",
                 "symptom": "due for an oil change", "codes": []}},
        )
        self.assertTrue(fake.sent[-1][1]["case"]["declined"])
        Handler._api_bay_plan(fake, {"sessionId": sid})
        self.assertEqual(fake.sent[-1][0], 400)
        # Close beat: reopen, record everything, plan complete.
        Handler._api_bay_intake(fake, {"sessionId": sid, "demoCase": "case1"})
        Handler._api_bay_plan(fake, {"sessionId": sid})
        for tid in ("t1", "t2", "t3", "t4", "t5"):
            Handler._api_bay_result(
                fake, {"sessionId": sid, "testId": tid,
                       "result": "fail" if tid == "t4" else "pass"})
        done = fake.sent[-1][1]["plan"]
        self.assertEqual(len(done["results"]), len(done["tests"]))
        # Money beat: grades carry money stats; compare beat: demo forced.
        Handler._api_compare(
            fake, {"sessionId": sid, "demo": True})
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["modeOpen"], "demo-cache")

        session = server.get_session(sid)
        after = {v["part_id"]: v["verdict"]
                 for v in session["verdicts"]["verdicts"]}
        self.assertEqual(after, before)
        drafts = session.get("drafts") or {}
        self.assertTrue(drafts)
        self.assertTrue(all(d.get("status") == "draft" for d in drafts.values()))
        new_files = live_files() - files_before
        self.assertFalse(
            [f for f in new_files
             if "outbox" in f or os.path.basename(f).startswith("post-")],
            "tour sequence posted something",
        )
        # Intake snapshots are standard handler behavior; remove this
        # test's own session dir so the tree stays clean.
        shutil.rmtree(os.path.join(ROOT, "demo_cache", "live", sid), ignore_errors=True)

    def test_demo_flag_beats_live(self):
        calls = []
        real = spark_open.request_grades

        def counting(evidence):
            calls.append(1)
            raise AssertionError("tour must not attempt live")

        spark_open.request_grades = counting
        try:
            fake = FakeHandler()
            sid = server.new_session_id()
            cache = StepCache(ROOT)
            parts = cache.load_demo("harvest")["parts"]
            comps = get_comps_adapter(ROOT).lookup([p["id"] for p in parts], True)
            rules = load_rules(os.path.join(ROOT, "rules.json"))
            server.put_session(
                sid, {"harvest": cache.load_demo("harvest"),
                      "verdicts": evaluate(parts, rules, comps)})
            Handler._api_compare(fake, {"sessionId": sid, "demo": True})
        finally:
            spark_open.request_grades = real
        self.assertEqual(calls, [])
        self.assertEqual(fake.sent[-1][0], 200)
        self.assertEqual(fake.sent[-1][1]["modeOpen"], "demo-cache")


if __name__ == "__main__":
    unittest.main()
