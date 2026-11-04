"""WO16 follow-up tests: file=note, fence intact, legs honestly closed.

The retry pass already ran; these tests pin its artifacts. Everything
here runs offline: the docs/evals.md note must match the follow-up JSON, WO16's
artifacts must be identical modulo line endings, the script's live-call
allowlist must contain only the four probes, VIN_LIVE stays False, and
no secret may appear in any artifact. The product-file and web-tree
fences retired in WO22: they guarded one measurement order and now
block product work.
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

import eval_meta_followup

import bay
import test_eval_meta

LIVE_CALL_MARKERS = test_eval_meta.LiveCallSitesTest.MARKERS

FOLLOWUP_START = "<!-- EVAL-META-FOLLOWUP:START -->"
FOLLOWUP_END = "<!-- EVAL-META-FOLLOWUP:END -->"

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

# sha256 pins over LF-normalized bytes (see sha256_of). Any edit to a
# fenced measurement file fails loudly here instead of slipping through.
WO16_PINNED = {
    os.path.join("scripts", "eval_meta.py"):
        "e7ba5d698087fdcfd486782e9b55c7abda67bbb5b3ea7e31d81ff12f535810c4",
    "eval_meta_results.json":
        "62877fd49ff3171c1a389d6a5c7602784e254ee1fa319a17f5e26d90de1499ab",
    os.path.join("tests", "test_eval_meta.py"):
        "c51a23bd7c2167ae555fac673fdbbe5fe2b7f23777a2978ccde49167add06161",
}


def load_results():
    with open(os.path.join(ROOT, "eval_meta_followup_results.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def evals_text():
    with open(os.path.join(ROOT, "docs", "evals.md"), encoding="utf-8") as fh:
        return fh.read()


def evals_block(text, start, end):
    _, _, rest = text.partition(start)
    block, _, _ = rest.partition(end)
    return block


def sha256_of(rel):
    # LF-normalized: the same file hashes identically on CRLF and LF
    # checkouts, so the fence holds on Windows, Mac, and Linux.
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def followup_source():
    with open(os.path.join(ROOT, "scripts", "eval_meta_followup.py"),
              encoding="utf-8") as fh:
        return fh.read()


class FollowupShapeTest(unittest.TestCase):
    def test_results_file_has_four_probes(self):
        results = load_results()
        self.assertEqual(set(results["probes"]),
                         set(eval_meta_followup.PROBE_ALLOWLIST))
        self.assertEqual(len(results["probes"]), 4)
        for name, probe in results["probes"].items():
            self.assertEqual(probe["leg"], "closed", name)

    def test_agreement_rates_recompute(self):
        results = load_results()
        usability = results["probes"]["spark-usability"]
        agree = sum(1 for c in usability["cases"] for p in c["parts"]
                    if p["spark_agree"] is True)
        total = sum(1 for c in usability["cases"] for p in c["parts"]
                    if p["spark_agree"] is not None)
        recorded = usability["agreement"]
        self.assertEqual((recorded["agree"], recorded["total"]), (agree, total))
        self.assertEqual(recorded["rate"], "%d/%d" % (agree, total))
        yard = results["probes"]["baseten-yard"]
        agree = sum(1 for p in yard["parts"] if p["open_agree"] is True)
        total = sum(1 for p in yard["parts"] if p["open_agree"] is not None)
        recorded = yard["agreement"]
        self.assertEqual((recorded["agree"], recorded["total"]), (agree, total))
        pooled = results["pooled_updated"]
        base = results["baseline_wo16"]["live_vs_rules_pooled"]
        self.assertEqual(pooled["agree"], base["agree"]
                         + usability["agreement"]["agree"]
                         + yard["agreement"]["agree"])
        self.assertEqual(pooled["total"], base["total"]
                         + usability["agreement"]["total"]
                         + yard["agreement"]["total"])
        self.assertEqual(pooled["rate"], "%d/%d" % (pooled["agree"],
                                                   pooled["total"]))

    def test_rule_grades_recompute_offline(self):
        results = load_results()
        by_case = {c["case"]: c
                   for c in results["probes"]["spark-usability"]["cases"]}
        for case_id in eval_meta_followup.eval_scale.CASE_ORDER:
            built = eval_meta_followup.eval_scale.BUILDERS[case_id](ROOT)
            recorded = [(p["part_id"], p["rule_grade"], p["rule_id"])
                        for p in by_case[case_id]["parts"]]
            fresh = [(v["part_id"], v["verdict"], v["rule_id"])
                     for v in built["verdicts"]]
            self.assertEqual(recorded, fresh, case_id)
        yard = results["probes"]["baseten-yard"]
        built = eval_meta_followup.eval_scale.BUILDERS["yard-demo"](ROOT)
        recorded = [(p["part_id"], p["rule_grade"], p["rule_id"])
                    for p in yard["parts"]]
        fresh = [(v["part_id"], v["verdict"], v["rule_id"])
                 for v in built["verdicts"]]
        self.assertEqual(recorded, fresh, "yard-demo")

    def test_no_demo_grade_presented_as_live(self):
        results = load_results()
        modes = [p["spark_mode"]
                 for c in results["probes"]["spark-usability"]["cases"]
                 for p in c["parts"]]
        modes += [p["open_mode"]
                  for p in results["probes"]["baseten-yard"]["parts"]]
        for mode in modes:
            self.assertIn(mode, ("live", "live, ungraded", "no live grade"))
            self.assertNotIn("demo", mode)

    def test_one_attempt_each(self):
        results = load_results()
        usability = results["probes"]["spark-usability"]
        self.assertLessEqual(usability["verify"]["calls_sent"], 1)
        for case in usability["cases"]:
            self.assertIn(case["spark"]["call_sent"], (True, False),
                          case["case"])
        yard = results["probes"]["baseten-yard"]
        sam = results["probes"]["sam-segment"]["call"]
        payload = results["probes"]["spark-image-payload"]["call"]
        for name, call in (("yard", yard["open"]), ("sam", sam),
                           ("payload", payload)):
            self.assertIn(call["call_sent"], (True, False), name)
        calls = (usability["live_calls_sent"] + yard["live_calls_sent"]
                 + results["probes"]["sam-segment"]["live_calls_sent"]
                 + results["probes"]["spark-image-payload"]["live_calls_sent"])
        self.assertEqual(results["live_calls_sent_total"], calls)
        self.assertEqual(results["model_list_calls_sent"], 0)


class FollowupEvalsTest(unittest.TestCase):
    def test_evals_note_matches_file(self):
        results = load_results()
        block = evals_block(evals_text(), FOLLOWUP_START, FOLLOWUP_END)
        self.assertTrue(block.strip())
        self.assertIn(results["pooled_updated"]["rate"], block)
        usability = results["probes"]["spark-usability"]["agreement"]
        yard = results["probes"]["baseten-yard"]["agreement"]
        self.assertIn(usability["rate"], block)
        self.assertIn(yard["rate"], block)
        sam = results["probes"]["sam-segment"]["call"]
        payload = results["probes"]["spark-image-payload"]["call"]
        if sam.get("request_id"):
            self.assertIn(sam["request_id"], block)
        if payload.get("request_id"):
            self.assertIn(payload["request_id"], block)
        self.assertIn("CLOSED", block)
        self.assertIn("VIN_LIVE stays False", block)

    def test_wo16_table_still_renders_from_wo16_file(self):
        with open(os.path.join(ROOT, "eval_meta_results.json"),
                  encoding="utf-8") as fh:
            wo16 = json.load(fh)
        block = evals_block(evals_text(), eval_meta_followup.eval_meta.START,
                             eval_meta_followup.eval_meta.END)
        self.assertEqual(
            block, "\n" + eval_meta_followup.eval_meta.render_section(wo16))


class FenceTest(unittest.TestCase):
    def test_wo16_artifacts_identical(self):
        for rel, pinned in WO16_PINNED.items():
            self.assertEqual(sha256_of(rel), pinned, rel)

    def test_vin_live_still_false(self):
        results = load_results()
        self.assertFalse(results["vin_live"])
        self.assertEqual(results["live_vin_calls_sent"], 0)
        self.assertIs(bay.VIN_LIVE, False)

    def test_allowlist_is_four_probes(self):
        self.assertEqual(eval_meta_followup.PROBE_ALLOWLIST,
                         ("spark-usability", "baseten-yard", "sam-segment",
                          "spark-image-payload"))
        for name in ("probe_spark_usability", "probe_baseten_yard",
                     "probe_sam_segment", "probe_spark_payload"):
            self.assertTrue(callable(getattr(eval_meta_followup, name)), name)

    def test_no_other_live_path(self):
        src = followup_source()
        for marker in LIVE_CALL_MARKERS:
            self.assertNotIn(marker, src, marker)
        self.assertEqual(src.count("urlopen("), 2)
        self.assertNotIn('"/sam/segment"', src)
        self.assertNotIn("'/sam/segment'", src)
        self.assertIn("/responses", src)

    def test_sam_official_source_only(self):
        results = load_results()
        discovery = results["probes"]["sam-segment"]["discovery"]
        self.assertTrue(discovery["sources"])
        for source in discovery["sources"]:
            self.assertIn("dev.meta.ai", source)
        self.assertEqual(discovery["confirmed_path"],
                         "POST " + results["api_base"] + "/responses")
        self.assertEqual(discovery["confirmed_model"], "sam-3.1")

    def test_no_secrets_in_artifacts(self):
        values = env_secret_values(os.path.join(ROOT, ".env"))
        haystacks = [
            open(os.path.join(ROOT, "eval_meta_followup_results.json"),
                 encoding="utf-8").read(),
            evals_block(evals_text(), FOLLOWUP_START, FOLLOWUP_END),
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
