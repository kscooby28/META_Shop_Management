"""SAM PNG resend tests: file=note, fence intact, leg honestly closed.

The single segment call already ran; these tests pin its artifacts.
Everything here runs offline: the README note must match the PNG
results JSON, no WO16 or follow-up measurement file may have changed,
the script's live-call allowlist must contain only the one SAM PNG
call, VIN_LIVE stays False, and no secret may appear in any artifact.
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import eval_sam_png

import bay
import test_eval_meta

LIVE_CALL_MARKERS = test_eval_meta.LiveCallSitesTest.MARKERS

SAM_START = "<!-- EVAL-SAM-PNG:START -->"
SAM_END = "<!-- EVAL-SAM-PNG:END -->"

# .env names ending in these suffixes hold PUBLIC CONFIG (model ids,
# endpoint paths, base URLs — public by construction, published in
# official docs), never secrets. The no-secrets scan exempts values
# under these name patterns only; every other .env value is asserted
# absent from every artifact.
PUBLIC_CONFIG_SUFFIXES = ("_MODEL", "_PATH", "_ENDPOINT", "_BASE")


def env_secret_values(env_path):
    """Secret-shaped .env values only; public-config names exempt."""
    secrets = []
    try:
        with open(env_path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return secrets  # cold clone ships no .env; nothing to leak
    for line in lines:
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if not value.strip():
            continue
        if name.strip().endswith(PUBLIC_CONFIG_SUFFIXES):
            continue
        secrets.append(value.strip())
    return secrets

# sha256 pins over LF-normalized bytes (see sha256_of). Product-file
# and web-tree fences retired in WO22; only measurement files stay pinned.
FENCE_PINNED = {
    os.path.join("scripts", "eval_meta.py"):
        "2cce94147b9e1d73f8bb3c8779b12e18c2a9a5f9643eb31c026638518d294301",
    "eval_meta_results.json":
        "62877fd49ff3171c1a389d6a5c7602784e254ee1fa319a17f5e26d90de1499ab",
    os.path.join("tests", "test_eval_meta.py"):
        "574afea0f5e0ffb78ba8fce9d442f660b8e05fc389c46d76b3e5d4aeae4e3451",
    os.path.join("scripts", "eval_meta_followup.py"):
        "5bd89fb48780d3caf1a6b2051fd0afd205d202b436d873a8e559169fd056b6af",
    "eval_meta_followup_results.json":
        "0ae661705b688420514a2b5bfe147f6c0dc913c3d7b483d64380c60d62519134",
    os.path.join("tests", "test_eval_meta_followup.py"):
        "94e709e1369b6b13161295ead9798d28ea8100e75f1047f94c9b57b66df2ab65",
}


def load_results():
    with open(os.path.join(ROOT, "eval_sam_png_results.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def readme_text():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def readme_block(text, start, end):
    _, _, rest = text.partition(start)
    block, _, _ = rest.partition(end)
    return block


def sha256_of(rel):
    # LF-normalized: the same file hashes identically on CRLF and LF
    # checkouts, so the fence holds on Windows, Mac, and Linux.
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def resend_source():
    with open(os.path.join(ROOT, "scripts", "eval_sam_png.py"),
              encoding="utf-8") as fh:
        return fh.read()


class SamPngShapeTest(unittest.TestCase):
    def test_results_file_shape(self):
        results = load_results()
        self.assertIn("png", results)
        self.assertIn("call", results)
        self.assertIsInstance(results["sam_proven_live"], bool)
        self.assertEqual(results["sam_proven_live"],
                         results["call"]["verdict"] == "proven-live")
        self.assertEqual(results["rewire_follows"],
                         results["sam_proven_live"])
        self.assertIn(results["call"]["verdict"],
                      ("proven-live", "responded-empty", "failed", "no-call"))

    def test_one_attempt_gated_by_png(self):
        results = load_results()
        self.assertLessEqual(results["live_calls_sent_total"], 1)
        self.assertEqual(results["model_list_calls_sent"], 0)
        if not results["png"]["png_ok"]:
            self.assertFalse(results["call"]["call_sent"])
            self.assertEqual(results["call"]["verdict"], "no-call")
        if results["call"]["call_sent"]:
            self.assertTrue(results["png"]["png_ok"])
            self.assertEqual(results["call"]["frame"], "demo-frame-1")

    def test_png_fidelity_pins(self):
        results = load_results()
        with open(os.path.join(ROOT, "web", "demo", "frame1.svg"),
                  "rb") as fh:
            svg_hash = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(results["png"]["svg_sha256"], svg_hash)
        if results["png"]["png_ok"]:
            png = results["png"]["png"]
            self.assertEqual(png["mime"], "image/png")
            self.assertEqual(png["dims"], "1000x1000")
            self.assertGreater(png["bytes"], 0)
            self.assertTrue(png["sha256"])


class SamPngReadmeTest(unittest.TestCase):
    def test_readme_note_matches_file(self):
        results = load_results()
        block = readme_block(readme_text(), SAM_START, SAM_END)
        self.assertTrue(block.strip())
        call = results["call"]
        if call.get("request_id"):
            self.assertIn(call["request_id"], block)
        self.assertIn(call["verdict"], block)
        if results["png"]["png_ok"]:
            self.assertIn(results["png"]["png"]["sha256"], block)
        self.assertIn("NOT proven live" if not results["sam_proven_live"]
                      else "PROVEN live", block)
        self.assertIn("VIN_LIVE stays False", block)


class SamPngFenceTest(unittest.TestCase):
    def test_fenced_files_identical(self):
        for rel, pinned in FENCE_PINNED.items():
            self.assertEqual(sha256_of(rel), pinned, rel)

    def test_vin_live_still_false(self):
        results = load_results()
        self.assertFalse(results["vin_live"])
        self.assertEqual(results["live_vin_calls_sent"], 0)
        self.assertIs(bay.VIN_LIVE, False)

    def test_allowlist_is_one_sam_call(self):
        self.assertEqual(eval_sam_png.PROBE_ALLOWLIST, ("sam-png-segment",))
        self.assertTrue(callable(eval_sam_png.probe_sam_png))
        src = resend_source()
        for marker in LIVE_CALL_MARKERS:
            self.assertNotIn(marker, src, marker)
        self.assertEqual(src.count("urlopen("), 0)
        self.assertEqual(src.count("post_capture("), 1)
        self.assertNotIn('"/sam/segment"', src)
        self.assertNotIn("'/sam/segment'", src)

    def test_no_secrets_in_artifacts(self):
        values = env_secret_values(os.path.join(ROOT, ".env"))
        haystacks = [
            open(os.path.join(ROOT, "eval_sam_png_results.json"),
                 encoding="utf-8").read(),
            readme_block(readme_text(), SAM_START, SAM_END),
        ]
        for value in values:
            for haystack in haystacks:
                self.assertNotIn(value, haystack)

    def test_secret_split_catches_fake_key_exempts_public_config(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".env", delete=False, encoding="utf-8") as fh:
            fh.write("FAKE_API_KEY=sk-fakeplant-9f8e7d6c5b4a\n"
                     "MUSE_IMAGE_MODEL=muse-image-1.0\n"
                     "MUSE_IMAGE_PATH=/responses\n")
            tmp = fh.name
        try:
            values = env_secret_values(tmp)
        finally:
            os.unlink(tmp)
        self.assertEqual(values, ["sk-fakeplant-9f8e7d6c5b4a"])
        planted = ("model muse-image-1.0 path /responses "
                   "key sk-fakeplant-9f8e7d6c5b4a end")
        flagged = [v for v in values if v in planted]
        self.assertEqual(flagged, ["sk-fakeplant-9f8e7d6c5b4a"])


if __name__ == "__main__":
    unittest.main()
