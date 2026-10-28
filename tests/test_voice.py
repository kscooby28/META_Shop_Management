"""Voice notes tests (WO7 phase 2): demo transcripts, pinning, flag off."""

import os
import unittest

import server
import voice
from meta_client import MetaAPIError
from server import Handler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class VoiceDemoTest(unittest.TestCase):
    def test_live_flag_off(self):
        self.assertFalse(voice.VOICE_LIVE)

    def test_live_refuses_without_network(self):
        with self.assertRaises(MetaAPIError) as ctx:
            voice.transcribe_live("audiodata", "audio/webm")
        self.assertIn("key rotation", str(ctx.exception))

    def test_demo_transcript_per_kind(self):
        bay = voice.demo_transcript("bay", ROOT)
        inv = voice.demo_transcript("inv", ROOT)
        self.assertTrue(bay["text"] and inv["text"])
        self.assertNotEqual(bay["text"], inv["text"])
        self.assertIn("demo-cache", bay["source"])

    def test_missing_audio_is_named(self):
        quiet = voice.demo_transcript("bay", ROOT, audio_present=False)
        self.assertIn("No audio", quiet["note"])

    def test_gated_entry_serves_demo(self):
        result = voice.transcribe(None, "bay", ROOT)
        self.assertEqual(result["mode"], "demo-cache")
        self.assertTrue(result["text"])

    def test_bad_kind_rejected(self):
        with self.assertRaises(MetaAPIError):
            voice.transcribe(None, "garage", ROOT)


class FakeHandler:
    _bay_session = Handler._bay_session

    def __init__(self):
        self.sent = []

    def _send_json(self, obj, status=200):
        self.sent.append((status, obj))


class VoiceEndpointTest(unittest.TestCase):
    def _open_case(self, fake):
        Handler._api_bay_intake(fake, {"demoCase": "case1"})
        return fake.sent[-1][1]["sessionId"]

    def test_note_pins_to_open_case(self):
        fake = FakeHandler()
        sid = self._open_case(fake)
        Handler._api_voice_note(
            fake,
            {"sessionId": sid, "target": {"kind": "bay"},
             "audio": {"mime": "audio/webm", "data": "x"}},
        )
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "demo-cache")
        self.assertTrue(body["text"])
        self.assertTrue(body["pinned"])
        self.assertIn("key rotation", body["notice"])
        case = server.get_session(sid)["bay"]["case"]
        self.assertEqual(len(case["voice_notes"]), 1)
        self.assertIn("demo-cache", case["voice_notes"][0]["source"])

    def test_text_returns_without_open_case(self):
        fake = FakeHandler()
        Handler._api_voice_note(
            fake, {"target": {"kind": "bay"}, "audio": None}
        )
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertTrue(body["text"])
        self.assertFalse(body["pinned"])

    def test_inventory_transcribes_without_pinning(self):
        fake = FakeHandler()
        sid = self._open_case(fake)
        Handler._api_voice_note(
            fake, {"sessionId": sid, "target": {"kind": "inv"}, "audio": None}
        )
        status, body = fake.sent[-1]
        self.assertEqual(status, 200)
        self.assertFalse(body["pinned"])
        self.assertNotIn("voice_notes", server.get_session(sid)["bay"]["case"])

    def test_bad_kind_is_400(self):
        fake = FakeHandler()
        Handler._api_voice_note(fake, {"target": {"kind": "nope"}})
        self.assertEqual(fake.sent[-1][0], 400)


if __name__ == "__main__":
    unittest.main()
