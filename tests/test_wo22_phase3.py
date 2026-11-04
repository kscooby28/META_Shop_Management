"""WO22 Phase 3 pins: judge-first README, docs move, retired wording."""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_rel(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class ReadmeStructureTest(unittest.TestCase):
    HEADINGS = (
        "# Shop AI Copilot",
        "## Demo video",
        "## What it does",
        "## How Meta models are used",
        "## Why it isn't a chatbot or an image analyzer",
        "## Quickstart",
        "## Built during the event",
    )

    def test_headings_in_order(self):
        text = read_rel("README.md")
        at = 0
        for heading in self.HEADINGS:
            found = text.index(heading, at)
            self.assertGreaterEqual(found, at)
            at = found

    def test_video_placeholder_and_screenshot_note(self):
        text = read_rel("README.md")
        self.assertIn("VIDEO_URL", text)
        self.assertIn("docs/img/", text)
        self.assertIn("pending owner capture", text)

    def test_model_table_rows(self):
        text = read_rel("README.md")
        table = text[text.index("## How Meta models are used"):
                     text.index("## Why it isn't a chatbot")]
        for row in ("Muse Spark 1.3", "Muse Spark Open on Baseten",
                    "Muse Wonder Standard", "Muse Image", "SAM 3.1",
                    "Voice Transcribe", "VIN plate read"):
            self.assertIn(row, table, row)
        self.assertIn("photo \u2192 facts \u2192 rules verdict "
                      "\u2192 model second look \u2192 human gate", table)

    def test_two_columns_and_gates(self):
        text = read_rel("README.md")
        section = text[text.index("## What it does"):
                       text.index("## How Meta models are used")]
        self.assertIn("Shop \u2014 fix it", section)
        self.assertIn("DIY Garage \u2014 your cars and parts", section)
        why = text[text.index("## Why it isn't a chatbot"):
                   text.index("## Quickstart")]
        self.assertIn("Approve", why)
        self.assertIn("rules.json", why)

    def test_contributors_license_attribution(self):
        text = read_rel("README.md")
        built = text[text.index("## Built during the event"):]
        for phrase in ("kscooby28", "Muse", "Muse Code", "78931ba",
                       "October 26", "November 4", "MIT",
                       "[LICENSE](LICENSE)", "Piper", "CC BY 4.0",
                       "docs/build-log.md", "docs/evals.md",
                       "docs/video-plan.md"):
            self.assertIn(phrase, built, phrase)


class MovedDocsTest(unittest.TestCase):
    def test_build_log_holds_work_order_history(self):
        log = read_rel("docs", "build-log.md")
        for phrase in ("## The Bay side (Work Order 2)",
                       "## First-run identity + enthusiast inventory "
                       "(Work Order 3)",
                       "## Graphical pass + VIN experience (Work Order 4)",
                       "## Usability pass (Work Order 5)",
                       "## Valuation engine + money grade (Work Order 8)",
                       "## Credentials + auto-post, the mechanism "
                       "(Work Order 15)",
                       "## Glossary (only what the demo shows)",
                       "## Layout"):
            self.assertIn(phrase, log, phrase)

    def test_evals_holds_all_measurement_blocks(self):
        text = read_rel("docs", "evals.md")
        for marker in ("<!-- EVAL-LAB:START -->", "<!-- EVAL-LAB:END -->",
                       "<!-- EVAL-SCALE:START -->", "<!-- EVAL-SCALE:END -->",
                       "<!-- EVAL-META:START -->", "<!-- EVAL-META:END -->",
                       "<!-- EVAL-META-FOLLOWUP:START -->",
                       "<!-- EVAL-META-FOLLOWUP:END -->",
                       "<!-- EVAL-SAM-PNG:START -->",
                       "<!-- EVAL-SAM-PNG:END -->",
                       "<!-- EVAL-SAM-FILEID:START -->",
                       "<!-- EVAL-SAM-FILEID:END -->"):
            self.assertIn(marker, text, marker)
        self.assertIn("22/30", text)

    def test_readme_points_at_docs_not_tables(self):
        text = read_rel("README.md")
        self.assertNotIn("EVAL-SCALE:START", text)
        self.assertNotIn("EVAL-META:START", text)
        self.assertNotIn("## Glossary", text)


class RetiredWordingTest(unittest.TestCase):
    DOCS_AND_GENERATORS = (
        "README.md",
        os.path.join("docs", "evals.md"),
        os.path.join("scripts", "eval_lab.py"),
        os.path.join("scripts", "eval_scale.py"),
        "eval_scale_results.json",
    )
    PRODUCT = ("server.py", "meta_client.py", "spark_open.py", "wonder.py",
               "studio.py", "voice.py", "bay.py")

    def test_no_rotation_wording_in_docs_and_generators(self):
        for rel in self.DOCS_AND_GENERATORS:
            text = read_rel(rel)
            self.assertNotIn("rotation", text, rel)
            self.assertNotIn("Rotation", text, rel)

    def test_no_rotation_wording_in_product(self):
        for rel in self.PRODUCT:
            text = read_rel(rel)
            self.assertNotIn("rotation", text, rel)
            self.assertNotIn("Rotation", text, rel)

    def test_eval_meta_keeps_historical_order_name_only(self):
        text = read_rel("scripts", "eval_meta.py")
        self.assertNotIn("Rotation is", text)
        # The fenced WO16 order name is a historical record, not a status.
        self.assertIn("post-rotation", text)


if __name__ == "__main__":
    unittest.main()
