"""Server helper tests: exercise real Handler method bodies without sockets."""

import json
import os
import unittest

import server
from server import Handler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_demo(name):
    with open(os.path.join(ROOT, "demo_cache", name), "r", encoding="utf-8") as fh:
        return json.load(fh)


class ServerHelperTest(unittest.TestCase):
    def setUp(self):
        harvest = load_demo("harvest.demo.json")
        self.session = {
            "harvest": harvest,
            "comps": load_demo("comps.demo.json"),
            "verdicts": {"verdicts": [], "totals": {}},
        }

    def test_case_summary_before_and_after_verdicts(self):
        early = Handler._case_summary(None, self.session)
        self.assertIn("no verdicts yet", early)
        from verdict import evaluate, load_rules

        rules = load_rules(os.path.join(ROOT, "rules.json"))
        report = evaluate(self.session["harvest"]["parts"], rules, self.session["comps"])
        self.session["verdicts"] = report
        full = Handler._case_summary(None, self.session)
        self.assertIn("grade A", full)
        self.assertIn("Total A:", full)

    def test_local_chat_answers(self):
        self.assertIn("No car yet", Handler._local_chat_answer(None, None, "Identify this car"))
        car = Handler._local_chat_answer(None, self.session, "Identify this car")
        self.assertIn("325", car)
        self.assertIn("unknown", car)
        self.assertIn("No verdicts yet", Handler._local_chat_answer(None, self.session, "Why is this part a B?"))
        from verdict import evaluate, load_rules

        rules = load_rules(os.path.join(ROOT, "rules.json"))
        self.session["verdicts"] = evaluate(
            self.session["harvest"]["parts"], rules, self.session["comps"]
        )
        why = Handler._local_chat_answer(None, self.session, "Why is this part a B?")
        self.assertIn("headlight", why.lower())
        self.assertIn("listing", Handler._local_chat_answer(None, self.session, "Draft the listing").lower())

    def test_cutout_and_merge(self):
        diff = next(p for p in self.session["harvest"]["parts"] if p["id"] == "p_diff")
        cut = Handler._cutout_spec(None, diff)
        self.assertEqual(cut["frame"], "demo-frame-4")
        self.assertEqual(cut["box"], [300, 360, 700, 570])
        merged = Handler._merged_inputs(None, self.session, {"p_diff": {"price_low": 1}})
        self.assertEqual(merged["p_diff"]["price_low"], 1)  # shop-typed wins
        self.assertEqual(merged["p_diff"]["price_high"], 1100)  # comp fills the rest

    def test_module_imports_cleanly(self):
        self.assertTrue(server.ROOT.endswith("META_Shop_Management") or server.ROOT)


class SSEFakeHandler:
    """Capture _api_chat's SSE stream without sockets or network."""

    _case_summary = Handler._case_summary
    _local_chat_answer = Handler._local_chat_answer

    def __init__(self):
        self.raw = b""
        self.wfile = self

    def send_response(self, code):
        self.code = code

    def send_header(self, key, value):
        pass

    def end_headers(self):
        pass

    def write(self, chunk):
        self.raw += chunk

    def flush(self):
        pass

    def events(self):
        found = []
        for chunk in self.raw.split(b"\n\n"):
            if chunk.startswith(b"data: "):
                found.append(json.loads(chunk[6:].decode("utf-8")))
        return found


class ChatDemoTest(unittest.TestCase):
    def test_chat_honors_shop_demo_env(self):
        real_stream = server.chat_stream
        called = []

        def explode(*args, **kwargs):
            called.append(True)
            raise AssertionError("live chat attempted under SHOP_DEMO=1")

        server.chat_stream = explode
        real_env = os.environ.get("SHOP_DEMO")
        os.environ["SHOP_DEMO"] = "1"
        try:
            fake = SSEFakeHandler()
            Handler._api_chat(fake, {"message": "Will this run rich?"})
        finally:
            if real_env is None:
                os.environ.pop("SHOP_DEMO", None)
            else:
                os.environ["SHOP_DEMO"] = real_env
            server.chat_stream = real_stream
        self.assertEqual(called, [])
        events = fake.events()
        modes = [e.get("mode") for e in events
                 if e.get("type") in ("mode", "done")]
        self.assertTrue(modes)
        for mode in modes:
            self.assertEqual(mode, "demo-cache")
        self.assertTrue(any(e.get("type") == "token" and e.get("text")
                            for e in events))


if __name__ == "__main__":
    unittest.main()
