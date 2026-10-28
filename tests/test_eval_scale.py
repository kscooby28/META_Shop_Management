"""Scale evaluation tests (WO13): table=file, rules fixed, Baseten-only live.

The live run already happened; these tests pin its artifacts. Everything
here runs offline so a cold clone stays green: the README table must
render byte-identical from the JSON file, the JSON rule grades must
recompute from the untouched rules, no Meta network path may exist in
the harness, and the yard-photos loader must report absent/empty clean.
"""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eval_scale
import yard_photos


def load_results():
    with open(os.path.join(ROOT, "eval_scale_results.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def readme_text():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def readme_block(text, start, end):
    _, _, rest = text.partition(start)
    block, _, _ = rest.partition(end)
    return block


class ScaleAgreementTest(unittest.TestCase):
    def test_table_matches_file_exactly(self):
        results = load_results()
        block = readme_block(readme_text(), eval_scale.START, eval_scale.END)
        self.assertTrue(block.strip())
        self.assertEqual(block, "\n" + eval_scale.render_section(results))

    def test_agreement_rate_recomputes(self):
        results = load_results()
        agree = sum(1 for c in results["cases"] for p in c["parts"]
                    if p["agree"] is True)
        total = sum(1 for c in results["cases"] for p in c["parts"]
                    if p["agree"] is not None)
        self.assertEqual(results["agreement"]["agree"], agree)
        self.assertEqual(results["agreement"]["total"], total)
        self.assertEqual(results["agreement"]["rate"], "%d/%d" % (agree, total))
        self.assertIn("Agreement: %d/%d parts" % (agree, total), readme_text())

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
        shown = [c for c in results["cases"] for p in c["parts"]
                 if p["agree"] is False]
        self.assertTrue(shown)
        for case in results["cases"]:
            for part in case["parts"]:
                if part["agree"] is False:
                    self.assertIn(part["open_reason"], text)
                    self.assertIn(part["rule_name"], text)


class RulesUnchangedTest(unittest.TestCase):
    def test_rule_grades_recompute_offline(self):
        results = load_results()
        by_case = {c["case"]: c for c in results["cases"]}
        self.assertEqual([c["case"] for c in results["cases"]],
                         list(eval_scale.CASE_ORDER))
        for case_id in eval_scale.CASE_ORDER:
            built = eval_scale.BUILDERS[case_id](ROOT)
            recorded = [(p["part_id"], p["rule_grade"], p["rule_id"])
                        for p in by_case[case_id]["parts"]]
            fresh = [(v["part_id"], v["verdict"], v["rule_id"])
                     for v in built["verdicts"]]
            self.assertEqual(recorded, fresh, case_id)

    def test_rules_json_untouched(self):
        with open(os.path.join(ROOT, "rules.json"), encoding="utf-8") as fh:
            rules = json.load(fh)
        self.assertEqual(rules["version"], 1)
        self.assertEqual(rules["labor_rate_per_hour"], 180)
        self.assertEqual([r["id"] for r in rules["rules"]],
                         ["r_damaged", "r_thin_evidence", "r_pull_now",
                          "r_worth_it_seen", "r_worth_it_twice", "r_default"])


class BasetenOnlyTest(unittest.TestCase):
    def test_harness_has_no_meta_network_path(self):
        with open(os.path.join(ROOT, "scripts", "eval_scale.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        for banned in ("api.meta.ai", "meta_client", "chat_stream",
                       "VIN_LIVE = True", "IMAGE_LIVE = True",
                       "VOICE_LIVE = True", "WONDER_LIVE = True"):
            self.assertNotIn(banned, src, banned)
        self.assertIn("spark_open.request_grades", src)

    def test_meta_live_flags_off(self):
        import bay
        import studio
        import voice
        import wonder

        self.assertFalse(bay.VIN_LIVE)
        self.assertFalse(studio.IMAGE_LIVE)
        self.assertFalse(voice.VOICE_LIVE)
        self.assertFalse(wonder.WONDER_LIVE)

    def test_baseten_target_exact(self):
        import spark_open

        self.assertEqual(spark_open.BASETEN_ENDPOINT,
                         "https://inference.baseten.co/v1")
        self.assertEqual(spark_open.SPARK_OPEN_MODEL,
                         "meta-models/muse-spark-open-1026")
        self.assertEqual(spark_open.BASETEN_KEY_NAME, "BASETEN_API_KEY")

    def test_results_record_zero_meta_calls(self):
        results = load_results()
        self.assertEqual(results["live_meta_calls_attempted"], 0)
        self.assertEqual(results["live_baseten_calls_sent"],
                         sum(1 for c in results["cases"] if c["call_sent"]))
        for leg in ("Muse Spark 1.3", "SAM 3.1", "Muse Image", "Muse Voice",
                    "Muse Wonder"):
            self.assertTrue(any(leg in entry for entry in results["engines_demo"]),
                            leg)

    def test_no_demo_grade_presented_as_live(self):
        results = load_results()
        for case in results["cases"]:
            for part in case["parts"]:
                self.assertIn(part["open_mode"],
                              ("live", "live, ungraded", "no live grade"))
                self.assertNotIn("demo", part["open_mode"])

    def test_tour_compare_still_forces_demo(self):
        src = open(os.path.join(ROOT, "web", "app.js"), encoding="utf-8").read()
        start = src.index("===== guided tour (WO12)")
        end = src.index("===== end guided tour =====")
        self.assertIn("runCompare({ demo: true })", src[start:end])

    def test_no_secrets_in_artifacts(self):
        try:
            with open(os.path.join(ROOT, ".env"), encoding="utf-8") as fh:
                values = [line.split("=", 1)[1].strip()
                          for line in fh.read().splitlines()
                          if "=" in line and line.split("=", 1)[1].strip()]
        except OSError:
            values = []  # cold clone ships no .env; nothing to leak
        haystacks = [
            open(os.path.join(ROOT, "eval_scale_results.json"),
                 encoding="utf-8").read(),
            readme_block(readme_text(), eval_scale.START, eval_scale.END),
        ]
        for value in values:
            for haystack in haystacks:
                self.assertNotIn(value, haystack)


class YardLoaderTest(unittest.TestCase):
    def test_absent_folder_reports_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = yard_photos.load_yard(tmp)
        self.assertEqual(report["status"], "absent")
        self.assertEqual(report["cars"], [])
        self.assertIn("yard-photos", report["notice"])

    def test_empty_folder_reports_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "yard-photos"))
            report = yard_photos.load_yard(tmp)
        self.assertEqual(report["status"], "empty")
        self.assertEqual(report["cars"], [])

    def test_populated_folder_parses_without_invention(self):
        with tempfile.TemporaryDirectory() as tmp:
            car = os.path.join(tmp, "yard-photos", "car-a")
            os.makedirs(car)
            open(os.path.join(car, "front.jpg"), "wb").close()
            open(os.path.join(car, "rear.png"), "wb").close()
            open(os.path.join(car, "notes.txt"), "w",
                 encoding="utf-8").write("runs: yes\nmiles: 141000\n")
            report = yard_photos.load_yard(tmp)
        self.assertEqual(report["status"], "ok")
        (entry,) = report["cars"]
        self.assertEqual(entry["car"], "car-a")
        self.assertEqual(entry["photos"], ["front.jpg", "rear.png"])
        self.assertEqual(entry["notes"]["runs"], "yes")
        self.assertEqual(entry["notes"]["miles"], "141000")
        self.assertEqual(entry["notes"]["why_parked"], "unknown")

    def test_missing_notes_read_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "yard-photos", "car-b"))
            report = yard_photos.load_yard(tmp)
        (entry,) = report["cars"]
        self.assertEqual(entry["photos"], [])
        self.assertEqual(entry["notes"]["runs"], "unknown")
        self.assertEqual(entry["notes"]["miles"], "unknown")
        self.assertEqual(entry["notes"]["why_parked"], "unknown")


if __name__ == "__main__":
    unittest.main()
