"""Compare stage tests (WO9 phase 1): Spark Open adapter + endpoint, demo-forced.

No test here touches the network: the live flag is flipped off (or the
key gate is patched shut) for every live-path test, and the single-attempt
rule is proven by counting calls.
"""

import json
import os
import unittest

import server
import spark_open
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
    return cache.load_demo("harvest"), evaluate(parts, rules, comps)


class SparkOpenUnitTest(unittest.TestCase):
    def test_pinned_target_exact(self):
        self.assertEqual(spark_open.BASETEN_ENDPOINT, "https://inference.baseten.co/v1")
        self.assertEqual(spark_open.SPARK_OPEN_MODEL, "meta-models/muse-spark-open-1026")
        self.assertEqual(spark_open.BASETEN_KEY_NAME, "BASETEN_API_KEY")

    def test_no_meta_legs_in_module(self):
        with open(os.path.join(ROOT, "spark_open.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("api.meta.ai", src)
        self.assertNotIn("muse-spark-1.3", src)

    def test_live_refuses_when_flag_off(self):
        real, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, False
        try:
            with self.assertRaises(MetaAPIError):
                spark_open.request_grades({"parts": []})
        finally:
            spark_open.SPARK_OPEN_LIVE = real

    def test_live_refuses_without_key(self):
        real_flag, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, True
        real_key = spark_open._key_present
        spark_open._key_present = lambda: False
        try:
            with self.assertRaises(MetaAPIError) as ctx:
                spark_open.request_grades({"parts": []})
            self.assertEqual(ctx.exception.kind, "auth")
            self.assertIn("BASETEN_API_KEY", str(ctx.exception))
        finally:
            spark_open.SPARK_OPEN_LIVE = real_flag
            spark_open._key_present = real_key

    def test_key_gate_reads_env_name(self):
        real = os.environ.get("BASETEN_API_KEY")
        os.environ["BASETEN_API_KEY"] = "dummy-value-never-printed"
        try:
            self.assertTrue(spark_open._key_present())
        finally:
            if real is None:
                os.environ.pop("BASETEN_API_KEY", None)
            else:
                os.environ["BASETEN_API_KEY"] = real

    def test_demo_grades_cover_demo_set(self):
        found = spark_open.demo_grades(ROOT)
        self.assertEqual(len(found["grades"]), 7)
        self.assertIn("demo-cache", found["source"])
        self.assertTrue(all(g["reason"] for g in found["grades"]))
        by_id = {g["part_id"]: g["grade"] for g in found["grades"]}
        self.assertEqual(by_id["p_diff"], "A")
        self.assertEqual(by_id["p_headlight"], "B")
        self.assertEqual(by_id["p_taillight"], "C")

    def test_single_attempt_then_demo(self):
        calls = []
        real_request = spark_open.request_grades
        real_flag, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, True

        def counting(evidence):
            calls.append(1)
            raise MetaAPIError("boom", kind="unreachable")

        spark_open.request_grades = counting
        try:
            result = spark_open.compare_grades({"parts": []}, ["p_diff"], ROOT)
        finally:
            spark_open.request_grades = real_request
            spark_open.SPARK_OPEN_LIVE = real_flag
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["mode"], "demo-cache")

    def test_unknown_part_ids_dropped_and_named(self):
        real, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, False
        try:
            result = spark_open.compare_grades({"parts": []}, ["p_diff"], ROOT)
        finally:
            spark_open.SPARK_OPEN_LIVE = real
        self.assertEqual([g["part_id"] for g in result["grades"]], ["p_diff"])
        self.assertIn("dropped", result["notice"])


class FakeHandler:
    _bay_session = Handler._bay_session

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


class CompareEndpointTest(unittest.TestCase):
    def _session_with_verdicts(self):
        harvest, report = yard_verdicts()
        sid = server.new_session_id()
        server.put_session(sid, {"harvest": harvest, "verdicts": report})
        return sid, report

    def test_compare_rows_both_engines(self):
        real, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, False
        try:
            fake = FakeHandler()
            sid, report = self._session_with_verdicts()
            before = json.dumps(report["verdicts"], sort_keys=True)
            Handler._api_compare(fake, {"sessionId": sid})
        finally:
            spark_open.SPARK_OPEN_LIVE = real
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(len(body["rows"]), 7)
        self.assertEqual(body["mode13"], "demo-cache")
        self.assertEqual(body["modeOpen"], "demo-cache")
        # Rule grades pass through untouched: compare changes nothing.
        rules = {r["part_id"]: r["rule"] for r in body["rows"]}
        expect = {v["part_id"]: v["verdict"] for v in report["verdicts"]}
        self.assertEqual(rules, expect)
        after = json.dumps(server.get_session(sid)["verdicts"]["verdicts"], sort_keys=True)
        self.assertEqual(before, after)
        diff = next(r for r in body["rows"] if r["part_id"] == "p_diff")
        self.assertEqual(diff["grade13"], "A")
        self.assertEqual(diff["gradeOpen"], "A")
        self.assertIn("rotation", body["notice13"])
        self.assertIn("demo sample", body["noticeOpen"])

    def test_missing_key_notice_names_key(self):
        real_flag, spark_open.SPARK_OPEN_LIVE = spark_open.SPARK_OPEN_LIVE, True
        real_key = spark_open._key_present
        spark_open._key_present = lambda: False
        try:
            result = spark_open.compare_grades({"parts": []}, ["p_diff"], ROOT)
        finally:
            spark_open.SPARK_OPEN_LIVE = real_flag
            spark_open._key_present = real_key
        self.assertEqual(result["mode"], "demo-cache")
        self.assertIn("BASETEN_API_KEY", result["notice"])

    def test_compare_needs_verdicts(self):
        fake = FakeHandler()
        sid = server.new_session_id()
        server.put_session(sid, {})
        Handler._api_compare(fake, {"sessionId": sid})
        self.assertEqual(fake.sent[-1][0], 400)


class CompareLabelsTest(unittest.TestCase):
    """The ruling label must be visible in the shipped page, not just the API."""

    def test_engine_labels_in_page(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        for phrase in ("Muse Spark Open", "open-weight", "Baseten",
                       "Rules decide", "second look", "Compare"):
            self.assertIn(phrase, html, phrase)

    def test_engine_labels_in_render(self):
        with open(os.path.join(ROOT, "web", "app.js"), encoding="utf-8") as fh:
            src = fh.read()
        for phrase in ("Muse Spark 1.3", "Muse Spark Open, open-weight via Baseten"):
            self.assertIn(phrase, src, phrase)


if __name__ == "__main__":
    unittest.main()
