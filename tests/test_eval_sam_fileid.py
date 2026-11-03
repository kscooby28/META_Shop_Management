"""SAM file_id probe tests: file=note, fence intact, verdict honest.

The single upload plus segment already ran; these tests pin its
artifacts. Everything here runs offline: the README note must match
the probe JSON, no fenced measurement file may have changed, the
script's live-call allowlist must contain only the two probe calls,
VIN_LIVE stays False, the outside-repo photo stays out of the repo,
and no secret may appear in any artifact.
"""

import hashlib
import json
import ntpath
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import eval_sam_fileid

import bay
import test_eval_meta
import test_eval_sam_png

LIVE_CALL_MARKERS = test_eval_meta.LiveCallSitesTest.MARKERS

FILEID_START = "<!-- EVAL-SAM-FILEID:START -->"
FILEID_END = "<!-- EVAL-SAM-FILEID:END -->"

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
    os.path.join("scripts", "eval_sam_png.py"):
        "24504b9a0bb81340b55155ea751c5b55bcb3001e748ad5aae9e50a3c0d7437a8",
    "eval_sam_png_results.json":
        "a83381cd7dcfa98156f35a929a457d187b5cbcce96f8ab6ed15b598c9b53d8eb",
    os.path.join("tests", "test_eval_sam_png.py"):
        "bc2aa07bf26276eff36fb9b308160fe66634653961b442075883d9f8468a4877",
}


def load_results():
    with open(os.path.join(ROOT, "eval_sam_fileid_results.json"),
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


def probe_source():
    with open(os.path.join(ROOT, "scripts", "eval_sam_fileid.py"),
              encoding="utf-8") as fh:
        return fh.read()


class SamFileidShapeTest(unittest.TestCase):
    def test_results_file_wellformed(self):
        results = load_results()
        for key in ("photo", "upload", "call", "sam_verdict"):
            self.assertIn(key, results)
        self.assertIn(results["sam_verdict"], ("PROVEN", "CLOSED AGAIN"))
        self.assertEqual(results["sam_verdict"] == "PROVEN",
                         results["call"].get("verdict") == "PROVEN")
        self.assertIn(results["call"].get("verdict"),
                      ("PROVEN", "ZERO", "failed", "no-call"))

    def test_photo_hash_recorded(self):
        results = load_results()
        photo = results["photo"]
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", photo["sha256"]),
                        photo["sha256"])
        self.assertGreater(photo["bytes"], 0)
        self.assertTrue(re.fullmatch(r"\d+x\d+", photo["dims"]))
        self.assertTrue(photo["path"].endswith("sam-probe-photo.jpg"))
        # The recorded probe path is a Windows path; on POSIX it parses
        # as relative, so judge drive-qualified paths with Windows rules:
        # a Windows path cannot live inside a POSIX checkout.
        drive, _ = ntpath.splitdrive(photo["path"])
        if drive and os.name != "nt":
            self.assertTrue(ntpath.isabs(photo["path"]), photo["path"])
        else:
            self.assertFalse(os.path.abspath(photo["path"]).startswith(
                os.path.abspath(ROOT)))
        if os.path.isfile(photo["path"]):
            with open(photo["path"], "rb") as fh:
                raw = fh.read()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),
                             photo["sha256"])
            self.assertEqual(len(raw), photo["bytes"])

    def test_one_attempt_each(self):
        results = load_results()
        self.assertLessEqual(results["live_calls_sent_total"], 2)
        self.assertEqual(results["model_list_calls_sent"], 0)
        self.assertIn(results["upload"]["call_sent"], (True, False))
        self.assertIn(results["call"]["call_sent"], (True, False))
        if results["call"]["call_sent"]:
            self.assertTrue(results["upload"]["file_id"])

    def test_geometry_counts_honest(self):
        results = load_results()
        call = results["call"]
        if not call["call_sent"] or call.get("cause"):
            return
        geometry = call["geometry"]
        for key in ("box_count", "mask_count", "paired_records",
                    "malformed_lines"):
            self.assertIsInstance(geometry[key], int)
            self.assertGreaterEqual(geometry[key], 0)
        self.assertEqual(len(geometry["boxes"]), geometry["box_count"])
        self.assertEqual(len(geometry["masks"]), geometry["mask_count"])
        for box in geometry["boxes"]:
            for key in ("x1", "y1", "x2", "y2", "w", "h"):
                self.assertIsInstance(box[key], int)
        if call["verdict"] == "PROVEN":
            self.assertGreaterEqual(geometry["paired_records"], 1)
        else:
            self.assertEqual(geometry["paired_records"], 0)


class SamFileidReadmeTest(unittest.TestCase):
    def test_readme_note_matches_file(self):
        results = load_results()
        block = readme_block(readme_text(), FILEID_START, FILEID_END)
        self.assertTrue(block.strip())
        call = results["call"]
        if call.get("request_id"):
            self.assertIn(call["request_id"], block)
        if results["upload"].get("file_id"):
            self.assertIn(results["upload"]["file_id"], block)
        self.assertIn(results["sam_verdict"], block)
        self.assertIn("VIN_LIVE stays False", block)


class SamFileidFenceTest(unittest.TestCase):
    def test_fenced_files_identical(self):
        for rel, pinned in FENCE_PINNED.items():
            self.assertEqual(sha256_of(rel), pinned, rel)

    def test_photo_never_in_repo(self):
        # Shipped art (the landing street photo) is allowed; only the
        # recorded probe photo itself must stay out of the repo.
        probe = load_results()["photo"]["sha256"]
        hits = []
        for base, _, names in os.walk(ROOT):
            for name in names:
                if not name.lower().endswith((".jpg", ".jpeg")):
                    continue
                path = os.path.join(base, name)
                try:
                    with open(path, "rb") as fh:
                        digest = hashlib.sha256(fh.read()).hexdigest()
                except OSError:
                    continue
                if digest == probe:
                    hits.append(path)
        self.assertEqual(hits, [])

    def test_vin_live_still_false(self):
        results = load_results()
        self.assertFalse(results["vin_live"])
        self.assertEqual(results["live_vin_calls_sent"], 0)
        self.assertIs(bay.VIN_LIVE, False)

    def test_allowlist_is_two_sam_calls(self):
        self.assertEqual(eval_sam_fileid.PROBE_ALLOWLIST,
                         ("sam-fileid-upload", "sam-fileid-segment"))
        src = probe_source()
        for marker in LIVE_CALL_MARKERS:
            self.assertNotIn(marker, src, marker)
        self.assertEqual(src.count("urlopen("), 2)
        self.assertIn("/files", src)
        self.assertIn("/responses", src)
        self.assertNotIn("/chat/completions", src)
        self.assertNotIn("/images/", src)
        self.assertNotIn("/models", src)

    def test_no_secrets_in_artifacts(self):
        values = test_eval_sam_png.env_secret_values(
            os.path.join(ROOT, ".env"))
        haystacks = [
            open(os.path.join(ROOT, "eval_sam_fileid_results.json"),
                 encoding="utf-8").read(),
            readme_block(readme_text(), FILEID_START, FILEID_END),
        ]
        for value in values:
            for haystack in haystacks:
                self.assertNotIn(value, haystack)


if __name__ == "__main__":
    unittest.main()
