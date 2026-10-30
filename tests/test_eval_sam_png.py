"""SAM PNG resend tests: file=note, fence intact, leg honestly closed.

The single segment call already ran; these tests pin its artifacts.
Everything here runs offline: the README note must match the PNG
results JSON, no WO16, follow-up, or product file may have changed,
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

# sha256 pins taken at the resend commit. Any edit to a fenced file
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
        "d3c35050281889b3888fb781590837fda9e5ac2f813867ee3949004f4cf33369",
    "server.py":
        "cc56dae827a47b165c251ccfc4b2723d4a7f6e66b08e3c0d234a1c744180797a",
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
WEB_TREE_PINNED = ("a86ab4151302df3e6eea773b30ff2116b47fff20c0716f6cbea97e28"
                   "2bf1cbeb")


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
    def test_fenced_files_byte_identical(self):
        for rel, pinned in FENCE_PINNED.items():
            self.assertEqual(sha256_of(rel), pinned, rel)
        self.assertEqual(web_tree_hash(), WEB_TREE_PINNED)

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
