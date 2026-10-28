"""Inventory server-side tests: demo seed shape, comps lookup, no-data rule."""

import json
import os
import re
import unittest

from inventory import comp_for_label, load_seed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIN_SHAPE = re.compile(r"[A-HJ-NPR-Z0-9]{17}")
EMAIL_SHAPE = re.compile(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}")


class InventorySeedTest(unittest.TestCase):
    def setUp(self):
        self.seed = load_seed(ROOT)
        with open(os.path.join(ROOT, "demo_cache", "inv_seed.demo.json"), encoding="utf-8") as fh:
            self.raw = fh.read()

    def test_seed_shape(self):
        labels = [c["label"] for c in self.seed["cars"]]
        self.assertEqual(labels, ["My driver", "Parts car 1", "Parts car 2", "M3 parts car"])
        self.assertEqual(len(self.seed["parts"]), 6)
        self.assertEqual(len(self.seed["knowledge"]), 1)
        for key in ("sampleIdentify", "sampleVin", "samplePart", "partComps"):
            self.assertIn(key, self.seed)

    def test_seed_cars_are_source_tagged(self):
        for car in self.seed["cars"]:
            self.assertTrue(car["source_tags"])
            self.assertEqual(car["identity"]["trim"], "unknown")

    def test_m3_knowledge_note(self):
        note = self.seed["knowledge"][0]
        self.assertEqual(note["part"], "engine computer")
        self.assertIn("EWS", note["reason"])
        self.assertEqual(note["value"], 200)
        self.assertIn("owner note", note["source"])

    def test_seed_holds_no_vins_or_emails(self):
        self.assertIsNone(VIN_SHAPE.search(self.raw))
        self.assertIsNone(EMAIL_SHAPE.search(self.raw))

    def test_comps_demo_hit(self):
        comp = comp_for_label(self.seed, "engine computer", allow_samples=True)
        self.assertEqual(comp["value"], 200)
        self.assertTrue(comp["source"])

    def test_comps_demo_miss_is_no_data(self):
        comp = comp_for_label(self.seed, "trunk lid", allow_samples=True)
        self.assertIsNone(comp["value"])
        self.assertEqual(comp["source"], "")

    def test_comps_live_is_no_data(self):
        comp = comp_for_label(self.seed, "engine computer", allow_samples=False)
        self.assertIsNone(comp["value"])
        self.assertIn("No live comps", comp["note"])


if __name__ == "__main__":
    unittest.main()
