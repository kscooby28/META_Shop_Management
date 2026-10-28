"""Eval lab tests (WO7 phase 4): offline harness, owner agreement, all blocked."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eval_lab


class EvalLabTest(unittest.TestCase):
    def test_offline_rows_cover_all_engines(self):
        rows, notes = eval_lab.measure()
        engines = [r["engine"] for r in rows]
        self.assertEqual(len(rows), 4)
        self.assertTrue(any(e.startswith("muse-spark-1.3") for e in engines))
        self.assertTrue(any(e.startswith("wonder-standard") for e in engines))
        self.assertTrue(any("spark-open" in e for e in engines))
        self.assertTrue(any(e == "glimmer" for e in engines))

    def test_demo_legs_agree_with_owner(self):
        rows, _ = eval_lab.measure()
        spark = next(r for r in rows if r["engine"].startswith("muse-spark-1.3"))
        self.assertIn("7/7 boxes valid", spark["grounding"])
        self.assertIn("7/7 owner grades", spark["agreement"])
        self.assertNotIn("DRIFT", spark["agreement"])
        wonder = next(r for r in rows if r["engine"].startswith("wonder-standard"))
        self.assertIn("7/7 router outcomes", wonder["agreement"])

    def test_all_live_legs_flagged_off(self):
        import bay
        import studio
        import voice
        import wonder

        self.assertFalse(bay.VIN_LIVE)
        self.assertFalse(studio.IMAGE_LIVE)
        self.assertFalse(voice.VOICE_LIVE)
        self.assertFalse(wonder.WONDER_LIVE)
        rows, _ = eval_lab.measure()
        for row in rows:
            self.assertIn("blocked", row["status"])

    def test_baseten_target_exact(self):
        self.assertEqual(eval_lab.SPARK_OPEN_ENDPOINT, "https://inference.baseten.co/v1")
        self.assertEqual(eval_lab.SPARK_OPEN_MODEL, "meta-models/muse-spark-open-1026")
        self.assertEqual(eval_lab.BASETEN_KEY_NAME, "BASETEN_API_KEY")
        rows, _ = eval_lab.measure()
        opened = next(r for r in rows if "spark-open" in r["engine"])
        self.assertIn("https://inference.baseten.co/v1", opened["status"])
        self.assertIn("meta-models/muse-spark-open-1026", opened["status"])

    def test_glimmer_reports_blocked_not_faked(self):
        rows, notes = eval_lab.measure()
        glimmer = next(r for r in rows if r["engine"] == "glimmer")
        self.assertIn("12GB", glimmer["status"])
        self.assertTrue(all(v == "—" for k, v in glimmer.items()
                            if k in ("grounding", "agreement", "cost", "latency")))

    def test_harness_makes_no_network_calls(self):
        with open(os.path.join(ROOT, "scripts", "eval_lab.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("urllib", src)
        self.assertNotIn("socket", src)
        self.assertNotIn("urlopen", src)

    def test_key_names_only_never_values(self):
        _, notes = eval_lab.measure()
        text = " ".join(notes)
        self.assertIn("Key names only were read", text)
        for name in ("META_API_KEY", "MODEL_API_KEY", "BASETEN_API_KEY", "GLIMMER_ENDPOINT"):
            self.assertIn(name, text)
        with open(os.path.join(ROOT, "scripts", "eval_lab.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("environ.get(n)", src.replace(" ", ""))

    def test_table_renders(self):
        rows, _ = eval_lab.measure()
        table = eval_lab.render_table(rows)
        self.assertIn("| engine |", table)
        self.assertEqual(table.count("\n"), 5)


if __name__ == "__main__":
    unittest.main()
