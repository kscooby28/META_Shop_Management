"""SAM file_id probe tests: file=note, fence intact, verdict honest.

The single upload plus segment already ran; these tests pin its
artifacts. Everything here runs offline: the README note must match
the probe JSON, no fenced file may have changed, the script's
live-call allowlist must contain only the two probe calls, VIN_LIVE
stays False, the outside-repo photo stays out of the repo, and no
secret may appear in any artifact.
"""

import hashlib
import json
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

# sha256 pins taken at the probe commit. Any edit to a fenced file
# fails loudly here instead of slipping through.
FENCE_PINNED = {
    os.path.join("scripts", "eval_meta.py"):
        "2cce94147b9e1d73f8bb3c8779b12e18c2a9a5f9643eb31c026638518d294301",
    "eval_meta_results.json":
        "61b24bb39bc1b2888db0f0e85c2695bf419faaf952c518422e0f627f1fdd3d03",
    os.path.join("tests", "test_eval_meta.py"):
        "574afea0f5e0ffb78ba8fce9d442f660b8e05fc389c46d76b3e5d4aeae4e3451",
    os.path.join("scripts", "eval_meta_followup.py"):
        "5bd89fb48780d3caf1a6b2051fd0afd205d202b436d873a8e559169fd056b6af",
    "eval_meta_followup_results.json":
        "f5b10a426724dfd43ea5123a5eb1279b6b68e1edc0b01e872ba032e1d34e20cf",
    os.path.join("tests", "test_eval_meta_followup.py"):
        "2d8a8552a2d2e8d7e39b3a99e1fa9a072cf5d9bd603076d101929418f118640f",
    os.path.join("scripts", "eval_sam_png.py"):
        "24504b9a0bb81340b55155ea751c5b55bcb3001e748ad5aae9e50a3c0d7437a8",
    "eval_sam_png_results.json":
        "1780f883e71f5774f4dbc07840040f891b165e16dd0b955bf9294a464d42bd29",
    os.path.join("tests", "test_eval_sam_png.py"):
        "62b69543ec9df6dc9f0f4a216c2eb67c6d22c79146ae633b8b594abb3d73ecd2",
    "studio.py":
        "adbc77590010b488f29dd9403f673972aa6295afd8b151e98a464919dd0c20f8",
    "server.py":
        "34e976489eee0e00a2fefb3564eaccf90c5fa2fc46103276192b33c9806efcc7",
    "meta_client.py":
        "9bf3599d76dbcc577389d33e7b16928e3efacdf288eb828b09931be83f4119e4",
    "verdict.py":
        "72c3f158152ede90aa4d925be26ffd0c61b672c86f3b60c9a96d9c75c2f12c1b",
    "comps.py":
        "241c4904e845c4d4b1e12621af15a163cc8f2e0f21a229008965e99c5f5779b1",
    "bay.py":
        "1dd3214da0d302aa2bd255d6ab21e78cead3730429f71cb8f0824d20001ced51",
    "listing.py":
        "560fbd61f35838e6b32cf0ec2ca0c731cc8db5fea2da0d16659bd167f7a511ef",
    "inventory.py":
        "89ccae27d3b4a883b685afd14fea013be10b1f7af4a9296e3d10db38d99560f6",
    "rules.json":
        "1861d550c7680f5c0199906fda321f6c66108df2ee7d948639c683ed2b521a86",
}
WEB_TREE_PINNED = ("0e54b30a21eebe366da64939a05d29db1708cdb043bd35fe9cc3e909d9f553d6"
                   "")


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
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def web_tree_hash():
    files = []
    for base, _, names in os.walk(os.path.join(ROOT, "web")):
        for name in names:
            files.append(os.path.relpath(os.path.join(base, name), ROOT)
                         .replace(os.sep, "/"))
    digest = hashlib.sha256()
    for rel in sorted(files):
        with open(os.path.join(ROOT, rel), "rb") as fh:
            digest.update(rel.encode("utf-8") + b"\0" + fh.read() + b"\0")
    return digest.hexdigest()


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
    def test_fenced_files_byte_identical(self):
        for rel, pinned in FENCE_PINNED.items():
            self.assertEqual(sha256_of(rel), pinned, rel)
        self.assertEqual(web_tree_hash(), WEB_TREE_PINNED)

    def test_photo_never_in_repo(self):
        hits = []
        for base, _, names in os.walk(ROOT):
            for name in names:
                if name.lower().endswith((".jpg", ".jpeg")):
                    hits.append(os.path.join(base, name))
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
