"""Meta-live evaluation tests (WO16): table=file, rules fixed, legs honest.

The live run already happened; these tests pin its artifacts. Everything
here runs offline so a cold clone stays green: the README table must
render byte-identical from the JSON file, the JSON rule grades must
recompute from the untouched rules, live-call sites are pinned to the
known set, the VIN gate stays shut on anything but unanimous proof, and
no secret may appear in any artifact.
"""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eval_meta

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

import bay


def load_results():
    with open(os.path.join(ROOT, "eval_meta_results.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def readme_text():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def readme_block(text, start, end):
    _, _, rest = text.partition(start)
    block, _, _ = rest.partition(end)
    return block


class MetaAgreementTest(unittest.TestCase):
    def test_table_matches_file_exactly(self):
        results = load_results()
        block = readme_block(readme_text(), eval_meta.START, eval_meta.END)
        self.assertTrue(block.strip())
        self.assertEqual(block, "\n" + eval_meta.render_section(results))

    def test_agreement_rates_recompute(self):
        results = load_results()
        pairs = [("spark_agree", "spark_vs_rules"),
                 ("open_agree", "open_vs_rules"),
                 ("engines_agree", "spark_vs_open")]
        for field, key in pairs:
            agree = sum(1 for c in results["cases"] for p in c["parts"]
                        if p[field] is True)
            total = sum(1 for c in results["cases"] for p in c["parts"]
                        if p[field] is not None)
            recorded = results["agreement"][key]
            self.assertEqual(recorded["agree"], agree, key)
            self.assertEqual(recorded["total"], total, key)
            self.assertEqual(recorded["rate"], "%d/%d" % (agree, total), key)
        pooled = results["agreement"]["live_vs_rules_pooled"]
        spark = results["agreement"]["spark_vs_rules"]
        opened = results["agreement"]["open_vs_rules"]
        self.assertEqual(pooled["agree"], spark["agree"] + opened["agree"])
        self.assertEqual(pooled["total"], spark["total"] + opened["total"])
        self.assertIn("Agreement: Spark 1.3 vs rules %s" % spark["rate"],
                      readme_text())

    def test_every_part_row_present(self):
        text = readme_text()
        results = load_results()
        for case in results["cases"]:
            for part in case["parts"]:
                self.assertIn("| %s | %s | %s |" % (
                    case["case"], part["label"], part["rule_grade"]), text)

    def test_disagreements_carry_both_reasons(self):
        text = readme_text()
        results = load_results()
        for case in results["cases"]:
            for part in case["parts"]:
                if part["spark_agree"] is False:
                    self.assertIn(part["spark_reason"], text)
                    self.assertIn(part["rule_name"], text)
                if part["open_agree"] is False:
                    self.assertIn(part["open_reason"], text)
                    self.assertIn(part["rule_name"], text)

    def test_fifteen_parts_bay3_empty(self):
        results = load_results()
        total = sum(len(c["parts"]) for c in results["cases"])
        self.assertEqual(total, 15)
        bay3 = next(c for c in results["cases"] if c["case"] == "bay-case3")
        self.assertEqual(bay3["parts"], [])
        for leg in ("spark", "open"):
            self.assertFalse(bay3[leg]["call_sent"], leg)
        self.assertFalse(bay3["wonder"]["call_sent"])
        self.assertFalse(bay3["sam"]["call_sent"])

    def test_call_counts_recompute(self):
        results = load_results()
        meta = sum(1 for c in results["cases"] if c["spark"]["call_sent"])
        meta += sum(1 for c in results["cases"] if c["wonder"]["call_sent"])
        meta += sum(1 for c in results["cases"] if c["sam"]["call_sent"])
        meta += 2  # Spark + Wonder verification calls
        self.assertEqual(results["live_meta_calls_attempted"], meta)
        opened = sum(1 for c in results["cases"] if c["open"]["call_sent"])
        self.assertEqual(results["live_baseten_calls_sent"], opened)

    def test_no_demo_grade_presented_as_live(self):
        results = load_results()
        for case in results["cases"]:
            for part in case["parts"]:
                for mode in (part["spark_mode"], part["open_mode"]):
                    self.assertIn(mode, ("live", "live, ungraded",
                                         "no live grade"))
                    self.assertNotIn("demo", mode)


class MetaRulesUnchangedTest(unittest.TestCase):
    def test_rule_grades_recompute_offline(self):
        results = load_results()
        by_case = {c["case"]: c for c in results["cases"]}
        self.assertEqual([c["case"] for c in results["cases"]],
                         list(eval_meta.eval_scale.CASE_ORDER))
        for case_id in eval_meta.eval_scale.CASE_ORDER:
            built = eval_meta.eval_scale.BUILDERS[case_id](ROOT)
            recorded = [(p["part_id"], p["rule_grade"], p["rule_id"])
                        for p in by_case[case_id]["parts"]]
            fresh = [(v["part_id"], v["verdict"], v["rule_id"])
                     for v in built["verdicts"]]
            self.assertEqual(recorded, fresh, case_id)


class LiveCallSitesTest(unittest.TestCase):
    MARKERS = ("request_grades(", "request_opinion(", "segment_parts(",
               "read_vin_photo(", "identify_car(", "describe_part(",
               "draft_plan(", "chat_stream(", "escalate(", "compare_grades(",
               "transcribe(", "request_studio_render(", "draft_listing(",
               "demo_lookup(")
    # Every file that may initiate or define a live-model call: the
    # adapters that define the legs, the gated product legs, and the
    # measurement scripts. tests/ is excluded: it names these functions
    # to pin and mock them, and the suite runs offline.
    ALLOWED = {"listing.py", "meta_client.py", "spark_open.py", "wonder.py",
               "voice.py", "studio.py", "server.py",
               os.path.join("scripts", "eval_lab.py"),
               os.path.join("scripts", "eval_scale.py"),
               os.path.join("scripts", "eval_meta.py")}

    def test_live_calls_only_in_known_files(self):
        found = set()
        roots = [(ROOT, False), (os.path.join(ROOT, "scripts"), True)]
        for base, _ in roots:
            for name in sorted(os.listdir(base)):
                if not name.endswith(".py"):
                    continue
                rel = name if base == ROOT else os.path.join("scripts", name)
                with open(os.path.join(base, name), encoding="utf-8") as fh:
                    src = fh.read()
                if any(marker in src for marker in self.MARKERS):
                    found.add(rel)
        self.assertEqual(found, self.ALLOWED)

    def test_eval_harness_makes_no_demo_substitution(self):
        with open(os.path.join(ROOT, "scripts", "eval_meta.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("spark_open.request_grades", src)
        self.assertIn("wonder.request_opinion", src)
        self.assertIn("meta_client.segment_parts", src)
        self.assertNotIn("demo_grades(", src)
        self.assertNotIn("demo_opinion(", src)


class VinGateTest(unittest.TestCase):
    def test_unanimous_proof_flips(self):
        flip, reason = eval_meta.vin_flip_decision(
            {"a": {"usable": True, "cause": ""},
             "b": {"usable": True, "cause": ""}})
        self.assertTrue(flip)
        self.assertIn("all 2", reason)

    def test_one_failure_blocks_flip(self):
        flip, reason = eval_meta.vin_flip_decision(
            {"a": {"usable": True, "cause": ""},
             "b": {"usable": False, "cause": "plate unreadable"}})
        self.assertFalse(flip)
        self.assertIn("b (plate unreadable)", reason)

    def test_empty_set_never_flips(self):
        flip, _ = eval_meta.vin_flip_decision({})
        self.assertFalse(flip)

    def test_recorded_decision_matches_product_flag(self):
        results = load_results()
        gate = results["vin_gate"]
        self.assertFalse(gate["flip"])
        self.assertEqual(gate["live_vin_calls_sent"], 0)
        self.assertIs(bay.VIN_LIVE, False)


class ModelIdsTest(unittest.TestCase):
    def test_ids_recorded_with_evidence(self):
        model_ids = load_results()["model_ids"]
        self.assertEqual(model_ids["spark_model"], "muse-spark-1.3")
        self.assertTrue(model_ids["spark_on_list"])
        self.assertTrue(model_ids["spark_check"]["cause"])
        self.assertEqual(model_ids["wonder_model"], "muse-wonder-1.0")
        self.assertEqual(model_ids["wonder_path"], "/chat/completions")
        self.assertTrue(model_ids["wonder_check"]["live_ok"])
        self.assertIn("wonder", ",".join(model_ids["live_model_ids"]))

    def test_sam_correction_recorded(self):
        model_ids = load_results()["model_ids"]
        self.assertEqual(model_ids["sam_model"], "sam-3-1")
        self.assertEqual(model_ids["sam_corrected_to"], "sam-3.1")
        self.assertIn("sam-3.1", model_ids["sam_correction_evidence"])
        import meta_client
        self.assertEqual(meta_client.SAM_MODEL, "sam-3.1")

    def test_sam_leg_called_once(self):
        results = load_results()
        sent = [c["case"] for c in results["cases"] if c["sam"]["call_sent"]]
        self.assertEqual(sent, ["yard-demo"])

    def test_no_secrets_in_artifacts(self):
        values = env_secret_values(os.path.join(ROOT, ".env"))
        haystacks = [
            open(os.path.join(ROOT, "eval_meta_results.json"),
                 encoding="utf-8").read(),
            readme_block(readme_text(), eval_meta.START, eval_meta.END),
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
