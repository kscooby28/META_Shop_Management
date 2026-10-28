"""Visual-layer suite: runs the Node driver against web/gallery.js.

Covers the behavior behind the Work Order 4 visuals: strip order, frame
selection, overlay coordinates on source frames, part-to-frame links, demo
framing, and VIN samples that carry fields but never a VIN string.
"""

import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class VisualTest(unittest.TestCase):
    def test_visual_suites(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required to run the visual suite")
        driver = os.path.join(ROOT, "tests", "visual_driver.js")
        proc = subprocess.run(
            [node, driver], cwd=ROOT, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, "visual driver failed:\n%s" % output)
        self.assertIn("ALL", output)
        self.assertNotIn("FAIL", output)


if __name__ == "__main__":
    unittest.main()
